import sys
import time

import cv2

from app.vision.api_client import ApiClient, ApiError
from app.vision.engine import SquatStateMachine, shoulder_angle
from app.vision.tracker import CameraTracker, ID_HOMBRO_DER, ID_HOMBRO_IZQ
from app.vision.tts import speak

PHASES = ["calentamiento", "entrenamiento", "enfriamiento"]

# Cooldown para repetir advertencias por voz (evita spam)
WARNING_COOLDOWN_S = 3.0

# Solo se envían observaciones en transiciones relevantes + un heartbeat de ~1 s,
# para no escribir una fila por frame en la BD del backend.
OBS_HEARTBEAT_S = 1.0


def _should_send(obs: dict, last_sig, last_ts) -> tuple:
    sig = (obs.get("fase"), obs.get("repeticiones"), obs.get("hombros_visibles"))
    now = time.time()
    if sig == last_sig and now - last_ts < OBS_HEARTBEAT_S:
        return sig, last_ts, False
    return sig, now, True


def _obs(exercise: str, frame_ts: float, **kwargs) -> dict:
    base = {
        "exercise": exercise,
        "frame_ts": frame_ts,
        "fase": "",
        "desplazamiento_y": 0.0,
        "postura_correcta": True,
        "hombros_visibles": False,
        "repeticiones": 0,
    }
    base.update(kwargs)
    return base


def _send(client: ApiClient, session_id: str, obs: dict) -> dict:
    """Envía una observación sin romper el detector si el backend falla."""
    try:
        return client.send_observation(session_id, obs)
    except ApiError as e:
        print(f"[API] No se pudo enviar la observación: {e}", flush=True)
        return {"level": "error", "message_es": "Sin conexión con el backend", "siguiente_paso": "CONTINUAR"}


def _maybe_speak(message: str, level: str, rep_valid: bool, last_message: str, last_warn: float):
    now = time.time()
    if rep_valid:
        speak(message)
    elif level == "ok":
        pass
    elif message != last_message or (now - last_warn) > WARNING_COOLDOWN_S:
        speak(message)
    return last_message if level == "ok" else message


