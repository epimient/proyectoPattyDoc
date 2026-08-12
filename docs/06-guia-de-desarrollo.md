# Guía de desarrollo

## 1. Requisitos del entorno

| Requisito | Versión |
|-----------|---------|
| Python | 3.12+ (proyecto original: 3.13 en Windows) |
| pip | - |
| GPU | Opcional (si no hay, TensorFlow usa CPU) |

## 2. Instalación

```bash
# Crear entorno virtual
python3 -m venv venv

# Activar (Linux/macOS)
source venv/bin/activate
# Activar (Windows)
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### Dependencias

```text
# Modelo y datos
tensorflow==2.20.0
keras==3.15.1
pandas==3.0.5
numpy==2.5.2
scikit-learn==1.9.0
openpyxl==3.1.5

# Voz (app de escritorio / fase 2) - natural por defecto
gtts==2.5.4
pygame==2.6.1
edge-tts==7.0.2
pyttsx3==2.99
pywin32==312; sys_platform == "win32"

# Backend
fastapi==0.139.0
uvicorn[standard]==0.34.0
joblib==1.4.2

# Tests
pytest==8.3.5
httpx==0.28.1

# Fase 2: gemelo digital (app/vision)
opencv-python==4.11.0.86
pupil-apriltags==1.0.4.post11
```

> **Nota:** **Voz:** el detector usa `gTTS` (voz natural, necesita internet). Para voces neurales: `--tts edge` con `--tts-voice es-ES-ElviraNeural`. `pyttsx3` (offline) solo como respaldo; en Linux requiere `sudo apt install espeak-ng`.

## 3. Ejecución

### 3.1 Levantar el backend

```bash
./venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>

> **Nota:** Para silenciar los logs de TensorFlow en desarrollo: `TF_CPP_MIN_LOG_LEVEL=3`.

### 3.2 Ejecutar los tests

```bash
./venv/bin/python -m pytest -q
```

Los tests cubren:

| Archivo | Cubre |
|---------|-------|
| `tests/test_health_exercises.py` | `/api/health` y `/api/exercises` |
| `tests/test_plan.py` | `/api/plan`: generación, aliases, fallback y validación |
| `tests/test_feedback.py` | `/api/feedback`: sin reentrenar, reentrenamiento y no contaminación de artefactos |
| `tests/test_session.py` | Sesiones: crear, consultar, observaciones, historial, completar, abandonar, 404 y validación |
| `tests/test_correction.py` | Motor de corrección: rep válida, postura, profundidad, sin hombros, completado |
| `tests/test_engine.py` | Máquina de estados del detector (sin necesidad de cámara) |
| `tests/test_camera.py` | Endpoints de cámara, stream, calibración, avance manual, doble clic y conteo con tracker falso |

**Detalle clave:** los tests de feedback usan un servicio sobre **artefactos temporales** (`tmp_path`) y los de sesión un **SQLite temporal**, vía `app.dependency_overrides` -> los artefactos de producción (`artifacts/*`) quedan intactos.

## 4. Ejecución del detector (Fase 2)

Requisito: el backend corriendo.

```bash
# Crear sesión con un plan y empezar (cámara por defecto)
./venv/bin/python -m app.vision \
  --plan '{"calentamiento":"Marcha en el lugar con cuerda guía","entrenamiento":"Sentadillas asistidas con silla/barra","enfriamiento":"Respiraciones profundas"}'

# Unirse a una sesión existente
./venv/bin/python -m app.vision --session-id <id>

# Usar un archivo de video en vez de la webcam
./venv/bin/python -m app.vision --plan plan.json --source video.mp4

# Calibración de cámara personalizada
./venv/bin/python -m app.vision --plan plan.json --camera-params 900,900,640,360
```

**Teclas:** `c` calibrar postura; `n` siguiente ejercicio; `q` salir. El frontend solo envía cada comando cuando el estado lo permite y trata un `409` adelantado como no-op. La sentadilla se cuenta al completar de pie -> profundidad -> de pie; las etiquetas `0` y `1` deben permanecer visibles. La voz confirma cada repetición contada o rechazada y la finalización de la meta.

