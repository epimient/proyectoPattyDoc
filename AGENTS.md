# AGENTS.md — proyectoPattyDoc

## Quick reference

| Task | Command |
|------|---------|
| **Dev servers (API + front)** | `scripts/dev.sh` |
| **API only** | `./venv/bin/python -m uvicorn app.main:app --reload --port 8000` |
| **Front only** | `cd frontend && npm run dev` |
| **Run all tests** | `./venv/bin/python -m pytest -q` |
| **Run single test file** | `./venv/bin/python -m pytest tests/test_camera.py -q` |
| **Regenerate artifacts from Excel** | `./venv/bin/python -m scripts.export_artifacts` |
| **Train model** | `./venv/bin/python -m scripts.train` |

## Architecture at a glance

- **API** (`app/`): FastAPI + Uvicorn on :8000. Endpoints: `/api/plan`, `/api/session`, `/api/camera/*`.
- **Frontend** (`frontend/`): React + Vite on :5173, proxies `/api` → `http://127.0.0.1:8000` (see `vite.config.js`).
- **Gemelo digital** (`app/vision/`): `CameraController` runs camera in a daemon thread inside the API process; exposes MJPEG stream (`/api/camera/stream`) and state (`/api/camera/state`).
- **CLI detector** (`app/vision/detector.py`): standalone OpenCV loop with TTS (used for video-file debugging).
- **Sessions**: SQLite via `SessionStore` (`data/sessions.db`).
- **Model artifacts**: `artifacts/modelo5.keras` + `artifacts/preprocessors.pkl`.

## Key conventions & gotchas

1. **CameraController is a singleton** (`app/vision/controller.py:401`). Its `__init__` injects `tracker_factory` and `store_getter` — **dependency_overrides don't apply to direct `get_store()` calls**; tests pass a custom `store_getter` lambda.

2. **TTS priority**: `gTTS` → `edge-tts` → `pyttsx3`. `edge-tts` returns 403 in sandbox; `pyttsx3` segfaults here (exit 139). `gTTS` is the reliable default. Env vars: `PATTYDOC_TTS`, `PATTYDOC_TTS_VOICE`.

3. **Template matching** (`app/services/correction_service.py:30-42`): `_normalize` strips accents/lowercases; `get_template` does bidirectional substring match (so `"(Fuerza y Resistencia) Sentadillas..."` matches `"Sentadillas asistidas..."`).

4. **Frontend**: `StrictMode` disabled in `main.jsx` to avoid double `startCamera`. Web Speech API used for voice (not server TTS).

5. **Camera source**: `CAMERA_SOURCE` in `app/core/config.py` defaults to `0` (first webcam). `scripts/dev.sh` starts API on `8000` + front on `5173`.

6. **Test fixtures** (`tests/conftest.py`): `client` (session-scoped TestClient), `service` (isolated PlanService), `override_service`, `session_store` (tmp SQLite). Camera tests use `FakeCameraController` for endpoints + `FakeTracker` for real loop tests.

7. **Cleanup**: `scripts/dev.sh` traps EXIT/INT/TERM to kill API. Orphan Vite on 5173 can persist — `pkill -f "vite"` if needed.

## Environment

- Python 3.13 (venv at `./venv`)
- TensorFlow 2.20 / Keras 3.15 (no GPU in this env; CUDA warnings in logs are harmless)
- Frontend: Node + Vite 6

## Common tasks

- **Add a new exercise template**: edit `data/exercise_templates.json` (keys must match plan output names; fuzzy match handles category prefixes).
- **Change camera source**: set `CAMERA_SOURCE` in `app/core/config.py` or pass `?source=...` to `POST /api/camera/start`.
- **Run with test video**: pass `source=/tmp/opencode/test.mp4` to start endpoint.

## Files worth knowing

| File | Purpose |
|------|---------|
| `app/vision/controller.py` | CameraController (threaded camera loop, state machine, MJPEG) |
| `app/services/correction_service.py` | Template loading, fuzzy match, correction logic |
| `app/vision/engine.py` | SquatStateMachine (reps counting) |
| `frontend/src/components/SessionView.jsx` | Orchestrates camera/voice/buttons |
| `scripts/dev.sh` | One-command dev stack |

## Test suite

```bash
./venv/bin/python -m pytest -q          # all (38 tests)
./venv/bin/python -m pytest tests/test_camera.py -q  # camera endpoints + loop
```

Tests isolate via `dependency_overrides` for `get_service` and `get_store`; `CameraController` tests inject `tracker_factory` and `store_getter` directly.