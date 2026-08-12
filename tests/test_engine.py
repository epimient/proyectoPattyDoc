from app.vision.engine import SquatStateMachine, shoulder_angle

import numpy as np

TEMPLATE = {
    "profundidad_objetivo_m": 0.35,
    "descenso_inicio_m": 0.1,
    "subida_completa_m": 0.15,
    "tolerancia_hombros_deg": 10,
}


def _sm():
    sm = SquatStateMachine(TEMPLATE)
    sm.calibrate(1.0)
    return sm


def test_inicia_en_esperando_sin_calibrar():
    sm = SquatStateMachine(TEMPLATE)
    state = sm.update(1.0, True)
    assert state["fase"] == "ESPERANDO"
    assert sm.repeticiones == 0


def test_calibracion_activa_de_pie():
    sm = SquatStateMachine(TEMPLATE)
    sm.calibrate(1.0)
    assert sm.fase == "DE_PIE"
    assert sm.calibrado


def test_ciclo_completo_cuenta_repeticion():
    sm = _sm()
    sm.update(1.15, True)          # +0.15m  DE_PIE -> BAJANDO
    sm.update(1.40, True)          # +0.40m  BAJANDO -> SQUAT_PROFUNDO
    state = sm.update(1.10, True)  # +0.10m  SQUAT_PROFUNDO -> DE_PIE
    assert state["repeticiones"] == 1
    assert state["rep_valid"] is True
    assert state["fase"] == "DE_PIE"


def test_postura_mala_no_cuenta():
    sm = _sm()
    sm.update(1.15, True)
    sm.update(1.40, True)
    state = sm.update(1.10, False)
    assert state["repeticiones"] == 0
    assert state["rep_valid"] is False
    assert state["rep_rejected"] is True
    assert state["rep_rejection_reason"] == "postura"


def test_desplazamiento_insuficiente_no_avanza():
    sm = _sm()
    sm.update(1.15, True)   # BAJANDO (+0.15m)
    state = sm.update(1.20, True)  # solo +0.20m, objetivo 0.35
    assert state["fase"] == "BAJANDO"


def test_shoulder_angle():
    assert shoulder_angle(np.array([0.0, 0.0]), np.array([0.1, 0.0])) == 0.0
    assert abs(shoulder_angle(np.array([0.0, 0.0]), np.array([0.1, 0.1]))) > 40.0
