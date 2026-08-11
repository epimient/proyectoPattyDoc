def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["model_loaded"] is True
    assert set(data["num_classes"].values()) == {9, 9, 7}


def test_exercises(client):
    response = client.get("/api/exercises")
    assert response.status_code == 200
    data = response.json()
    assert set(data.keys()) == {"Calentamiento", "Entrenamiento", "Enfriamiento"}
    assert len(data["Calentamiento"]) == 9
    assert len(data["Entrenamiento"]) == 9
    assert len(data["Enfriamiento"]) == 7
    assert all(len(e) > 0 for phase in data.values() for e in phase)