## 5. Scripts

### 5.1 `python -m scripts.export_artifacts`

Regenera `artifacts/preprocessors.pkl` desde `data/Datos generados con modelo.xlsx`.

```bash
./venv/bin/python -m scripts.export_artifacts
```

Salida esperada:

```text
Preprocesadores guardados en .../artifacts/preprocessors.pkl
Filas preprocesadas: 512
Clases por fase: {Fase1: 9, Fase2: 9, Fase3: 7}
```

**Cuándo usarlo:** si cambia el Excel, o para restaurar los preprocesadores a su estado original.

### 5.2 `python -m scripts.train`

Entrena el modelo desde el Excel y muestra la accuracy por fase sobre el test set.

```bash
./venv/bin/python -m scripts.train
```

Salida esperada (ejemplo):

```text
Calentamiento - Accuracy test: 78.00%
Entrenamiento - Accuracy test: 74.00%
Enfriamiento - Accuracy test: 85.00%
```

> **Advertencia:** El entrenamiento **sobrescribe** `artifacts/modelo5.keras`. Usa con cuidado.
> El feedback de la API crea un backup previo en `artifacts/backups/` antes de guardar artefactos reentrenados.

## 6. Estructura del código

```
app/
├── main.py                  # App FastAPI: CORS + lifespan (carga modelo y SQLite al arrancar)
├── core/config.py           # Rutas, orígenes CORS y base URL de la API
├── models/
│   ├── preprocessing.py     # preprocess_data, constantes de columnas
│   ├── neural.py            # build_model (arquitectura 128->64->3 salidas)
│   ├── artifacts.py         # save_artifacts / load_artifacts
│   ├── plan_service.py      # PlanService singleton: generate_plan, apply_feedback, list_exercises, health
│   └── session_store.py     # SessionStore: sesiones y observaciones en SQLite
├── schemas/
│   ├── plan.py              # Contratos Pydantic (UserProfile, PlanResponse, Feedback...)
│   └── session.py           # Contratos Pydantic (Plan, ObservationRequest, CorrectionResponse...)
├── services/correction_service.py  # Motor de corrección (reglas por plantilla)
├── routers/
│   ├── plan.py              # /api/plan, /api/exercises, /api/feedback, /api/health
│   └── session.py           # /api/session/start, /{id}, /observation, /observations, /complete
└── vision/                  # Gemelo digital (ver docs/05)
```

## 7. Cómo agregar un endpoint nuevo

1. Definir los contratos Pydantic en `app/schemas/` (o un schema nuevo).
2. Añadir la lógica en el servicio correspondiente (`PlanService` o `SessionStore`).
3. Registrar la ruta en `app/routers/` usando `Depends(get_service)` / `Depends(get_store)`.
4. Escribir un test en `tests/`.

## 8. Convenciones

- Respuestas y mensajes en **español**.
- Funciones con tipado (`def f(...) -> tipo`).
- Uso de `Depends(get_service)` (no acceder al singleton directamente en los routers).
- Guard clauses (early return) en los handlers.
- No commitear `venv/` ni artefactos generados a menos que se pida explícitamente.

## 9. Preguntas frecuentes

**¿Por qué `/api/exercises` usa claves con mayúscula y `/api/plan` minúsculas?**
`/api/exercises` respeta los nombres de fase del dataset (`Calentamiento`); `/api/plan` usa el contrato JSON definido (`calentamiento`). Está documentado en [`03-api.md`](03-api.md#43-get-apiexercises--catálogo-de-ejercicios).

**¿El feedback modifica el modelo de producción?**
Sí, por diseño (es el objetivo del reentrenamiento). Para probar sin efectos, la suite de tests usa artefactos temporales.

**¿Qué pasa si llega un valor categórico desconocido?**
Se sustituye por el valor más frecuente de esa columna (ver defaults en [`01-modelo-de-ia.md`](01-modelo-de-ia.md#5-artefactos)).
