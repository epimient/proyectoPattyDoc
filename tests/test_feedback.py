from conftest import SAMPLE_PROFILE

VALID_CORRECTIONS = {
    "Calentamiento": "Rotaciones articulares suaves",
    "Entrenamiento": "Flexiones en pared",
    "Enfriamiento": "Respiraciones profundas",
}


def _feedback_payload(suitable, corrections, profile=None):
    return {
        "suitable": suitable,
        "input_data": profile or SAMPLE_PROFILE,
        "corrected_exercises": corrections,
    }


def test_feedback_suitable_does_not_retrain(client):
    response = client.post("/api/feedback", json=_feedback_payload(True, VALID_CORRECTIONS))
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "retrained": False,
        "message": "Plan adecuado, no se requiere reentrenamiento",
    }


def test_feedback_retrain_uses_lock(client, override_service, monkeypatch):
    class RecordingLock:
        def __init__(self):
            self.enter_count = 0

        def __enter__(self):
            self.enter_count += 1

        def __exit__(self, exc_type, exc, tb):
            return False

    lock = RecordingLock()
    override_service._feedback_lock = lock

    def fake_retrain(request):
        return {
            "status": "ok",
            "retrained": True,
            "message": "Modelo reentrenado y guardado",
        }

    monkeypatch.setattr(override_service, "_retrain_from_feedback", fake_retrain)

    response = client.post("/api/feedback", json=_feedback_payload(False, VALID_CORRECTIONS))

    assert response.status_code == 200
    assert response.json()["retrained"] is True
    assert lock.enter_count == 1


def test_feedback_retrains_with_new_exercise(client, override_service):
    new_exercise = "Caminata en el lugar"
    payload = _feedback_payload(False, {**VALID_CORRECTIONS, "Entrenamiento": new_exercise})

    response = client.post("/api/feedback", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["retrained"] is True

    health = client.get("/api/health").json()
    assert health["num_classes"]["Ejercicios Fase 2 de Entrenamiento"] == 10

    exercises = client.get("/api/exercises").json()
    assert new_exercise in exercises["Entrenamiento"]


def test_feedback_creates_backup_before_overwriting_artifacts(client, override_service):
    before_model = override_service.model_path.read_bytes()
    before_preprocessors = override_service.preprocessors_path.read_bytes()

    response = client.post("/api/feedback", json=_feedback_payload(False, VALID_CORRECTIONS))

    assert response.status_code == 200
    backup_dirs = list(override_service.backup_dir.iterdir())
    assert len(backup_dirs) == 1
    backup_dir = backup_dirs[0]
    assert (backup_dir / override_service.model_path.name).read_bytes() == before_model
    assert (backup_dir / override_service.preprocessors_path.name).read_bytes() == before_preprocessors


def test_feedback_does_not_modify_production_artifacts(client, override_service):
    from app.core.config import MODEL_PATH, PREPROCESSORS_PATH

    before = {
        str(p): p.read_bytes()
        for p in (MODEL_PATH, PREPROCESSORS_PATH)
    }
    response = client.post("/api/feedback", json=_feedback_payload(False, VALID_CORRECTIONS))
    assert response.status_code == 200
    after = {
        str(p): p.read_bytes()
        for p in (MODEL_PATH, PREPROCESSORS_PATH)
    }
    assert before == after
