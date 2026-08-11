import argparse
import json
import os

from app.core.config import API_BASE_URL
from app.vision.api_client import ApiClient
from app.vision.detector import run_session
from app.vision.tracker import DEFAULT_CAMERA_PARAMS


def _parse_camera_params(value: str):
    parts = value.split(",")
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("Formato esperado: fx,fy,cx,cy")
    return [float(p) for p in parts]


def _load_plan(raw: str) -> dict:
    if os.path.exists(raw):
        with open(raw, encoding="utf-8") as f:
            return json.load(f)
    return json.loads(raw)


def main():
    parser = argparse.ArgumentParser(
        description="PattyDoc - Detector de ejercicios (gemelo digital). "
        "Requiere un backend FastAPI corriendo en --base-url.",
    )
    parser.add_argument("--plan", help="Plan JSON (inline o ruta a archivo) para crear sesión")
    parser.add_argument("--session-id", help="Unirse a una sesión existente (ignora --plan)")
    parser.add_argument("--base-url", default=API_BASE_URL, help="URL del backend")
    parser.add_argument("--source", default=0, help="Fuente: 0 para webcam o ruta a video")
    parser.add_argument(
        "--camera-params",
        type=_parse_camera_params,
        default=DEFAULT_CAMERA_PARAMS,
        help="fx,fy,cx,cy de la cámara",
    )
    parser.add_argument(
        "--tts",
        choices=["gtts", "edge", "pyttsx3"],
        default=None,
        help="Motor de voz: gtts (Google, recomendado) | edge (Microsoft) | pyttsx3 (offline)",
    )
    parser.add_argument(
        "--tts-voice",
        default="es-MX-DaliaNeural",
        help="Voz para edge-tts (ej: es-ES-ElviraNeural, es-AR-ElenaNeural)",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="No esperar Enter en ejercicios sin plantilla (útil con video/automatización)",
    )
    args = parser.parse_args()

    if not args.session_id and not args.plan:
        parser.error("Se requiere --plan o --session-id")

    if args.tts:
        os.environ["PATTYDOC_TTS"] = args.tts
    os.environ["PATTYDOC_TTS_VOICE"] = args.tts_voice

    client = ApiClient(args.base_url)
    if args.session_id:
        session = client.get_session(args.session_id)
    else:
        plan = _load_plan(args.plan)
        session = client.start_session(plan)

    print(f"Sesión: {session['session_id']}", flush=True)
    run_session(client, session, args.source, args.camera_params, non_interactive=args.non_interactive)


if __name__ == "__main__":
    main()
