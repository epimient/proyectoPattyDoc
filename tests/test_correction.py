from app.schemas.session import ObservationRequest
from app.services.correction_service import evaluate_correction

SQUAT = "Sentadillas asistidas con silla/barra"


def _obs(**kwargs):
    base = {
        "exercise": SQUAT,
        "frame_ts": 0.0,
        "fase": "DE_PIE",
        "desplazamiento_y": 0.0,
        "postura_correcta": True,
        "hombros_visibles": True,
        "repeticiones": 0,
    }
    base.update(kwargs)
    return ObservationRequest(**base)


def test_hombros_no_visibles():
    r = evaluate_correction(SQUAT, _obs(hombros_visibles=False))
    assert r.level == "error"
    assert "frente a la cámara" in r.message_es
    assert r.siguiente_paso == "CONTINUAR"


def test_repeticion_valida():
    r = evaluate_correction(SQUAT, _obs(fase="DE_PIE", repeticiones=3))
    assert r.level == "ok"
    assert "3/10" in r.message_es
    assert r.siguiente_paso == "CONTINUAR"


def test_repeticion_contada_tiene_evento_de_voz():
    r = evaluate_correction(SQUAT, _obs(repeticiones=3, rep_valid=True))
    assert r.evento_voz == "repeticion_contada"
    assert "Repetición 3 de 10" in r.mensaje_voz


def test_repeticion_rechazada_tiene_evento_de_voz():
    r = evaluate_correction(SQUAT, _obs(rep_rejected=True))
    assert r.evento_voz == "repeticion_rechazada"
    assert "no contó" in r.mensaje_voz
    assert r.siguiente_paso == "REPETIR"


def test_postura_mala_en_profundidad():
    r = evaluate_correction(
        SQUAT,
        _obs(fase="SQUAT_PROFUNDO", desplazamiento_y=0.38, postura_correcta=False),
    )
    assert r.level == "warning"
    assert "espalda recta" in r.message_es
    assert r.siguiente_paso == "REPETIR"


def test_profundidad_insuficiente():
    r = evaluate_correction(SQUAT, _obs(fase="BAJANDO", desplazamiento_y=0.2))
    assert r.level == "warning"
    assert "Baja un poco más" in r.message_es
    assert r.siguiente_paso == "CONTINUAR"


def test_completado_avanza():
    r = evaluate_correction(SQUAT, _obs(repeticiones=10))
    assert r.level == "ok"
    assert "completadas" in r.message_es
    assert r.siguiente_paso == "AVANZAR"


def test_ejercicio_sin_plantilla():
    r = evaluate_correction("Balanceo de brazos", _obs(exercise="Balanceo de brazos"))
    assert r.level == "ok"
    assert "sin plantilla" in r.message_es
    assert r.siguiente_paso == "CONTINUAR"


def test_nombre_con_prefijo_de_categoria():
    nombre_dataset = "(Fuerza y Resistencia) Sentadillas asistidas con silla/barra"
    r = evaluate_correction(nombre_dataset, _obs(exercise=nombre_dataset, repeticiones=2))
    assert r.level == "ok"
    assert "2/10" in r.message_es
