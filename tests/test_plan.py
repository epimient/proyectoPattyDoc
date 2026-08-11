from conftest import SAMPLE_PROFILE


def test_plan_generates_valid_exercises(client):
    response = client.post("/api/plan", json=SAMPLE_PROFILE)
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"calentamiento", "entrenamiento", "enfriamiento"}
    assert all(data[k] for k in data)

    exercises = client.get("/api/exercises").json()
    assert data["calentamiento"] in exercises["Calentamiento"]
    assert data["entrenamiento"] in exercises["Entrenamiento"]
    assert data["enfriamiento"] in exercises["Enfriamiento"]


def test_plan_accepts_snake_case_fields(client):
    profile = {
        "edad": SAMPLE_PROFILE["Edad"],
        "genero": SAMPLE_PROFILE["Género"],
        "imc": SAMPLE_PROFILE["IMC"],
        "nivel_vision": SAMPLE_PROFILE["Nivel de Visión"],
        "condicion_fisica": SAMPLE_PROFILE["Condición Física"],
        "tiempo_actividad_fisica": SAMPLE_PROFILE["Tiempo de Actividad Física"],
        "condicion_comorbida": SAMPLE_PROFILE["Condición Comórbida"],
        "preferencia_accesibilidad": SAMPLE_PROFILE["Preferencia de Accesibilidad"],
        "entorno_ejercicio": SAMPLE_PROFILE["Entorno de Ejercicio"],
        "motivacion": SAMPLE_PROFILE["Motivación"],
    }
    response = client.post("/api/plan", json=profile)
    assert response.status_code == 200
    assert all(response.json()[k] for k in ("calentamiento", "entrenamiento", "enfriamiento"))


def test_plan_falls_back_on_unknown_labels(client):
    profile = {**SAMPLE_PROFILE, "Motivación": "Nula", "Género": "Otro"}
    response = client.post("/api/plan", json=profile)
    assert response.status_code == 200
    assert all(response.json()[k] for k in ("calentamiento", "entrenamiento", "enfriamiento"))


def test_plan_rejects_missing_fields(client):
    incomplete = {k: v for k, v in SAMPLE_PROFILE.items() if k != "IMC"}
    response = client.post("/api/plan", json=incomplete)
    assert response.status_code == 422


def test_plan_rejects_out_of_range(client):
    profile = {**SAMPLE_PROFILE, "Edad": 200}
    response = client.post("/api/plan", json=profile)
    assert response.status_code == 422
