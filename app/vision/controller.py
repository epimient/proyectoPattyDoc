"""Controlador de cámara para el flujo web.

El detector de tags corre dentro del proceso FastAPI (hilo daemon), publica el
último frame anotado como JPEG y expone un estado en tiempo real. El frontend
solo muestra el stream (MJPEG) y envía comandos (calibrar/next/stop).

Reutiliza la misma lógica de visión que el CLI (app/vision/detector.py): la
evaluación se hace en-proceso con `evaluate_correction` + `session_store`, sin
HTTP interno.
"""

import threading
import time

import cv2
import numpy as np

from app.models.session_store import get_store
from app.schemas.session import ObservationRequest
from app.services.correction_service import evaluate_correction, get_template
from app.vision.engine import SquatStateMachine, shoulder_angle
from app.vision.tracker import ID_HOMBRO_DER, ID_HOMBRO_IZQ, CameraTracker

PHASES = ["calentamiento", "entrenamiento", "enfriamiento"]
FRAME_INTERVAL_S = 0.03


def _placeholder_jpeg() -> bytes:
    img = np.full((480, 640, 3), 18, np.uint8)
    cv2.putText(img, "Camara apagada", (150, 230), cv2.FONT_HERSHEY_SIMPLEX, 1.3, (255, 255, 255), 2)
    cv2.putText(img, "Empieza una sesion para activarla", (120, 275), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (210, 210, 210), 1)
    ok, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def _default_state() -> dict:
    return {
        "status": "idle",  # idle | running | waiting_next | completed | stopped | error
        "session_id": None,
        "plan": None,
        "phase": None,
        "exercise": None,
        "fase": "",
        "repeticiones": 0,
        "objetivo": 0,
        "desplazamiento_y": 0.0,
        "postura_ok": True,
        "hombros_visibles": False,
        "calibrado": False,
        "tracking_available": False,
        "calibration_requested": False,
        "detected_tags": [],
        "correction": {"level": "ok", "message_es": "Sin actividad", "siguiente_paso": "CONTINUAR"},
        "error": None,
        "completed_naturally": False,
    }


