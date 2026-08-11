from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
ARTIFACTS_DIR = BASE_DIR / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "modelo5.keras"
PREPROCESSORS_PATH = ARTIFACTS_DIR / "preprocessors.pkl"
DATA_PATH = BASE_DIR / "data" / "Datos generados con modelo.xlsx"
TEMPLATES_PATH = BASE_DIR / "data" / "exercise_templates.json"
SESSIONS_DB_PATH = BASE_DIR / "data" / "sessions.db"

API_BASE_URL = "http://127.0.0.1:8000"

# Fuente de video por defecto para el controlador de cámara (0 = webcam).
CAMERA_SOURCE = 0

CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