def run_exercise(
    client: ApiClient,
    session_id: str,
    phase: str,
    exercise: str,
    template: dict,
    source,
    camera_params,
) -> bool:
    """Ejecuta el tracking de un ejercicio. Devuelve True si se avanza a la
    siguiente fase, False si el usuario sale (q)."""
    tracker = CameraTracker(source=source, camera_params=camera_params)
    sm = SquatStateMachine(template)
    completed = False
    last_message = ""
    last_warn = 0.0
    last_correction = {"level": "ok", "message_es": "", "siguiente_paso": "CONTINUAR"}
    last_sig = None
    last_sent_ts = 0.0

    speak(f"Comenzando {exercise}. Ponte de pie frente a la cámara y presiona C para calibrar.")
    try:
        while True:
            frame, detections = tracker.read()
            if frame is None:
                break

            corners = detections["corners"]
            CameraTracker.draw_tags(frame, corners)

            positions_3d = detections["positions_3d"]
            centers_2d = detections["centers_2d"]
            hombros_visibles = ID_HOMBRO_IZQ in positions_3d and ID_HOMBRO_DER in positions_3d
            frame_ts = time.time()
            obs = _obs(exercise, frame_ts, hombros_visibles=hombros_visibles)

            if hombros_visibles:
                p_izq = positions_3d[ID_HOMBRO_IZQ]
                p_der = positions_3d[ID_HOMBRO_DER]
                mid_3d = (p_izq + p_der) / 2.0
                mid_2d = (
                    int((centers_2d[ID_HOMBRO_IZQ][0] + centers_2d[ID_HOMBRO_DER][0]) / 2),
                    int((centers_2d[ID_HOMBRO_IZQ][1] + centers_2d[ID_HOMBRO_DER][1]) / 2),
                )
                cv2.circle(frame, mid_2d, 8, (0, 255, 255), -1)

                angulo = abs(shoulder_angle(p_izq, p_der))
                postura_ok = angulo < template["tolerancia_hombros_deg"]

                if not sm.calibrado:
                    cv2.putText(
                        frame,
                        "Ponte de pie recto y presiona 'c' para calibrar",
                        (20, frame.shape[0] - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2,
                    )
                else:
                    state = sm.update(mid_3d[1], postura_ok)
                    obs.update(
                        fase=state["fase"],
                        desplazamiento_y=state["desplazamiento_y"],
                        repeticiones=state["repeticiones"],
                        postura_correcta=postura_ok,
                        rep_valid=state["rep_valid"],
                        rep_rejected=state["rep_rejected"],
                        rep_rejection_reason=state["rep_rejection_reason"],
                    )
                    last_sig, last_sent_ts, do_send = _should_send(obs, last_sig, last_sent_ts)
                    if do_send:
                        last_correction = _send(client, session_id, obs)
                    correction = last_correction

                    color = (0, 255, 0) if correction["level"] == "ok" else (0, 0, 255)
                    cv2.putText(frame, f"Fase: {state['fase']}", (20, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                    cv2.putText(frame, f"Descenso: {state['desplazamiento_y']:.2f}m", (20, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    cv2.putText(frame, f"Repeticiones: {state['repeticiones']}", (20, 90),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                    cv2.putText(frame, f"Postura: {'OK' if postura_ok else 'MALA'}", (20, 120),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                    cv2.putText(frame, correction["message_es"], (20, 150),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

                    last_message = _maybe_speak(
                        correction["message_es"], correction["level"],
                        state["rep_valid"], last_message, last_warn,
                    )
                    if correction["level"] != "ok":
                        last_warn = time.time()

                    if correction["siguiente_paso"] == "AVANZAR" and not completed:
                        completed = True
                        speak(correction["message_es"])
                        speak("Pulsa N para pasar al siguiente ejercicio, o C para continuar.")
            else:
                last_sig, last_sent_ts, do_send = _should_send(obs, last_sig, last_sent_ts)
                if do_send:
                    last_correction = _send(client, session_id, obs)
                correction = last_correction
                cv2.putText(frame, "HOMBROS NO VISIBLES", (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                last_message = _maybe_speak(
                    correction["message_es"], correction["level"],
                    False, last_message, last_warn,
                )
                if correction["level"] != "ok":
                    last_warn = time.time()

            cv2.imshow("Trackeo de Ejercicio", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                return False
            if key == ord("c") and hombros_visibles:
                sm.calibrate(mid_3d[1])
                speak("Altura calibrada. Comienza.")
            if completed and key == ord("n"):
                return True
    finally:
        tracker.release()
    return False


def run_session(client: ApiClient, session: dict, source, camera_params, non_interactive: bool = False) -> None:
    """Recorre las 3 fases del plan. Solo los ejercicios con plantilla se trackean."""
    plan = session["plan"]
    session_id = session["session_id"]
    speak("Plan cargado. Empieza la sesión.")
    for phase in PHASES:
        exercise = plan[phase]
        print(f"\nFase {phase}: {exercise}", flush=True)
        speak(f"Fase {phase}: {exercise}")
        template = _get_template(exercise)
        if template is None:
            if non_interactive or not sys.stdin.isatty():
                print("   (sin plantilla, continuando...)", flush=True)
                time.sleep(1)
                continue
            speak("Este ejercicio aún no tiene plantilla. Pulsa Enter para continuar.")
            try:
                input("   [Enter] para continuar...")
            except (EOFError, KeyboardInterrupt):
                continue
            continue
        avanzar = run_exercise(client, session_id, phase, exercise, template, source, camera_params)
        if not avanzar:
            speak("Sesión terminada.")
            break
    else:
        client.complete_session(session_id)
        speak("¡Sesión completada!")


def _get_template(exercise: str):
    from app.services.correction_service import get_template
    return get_template(exercise)