class CameraController:
    """Singleton que ejecuta el loop de cámara en un hilo propio."""

    def __init__(self, tracker_factory=None, source=0, store_getter=None):
        self._factory = tracker_factory or CameraTracker
        self._default_source = source
        self._store_getter = store_getter or get_store
        self._lock = threading.Lock()
        self._state = _default_state()
        self._jpeg = _placeholder_jpeg()
        self._stop = threading.Event()
        self._calibrate = threading.Event()
        self._next = threading.Event()
        self._thread = None
        self._tracker = None

    # ---------------------------------------------------------------- API

    @property
    def state(self) -> dict:
        with self._lock:
            return dict(self._state)

    def get_frame(self) -> bytes:
        with self._lock:
            return self._jpeg

    def start(self, plan: dict, source=None) -> dict:
        source = self._default_source if source is None else source
        with self._lock:
            if self._state["status"] in ("running", "waiting_next"):
                raise RuntimeError("Ya hay una sesión en curso")
            try:
                tracker = self._factory(source=source)
            except Exception as e:  # noqa: BLE001
                raise RuntimeError(str(e)) from e
            store = self._store_getter()
            try:
                session = store.create_session(plan)
            except Exception:
                tracker.release()
                raise
            self._stop.clear()
            self._calibrate.clear()
            self._next.clear()
            self._state = _default_state()
            self._state.update(
                {
                    "status": "running",
                    "session_id": session["session_id"],
                    "plan": plan,
                }
            )
            self._thread = threading.Thread(
                target=self._run, args=(plan, tracker), daemon=True
            )
            self._thread.start()
            return dict(self._state)

    def calibrate(self) -> dict:
        with self._lock:
            if self._state["status"] != "running" or not self._state["tracking_available"]:
                raise RuntimeError("El ejercicio actual no admite calibración")
            if self._state["calibrado"]:
                raise RuntimeError("La postura ya está calibrada")
            self._state["calibration_requested"] = True
            self._state["correction"] = {
                "level": "info",
                "message_es": "Buscando las etiquetas 0 y 1. Muestra ambas a la cámara.",
                "siguiente_paso": "MOSTRAR_ETIQUETAS",
            }
        self._calibrate.set()
        return self.state

    def next(self) -> dict:
        with self._lock:
            if self._state["status"] != "waiting_next":
                raise RuntimeError("No hay ejercicio completado esperando Siguiente")
            # Deshabilita el control inmediatamente y evita que un doble clic
            # adelante también el ejercicio siguiente.
            self._state["status"] = "running"
        self._next.set()
        return self.state

    def stop(self) -> dict:
        with self._lock:
            if self._state["status"] in ("idle", "completed", "stopped", "error"):
                raise RuntimeError("No hay sesión activa")
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        return self.state

    def shutdown(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._thread = None

    # ------------------------------------------------------------ internals

    def _run(self, plan: dict, tracker):
        self._tracker = tracker
        try:
            self._loop(plan, tracker)
        except Exception as e:  # noqa: BLE001
            self._fail(str(e))
        finally:
            tracker.release()
            self._tracker = None
            with self._lock:
                if self._state["status"] in ("running", "waiting_next"):
                    self._state["status"] = "stopped"

    def _loop(self, plan: dict, tracker):
        store = self._store_getter()
        session_id = self._state["session_id"]
        for phase in PHASES:
            if self._stop.is_set():
                return
            exercise = plan[phase]
            self._update_state(
                phase=phase,
                exercise=exercise,
                fase="",
                calibrado=False,
                tracking_available=False,
                calibration_requested=False,
                detected_tags=[],
                repeticiones=0,
                objetivo=0,
                correction={
                    "level": "info",
                    "message_es": f"Fase {phase}: {exercise}",
                    "siguiente_paso": "CONTINUAR",
                },
            )
            template = get_template(exercise)
            if template is None:
                self._update_state(
                    status="waiting_next",
                    fase="MANUAL",
                    correction={
                        "level": "info",
                        "message_es": (
                            f"Realiza {exercise} a tu ritmo. "
                            "Cuando termines, pulsa Siguiente."
                        ),
                        "siguiente_paso": "NEXT",
                    }
                )
                if not self._wait_next(tracker):
                    return
                self._update_state(status="running")
                continue
            keep = self._run_exercise(tracker, session_id, phase, exercise, template)
            if not keep:
                return
        store.complete_session(session_id)
        self._update_state(
            status="completed",
            completed_naturally=True,
            correction={
                "level": "ok",
                "message_es": "¡Sesión completada!",
                "siguiente_paso": "FIN",
            },
        )

    def _run_exercise(self, tracker, session_id, phase, exercise, template) -> bool:
        sm = SquatStateMachine(template)
        objetivo = template["repeticiones_objetivo"]
        self._update_state(
            fase="ESPERANDO",
            calibrado=False,
            tracking_available=True,
            calibration_requested=False,
            detected_tags=[],
            repeticiones=0,
            objetivo=objetivo,
            desplazamiento_y=0.0,
            postura_ok=True,
            correction={
                "level": "info",
                "message_es": "Ponte de pie frente a la cámara y pulsa Calibrar.",
                "siguiente_paso": "CALIBRAR",
            },
        )

        while not self._stop.is_set():
            frame, det = tracker.read()
            if frame is None:
                return False
            hombros = self._shoulders(det)
            tag_ids = self._tag_ids(det)
            self._draw_and_publish(frame, det)
            self._update_state(hombros_visibles=bool(hombros), detected_tags=tag_ids)
            if self._calibrate.is_set() and not hombros:
                self._update_state(correction=self._calibration_correction(tag_ids))
            if self._calibrate.is_set() and hombros:
                self._calibrate.clear()
                sm.calibrate(hombros[2][1])
                self._update_state(
                    calibrado=True,
                    calibration_requested=False,
                    fase="DE_PIE",
                    correction={
                        "level": "info",
                        "message_es": "Calibrado. Comienza.",
                        "siguiente_paso": "CONTINUAR",
                    },
                )
                break
            time.sleep(FRAME_INTERVAL_S)
        if self._stop.is_set():
            return False

        completed = False
        while not self._stop.is_set():
            frame, det = tracker.read()
            if frame is None:
                return False
            hombros = self._shoulders(det)
            obs = self._make_obs(exercise, hombros)

            if hombros:
                p_izq, p_der, mid_3d, mid_2d = hombros
                angulo = abs(shoulder_angle(p_izq, p_der))
                postura_ok = angulo < template["tolerancia_hombros_deg"]
                state = sm.update(mid_3d[1], postura_ok)
                obs.update(
                    fase=state["fase"],
                    desplazamiento_y=state["desplazamiento_y"],
                    repeticiones=state["repeticiones"],
                    postura_correcta=postura_ok,
                )
                correction = evaluate_correction(
                    exercise, ObservationRequest(**obs)
                ).model_dump()
                if (
                    state["fase"] == "SQUAT_PROFUNDO"
                    and postura_ok
                    and not state["rep_valid"]
                ):
                    correction = {
                        "level": "info",
                        "message_es": "Profundidad alcanzada. Ahora vuelve a estar de pie para contar la repetición.",
                        "siguiente_paso": "SUBIR",
                    }
                self._record_observation(session_id, obs, correction)
                self._update_state(
                    fase=state["fase"],
                    desplazamiento_y=state["desplazamiento_y"],
                    repeticiones=state["repeticiones"],
                    postura_ok=postura_ok,
                    hombros_visibles=True,
                    detected_tags=self._tag_ids(det),
                    calibrado=True,
                    correction=correction,
                )
                if state["rep_valid"]:
                    self._update_state(correction=correction)
                if correction["siguiente_paso"] == "AVANZAR" and not completed:
                    completed = True
                    self._update_state(
                        status="waiting_next",
                        correction={
                            "level": "ok",
                            "message_es": "¡Ejercicio completado! Pulsa Siguiente.",
                            "siguiente_paso": "NEXT",
                        },
                    )
                    if not self._wait_next(tracker):
                        return False
                    self._update_state(status="running")
                    return True
            else:
                tag_ids = self._tag_ids(det)
                if sm.fase == "SQUAT_PROFUNDO":
                    message = (
                        "Profundidad alcanzada. Mantén visibles las etiquetas y vuelve "
                        "a estar de pie para contar la repetición."
                    )
                elif ID_HOMBRO_IZQ in tag_ids and ID_HOMBRO_DER in tag_ids:
                    message = (
                        "Veo las etiquetas 0 y 1, pero no puedo calcular su posición. "
                        "Ponlas planas, de frente y sin reflejos."
                    )
                else:
                    message = "Colócate frente a la cámara para que pueda ver las etiquetas 0 y 1"
                correction = {
                    "level": "error",
                    "message_es": message,
                    "siguiente_paso": "CONTINUAR",
                }
                self._record_observation(session_id, obs, correction)
                self._update_state(
                    hombros_visibles=False,
                    detected_tags=self._tag_ids(det),
                    correction=correction,
                )

            self._draw_and_publish(frame, det)
            time.sleep(FRAME_INTERVAL_S)
        return False

    def _wait_next(self, tracker) -> bool:
        while not self._stop.is_set() and not self._next.is_set():
            frame, det = tracker.read()
            if frame is None:
                return False
            self._draw_and_publish(frame, det)
            time.sleep(FRAME_INTERVAL_S)
        if self._stop.is_set():
            return False
        self._next.clear()
        return True

    # -------------------------------------------------------------- helpers

    
    def _tag_ids(self, det: dict) -> list[int]:
        return sorted(
            int(tag_id)
            for tag_id in det.get("detected_ids", det.get("positions_3d", {}))
        )

    
    def _calibration_correction(self, tag_ids: list[int]) -> dict:
        found = set(tag_ids)
        missing = [tag_id for tag_id in (ID_HOMBRO_IZQ, ID_HOMBRO_DER) if tag_id not in found]
        if not tag_ids:
            message = "No detecto etiquetas. Acerca las AprilTag 0 y 1 y evita reflejos."
        elif len(missing) == 1:
            message = f"Detecté {tag_ids}. Falta la etiqueta {missing[0]}."
        else:
            message = f"Detecté {tag_ids}, pero necesito las etiquetas 0 y 1."
        return {
            "level": "warning",
            "message_es": message,
            "siguiente_paso": "MOSTRAR_ETIQUETAS",
        }


    def _shoulders(self, det):
        positions = det["positions_3d"]
        centers = det["centers_2d"]
        if ID_HOMBRO_IZQ in positions and ID_HOMBRO_DER in positions:
            p_izq = positions[ID_HOMBRO_IZQ]
            p_der = positions[ID_HOMBRO_DER]
            mid_3d = (p_izq + p_der) / 2.0
            mid_2d = (
                int((centers[ID_HOMBRO_IZQ][0] + centers[ID_HOMBRO_DER][0]) / 2),
                int((centers[ID_HOMBRO_IZQ][1] + centers[ID_HOMBRO_DER][1]) / 2),
            )
            return p_izq, p_der, mid_3d, mid_2d
        return None

    def _make_obs(self, exercise: str, hombros) -> dict:
        return {
            "exercise": exercise,
            "frame_ts": time.time(),
            "fase": "",
            "desplazamiento_y": 0.0,
            "postura_correcta": True,
            "hombros_visibles": bool(hombros),
            "repeticiones": 0,
        }

    def _record_observation(self, session_id: str, obs: dict, correction: dict):
        try:
            store = self._store_getter()
            store.add_observation(session_id, obs, correction)
            store.set_current_exercise(session_id, obs["exercise"])
        except Exception as e:  # noqa: BLE001
            print(f"[camera] No se pudo guardar observación: {e}", flush=True)

    def _draw_and_publish(self, frame, det):
        CameraTracker.draw_tags(frame, det["corners"])
        with self._lock:
            st = self._state
        y = 30
        if not det["positions_3d"]:
            cv2.putText(frame, "HOMBROS NO VISIBLES", (20, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            y += 28
        if st["exercise"]:
            cv2.putText(
                frame,
                f"{st['phase']}: {st['exercise'][:38]}",
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 0), 1,
            )
            y += 24
        if st["fase"]:
            color = (0, 255, 0) if st["postura_ok"] else (0, 0, 255)
            cv2.putText(
                frame,
                f"Fase: {st['fase']}  Reps: {st['repeticiones']}/{st['objetivo']}",
                (20, y),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2,
            )
        message = st["correction"].get("message_es", "")
        if message:
            cv2.putText(
                frame,
                message[:52],
                (20, frame.shape[0] - 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 1,
            )
        ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if ok:
            with self._lock:
                self._jpeg = buf.tobytes()

    def _update_state(self, **kwargs):
        with self._lock:
            self._state.update(kwargs)

    def _fail(self, message: str):
        with self._lock:
            self._state["status"] = "error"
            self._state["error"] = message
        print(f"[camera] Error: {message}", flush=True)


controller = CameraController(source=0)
