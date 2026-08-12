import json

from app.core.config import TEMPLATES_PATH
from app.schemas.session import CorrectionResponse, ObservationRequest

_templates = None


def load_templates(path=TEMPLATES_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_templates():
    global _templates
    if _templates is None:
        _templates = load_templates()
    return _templates


def _normalize(s: str) -> str:
    return (
        s.lower()
        .replace("á", "a").replace("é", "e").replace("í", "i")
        .replace("ó", "o").replace("ú", "u").replace("ü", "u")
        .strip()
    )


def get_template(exercise: str) -> dict | None:
    templates = get_templates()
    if exercise in templates:
        return templates[exercise]

    # Matcheo flexible: ignora prefijos de categoría y acentos,
    # p.ej. "(Fuerza y Resistencia) Sentadillas..." → "Sentadillas..."
    target = _normalize(exercise)
    for key, tpl in templates.items():
        nkey = _normalize(key)
        if nkey in target or target in nkey:
            return tpl
    return None


def evaluate_correction(exercise: str, obs: ObservationRequest) -> CorrectionResponse:
    template = get_template(exercise)
    if template is None:
        return CorrectionResponse(
            level="ok",
            message_es="Ejercicio sin plantilla de evaluación aún",
            siguiente_paso="CONTINUAR",
        )
    return _evaluate(template, obs)


def _evaluate(template: dict, obs: ObservationRequest) -> CorrectionResponse:
    mensajes = template["mensajes"]

    def corr(level, key, step, evento_voz=None, mensaje_voz=None, **fmt):
        msg = mensajes.get(key, key)
        if fmt:
            msg = msg.format(**fmt)
        return CorrectionResponse(
            level=level,
            message_es=msg,
            siguiente_paso=step,
            evento_voz=evento_voz,
            mensaje_voz=mensaje_voz,
        )

    objetivo = template["repeticiones_objetivo"]

    if not obs.hombros_visibles:
        return corr("error", "hombros_no_visibles", "CONTINUAR")

    if obs.rep_rejected:
        message = (
            "La repetición no contó porque la postura no era correcta. "
            f"Llevas {obs.repeticiones} repeticiones contadas. "
            "Mantén los hombros nivelados y vuelve a intentarlo."
        )
        return CorrectionResponse(
            level="warning",
            message_es=message,
            siguiente_paso="REPETIR",
            evento_voz="repeticion_rechazada",
            mensaje_voz=message,
            id_evento_voz=f"repeticion_rechazada:{obs.frame_ts}",
        )

    if obs.rep_valid:
        if obs.repeticiones >= objetivo:
            message = f"Has completado las {objetivo} sentadillas."
            return CorrectionResponse(
                level="ok",
                message_es=mensajes.get("completado", message).format(objetivo=objetivo),
                siguiente_paso="AVANZAR",
                evento_voz="ejercicio_completado",
                mensaje_voz=message,
                id_evento_voz="ejercicio_completado",
            )
        message = (
            f"Repetición {obs.repeticiones} de {objetivo} completada correctamente. "
            "Puedes iniciar la siguiente."
        )
        return CorrectionResponse(
            level="ok",
            message_es=message,
            siguiente_paso="CONTINUAR",
            evento_voz="repeticion_contada",
            mensaje_voz=message,
            id_evento_voz=f"repeticion_contada:{obs.repeticiones}",
        )

    if obs.repeticiones >= objetivo:
        return corr("ok", "completado", "AVANZAR", objetivo=objetivo)

    if obs.fase == "SQUAT_PROFUNDO" and not obs.postura_correcta:
        return corr("warning", "postura", "REPETIR")

    if obs.fase == "BAJANDO" and obs.desplazamiento_y < template["profundidad_objetivo_m"]:
        return corr("warning", "profundidad", "CONTINUAR")

    return corr("ok", "ok", "CONTINUAR", reps=obs.repeticiones, objetivo=objetivo)
