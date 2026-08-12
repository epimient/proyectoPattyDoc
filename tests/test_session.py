import pytest

from conftest import SAMPLE_PLAN

SQUAT = "Sentadillas asistidas con silla/barra"


def _start(client):
    response = client.post("/api/session/start", json={"plan": SAMPLE_PLAN})
    assert response.status_code == 200
    return response.json()


def _obs(**kwargs):
    base = {
        "exercise": SQUAT,
        "frame_ts": 1.0,
        "fase": "DE_PIE",
        "desplazamiento_y": 0.0,
        "postura_correcta": True,
        "hombros_visibles": True,
        "repeticiones": 0,
    }
    base.update(kwargs)
    return base


def test_start_session_returns_plan(client, session_store):
    data = _start(client)
    assert data["status"] == "active"
    assert data["plan"] == SAMPLE_PLAN
    assert len(data["session_id"]) == 32


def test_get_session(client, session_store):
    sid = _start(client)["session_id"]
    response = client.get(f"/api/session/{sid}")
    assert response.status_code == 200
    assert response.json()["current_exercise"] is None


def test_observation_records_and_returns_correction(client, session_store):
    sid = _start(client)["session_id"]
    response = client.post(f"/api/session/{sid}/observation", json=_obs(repeticiones=3))
    assert response.status_code == 200
    assert response.json()["level"] == "ok"
    assert "3/10" in response.json()["message_es"]

    response = client.post(
        f"/api/session/{sid}/observation",
        json=_obs(fase="SQUAT_PROFUNDO", desplazamiento_y=0.38, postura_correcta=False),
    )
    assert response.json()["level"] == "warning"

    log = client.get(f"/api/session/{sid}/observations").json()
    assert len(log) == 2
    assert log[-1]["level"] == "warning"

    session = client.get(f"/api/session/{sid}").json()
    assert session["current_exercise"] == SQUAT


def test_observation_sin_plantilla(client, session_store):
    sid = _start(client)["session_id"]
    obs = _obs(exercise="Balanceo de brazos")
    response = client.post(f"/api/session/{sid}/observation", json=obs)
    assert response.status_code == 200
    assert "sin plantilla" in response.json()["message_es"]


def test_complete_session(client, session_store):
    sid = _start(client)["session_id"]
    response = client.post(f"/api/session/{sid}/complete")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["completed_at"] is not None


def test_unknown_session_returns_404(client, session_store):
    assert client.get("/api/session/inexistente").status_code == 404
    assert client.post("/api/session/inexistente/observation", json=_obs()).status_code == 404
    assert client.get("/api/session/inexistente/observations").status_code == 404
    assert client.post("/api/session/inexistente/complete").status_code == 404


def test_abandon_session(client, session_store):
    sid = _start(client)["session_id"]
    assert session_store.abandon_session(sid) is True
    session = client.get(f"/api/session/{sid}").json()
    assert session["status"] == "abandoned"
    assert session["completed_at"] is not None
    # Una sesión ya cerrada (completed/abandoned) no se puede abandonar de nuevo.
    assert session_store.abandon_session(sid) is False


def test_observation_validation_error(client, session_store):
    sid = _start(client)["session_id"]
    bad = _obs(repeticiones=-5)
    assert client.post(f"/api/session/{sid}/observation", json=bad).status_code == 422
