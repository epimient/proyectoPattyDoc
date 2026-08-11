import threading
import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers.camera import get_controller
from app.vision.controller import CameraController

SQUAT = "Sentadillas asistidas con silla/barra"

SAMPLE_PLAN = {
    "calentamiento": "Marcha en el lugar con cuerda guía",
    "entrenamiento": SQUAT,
    "enfriamiento": "Respiraciones profundas",
}


# --------------------------------------------------------------------------
# Endpoints (con un controlador falso, sin cámara real)
# --------------------------------------------------------------------------

class FakeCameraController:
    def __init__(self, fail_start=False, fail_calibrate=False, fail_next=False, fail_stop=False):
        self.calls = []
        self.fail_start = fail_start
        self.fail_calibrate = fail_calibrate
        self.fail_next = fail_next
        self.fail_stop = fail_stop

    def get_frame(self):
        return b"\xff\xd8fakejpeg"

    @property
    def state(self):
        return {"status": "running", "session_id": "fake", "plan": SAMPLE_PLAN}

    def start(self, plan, source=None):
        self.calls.append(("start", plan, source))
        if self.fail_start:
            raise RuntimeError("cámara no disponible")
        return {"session_id": "fake", "plan": plan, "status": "running"}

    def calibrate(self):
        self.calls.append("calibrate")
        if self.fail_calibrate:
            raise RuntimeError("no hay sesión activa")
        return self.state

    def next(self):
        self.calls.append("next")
        if self.fail_next:
            raise RuntimeError("no hay ejercicio completado")
        return self.state

    def stop(self):
        self.calls.append("stop")
        if self.fail_stop:
            raise RuntimeError("no hay sesión activa")
        return self.state


@pytest.fixture()
def fake(client):
    fake = FakeCameraController()
    app.dependency_overrides[get_controller] = lambda: fake
    yield client, fake
    app.dependency_overrides = {}


def test_camera_state(fake):
    client, _ = fake
    r = client.get("/api/camera/state")
    assert r.status_code == 200
    assert r.json()["status"] == "running"
    assert r.json()["session_id"] == "fake"


def test_camera_start(fake):
    client, fake_ctrl = fake
    r = client.post("/api/camera/start", json={"plan": SAMPLE_PLAN})
    assert r.status_code == 200
    assert r.json()["session_id"] == "fake"
    assert fake_ctrl.calls[0][0] == "start"
    assert fake_ctrl.calls[0][1] == SAMPLE_PLAN


def test_camera_start_sin_camara_devuelve_503(client):
    app.dependency_overrides[get_controller] = lambda: FakeCameraController(fail_start=True)
    try:
        r = client.post("/api/camera/start", json={"plan": SAMPLE_PLAN})
        assert r.status_code == 503
    finally:
        app.dependency_overrides = {}


def test_camera_calibrate_sin_sesion_409(client):
    app.dependency_overrides[get_controller] = lambda: FakeCameraController(fail_calibrate=True)
    try:
        assert client.post("/api/camera/calibrate").status_code == 409
    finally:
        app.dependency_overrides = {}


def test_camera_next_sin_completado_409(client):
    app.dependency_overrides[get_controller] = lambda: FakeCameraController(fail_next=True)
    try:
        assert client.post("/api/camera/next").status_code == 409
    finally:
        app.dependency_overrides = {}


def test_camera_stop_sin_sesion_409(client):
    app.dependency_overrides[get_controller] = lambda: FakeCameraController(fail_stop=True)
    try:
        assert client.post("/api/camera/stop").status_code == 409
    finally:
        app.dependency_overrides = {}


def test_camera_stream_registrado_en_openapi(client):
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/camera/stream" in paths
    assert "get" in paths["/api/camera/stream"]


# --------------------------------------------------------------------------
# Controlador real (con un tracker falso que simula una sentadilla)
# --------------------------------------------------------------------------

def make_frame(y: float):
    img = np.zeros((240, 320, 3), np.uint8)
    positions = {
        0: np.array([-0.15, y, 1.0]),
        1: np.array([0.15, y, 1.0]),
    }
    centers = {0: (100, 120), 1: (220, 120)}
    corners = {
        0: np.array([[90, 110], [110, 110], [110, 130], [90, 130]]),
        1: np.array([[210, 110], [230, 110], [230, 130], [210, 130]]),
    }
    det = {"positions_3d": positions, "centers_2d": centers, "corners": corners}
    return img, det


class FakeTracker:
    def __init__(self, ys, source=0):
        self.frames = [make_frame(y) for y in ys]
        self.source = source
        self.released = False

    def read(self):
        if not self.frames:
            return None, None
        return self.frames.pop(0)

    def release(self):
        self.released = True


class RepeatTracker:
    def __init__(self):
        self.released = False

    def read(self):
        return make_frame(1.0)

    def release(self):
        self.released = True


def _wait_for_state(ctrl, expected, timeout=1.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = ctrl.state
        if all(state.get(key) == value for key, value in expected.items()):
            return state
        time.sleep(0.01)
    pytest.fail(f"Estado no alcanzado: {expected}; actual: {ctrl.state}")


def test_ejercicio_sin_plantilla_espera_siguiente(session_store):
    plan = {phase: f"Ejercicio manual {phase}" for phase in SAMPLE_PLAN}
    tracker = RepeatTracker()
    ctrl = CameraController(tracker_factory=lambda source=0: tracker, store_getter=lambda: session_store)
    session = session_store.create_session(plan)
    ctrl._state.update(status="running", session_id=session["session_id"], plan=plan)

    worker = threading.Thread(target=ctrl._run, args=(plan, tracker))
    worker.start()
    first = _wait_for_state(ctrl, {"status": "waiting_next", "phase": "calentamiento"})
    assert first["tracking_available"] is False
    time.sleep(0.1)
    assert ctrl.state["phase"] == "calentamiento"

    ctrl.next()
    _wait_for_state(ctrl, {"status": "waiting_next", "phase": "entrenamiento"})
    ctrl.stop()
    worker.join(timeout=1)
    assert tracker.released is True


def test_next_rechaza_doble_avance():
    ctrl = CameraController()
    ctrl._state["status"] = "waiting_next"

    assert ctrl.next()["status"] == "running"
    with pytest.raises(RuntimeError):
        ctrl.next()


def test_controller_cuenta_una_repeticion(session_store):
    from app.services.correction_service import get_template

    ys = [1.00, 1.12, 1.20, 1.30, 1.38, 1.20, 1.00, 0.90]
    fake = FakeTracker(ys)
    ctrl = CameraController(tracker_factory=lambda source=0: fake)

    store = session_store
    ctrl = CameraController(tracker_factory=lambda source=0: fake, store_getter=lambda: store)
    session = store.create_session(SAMPLE_PLAN)
    session_id = session["session_id"]

    ctrl._state.update(
        status="running",
        session_id=session_id,
        plan=SAMPLE_PLAN,
        phase="entrenamiento",
        exercise=SQUAT,
    )
    ctrl._calibrate.set()
    ctrl._next.set()

    ctrl._run(SAMPLE_PLAN, fake)

    obs = store.list_observations(session_id)
    assert len(obs) > 0
    assert obs[-1]["repeticiones"] == 1
    assert obs[-1]["fase"] in ("DE_PIE", "BAJANDO")
    assert fake.released is True
    assert ctrl.state["status"] in ("stopped", "completed")
