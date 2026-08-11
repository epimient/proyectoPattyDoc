import shutil

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.plan_service import PlanService, get_service
from app.models.session_store import SessionStore, get_store

SAMPLE_PROFILE = {
    "Edad": 51,
    "Género": "Femenino",
    "IMC": 27.4,
    "Nivel de Visión": "Hipermetropía",
    "Condición Física": "Moderada",
    "Tiempo de Actividad Física": 30,
    "Condición Comórbida": "Diabetes Tipo 2",
    "Preferencia de Accesibilidad": "Guías auditivas",
    "Entorno de Ejercicio": "Gimnasio",
    "Motivación": "Moderada",
}


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def service(tmp_path):
    model_src = get_service().model_path
    preprocessors_src = get_service().preprocessors_path
    model_dst = tmp_path / "modelo5.keras"
    preprocessors_dst = tmp_path / "preprocessors.pkl"
    shutil.copy(model_src, model_dst)
    shutil.copy(preprocessors_src, preprocessors_dst)
    return PlanService(model_path=model_dst, preprocessors_path=preprocessors_dst)


@pytest.fixture()
def override_service(service):
    app.dependency_overrides[get_service] = lambda: service
    yield service
    app.dependency_overrides = {}


@pytest.fixture()
def session_store(tmp_path):
    store = SessionStore(db_path=tmp_path / "sessions.db")
    app.dependency_overrides[get_store] = lambda: store
    yield store
    app.dependency_overrides = {}


SAMPLE_PLAN = {
    "calentamiento": "Marcha en el lugar con cuerda guía",
    "entrenamiento": "Sentadillas asistidas con silla/barra",
    "enfriamiento": "Respiraciones profundas",
}
