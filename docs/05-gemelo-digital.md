# 🎥 Fase 2 — Gemelo digital (detección de tags y corrección por voz)

> **Estado:** MVP implementado (sentadilla). Backend de sesiones ✅ · Motor de corrección ✅ · Detector de escritorio ✅ · Voz (TTS) ✅ · Plantillas: 1 de 25 ejercicios.

## 1. Visión de la solución

El flujo completo del producto es:

```
1. El usuario genera su plan  →  POST /api/plan
2. Pulsa "Comenzar"
3. Se activa la cámara; la persona lleva tags (AprilTags) en los hombros
4. El detector evalúa si ejecuta bien el ejercicio
5. El sistema le habla, corrigiendo postura y contando repeticiones
```

## 2. El detector actual (`detector_tags (1).py`)

> 📦 El prototipo original se archivó en `archived/detector_tags_v1.py` tras refactorizarlo a `app/vision/`. Demostró la mecánica de una **sentadilla** con AprilTags en los hombros:

| Aspecto | Detalle |
|---------|---------|
| Librería | `pupil_apriltags` (familia `tag36h11`) |
| Cámara | `cv2.VideoCapture(0)` |
| Tags | ID 0 = hombro izquierdo, ID 1 = hombro derecho |
| Tag size | 0.05 m |
| Cámara (params) | `[600, 600, 320, 240]` (fx, fy, cx, cy) |
| Pose | `detector.detect(gray, estimate_tag_pose=True, …)` → `pose_t` (traslación 3D) |
| Lógica | Punto medio de hombros + máquina de estados de sentadilla |
| Salida actual | Overlay con IDs, fase y repeticiones; voz en CLI y navegador |

### 2.1 Máquina de estados de la sentadilla

```
ESPERANDO → (calibración tecla 'c') → DE_PIE
DE_PIE  --descenso > 0.1m-->  BAJANDO
BAJANDO --descenso ≥ 0.35m--> SQUAT_PROFUNDO
SQUAT_PROFUNDO --subida < 0.15m--> (postura OK?) repeticiones++ → DE_PIE
```

### 2.2 Calibración y conteo

Al iniciar un ejercicio compatible, el usuario se pone de pie y pulsa **Calibrar postura** (o `c` en CLI). El detector requiere dos AprilTags de familia `tag36h11`: ID `0` en el hombro izquierdo e ID `1` en el derecho. Cuando ambas tienen pose 3D válida, guarda el punto medio vertical como `y_inicial`.

La interfaz expone `calibration_requested`, `detected_tags`, `hombros_visibles` y `calibrado`. Mientras busca, informa si no ve ninguna etiqueta, si falta una o si reconoce el patrón pero no puede estimar su pose.

Una repetición solo se cuenta al completar el ciclo **DE_PIE → BAJANDO → SQUAT_PROFUNDO → DE_PIE**. Alcanzar `0.35 m` llena el indicador de profundidad, pero el conteo ocurre al volver por debajo de `0.15 m` con postura válida y ambas etiquetas visibles.

### 2.3 Estado y limitaciones actuales

| Área | Estado |
|------|--------|
| Refactor a `app/vision/*` | Implementado |
| Voz | Implementada: Web Speech API en web; gTTS/edge-tts/pyttsx3 en CLI |
| Diagnóstico por pérdida de tags | Implementado: IDs visibles y mensajes según fase |
| Ejercicios sin plantilla | Implementado como guiado manual con avance explícito |
| Seguimiento automático | Limitado a sentadilla asistida (1 plantilla) |
| Parámetros intrínsecos de cámara | Valores aproximados; falta calibración checkerboard real |
| Velocidad y ritmo | Pendiente |

## 3. Implementación actual (`app/vision`)

```
app/vision/
├── __main__.py      # CLI: python -m app.vision --plan ... --source 0
├── detector.py      # Loop principal: tracking + envía observaciones + habla correcciones
├── engine.py        # SquatStateMachine (máquina de estados + ángulo de hombros)
├── tracker.py       # CameraTracker: cámara/video + detección AprilTags (pose 3D)
├── api_client.py    # Cliente HTTP mínimo (stdlib) hacia el backend
└── tts.py           # Voz natural en español (gTTS → edge-tts → pyttsx3)
```

**Diseño de la arquitectura (backend evalúa):**

```
Frontend Web ──POST /api/plan──► FastAPI ◄── Detector (desktop, cámara+tags)
   (plan JSON)                          │
        │                               │  POST /api/session/start → session_id
        └── "Comenzar" ───────────────► Detector
                                         │
                                         ├─ POST /api/session/{id}/observation
                                         │        (fase, desplazamiento, postura, reps)
                                         │              ▼
                                         │   Backend evalúa contra exercise_templates.json
                                         │              ▼
                                         └─ {level, message_es, siguiente_paso}
                                               Detector habla la corrección
```

- El **detector** mantiene la máquina de estados en local (necesita la fase en tiempo real para el overlay y el conteo de reps) y envía observaciones cada frame.
- El **backend** aplica las reglas de la plantilla y decide la corrección (`level`, `message_es`, `siguiente_paso`).
- La **voz** la emite el detector con `app/vision/tts.py` (solo en transiciones relevantes y con cooldown, para no repetir).

### 3.0 Interfaz web (recomendada)

Desde la Fase 2 hay una **interfaz web** (React + Vite) que reemplaza la ventana
de OpenCV como forma principal de interactuar:

```
Navegador (:5173)  ──POST /api/plan──►  API (:8000)
   │  (perfil del usuario)                    │ modelo5.keras
   │  ◄── plan (3 ejercicios) ────────────────┘
   │  ──POST /api/camera/start {plan}──►  arranca el hilo de cámara
   │  ◄── GET /api/camera/stream ───────  MJPEG con tags dibujados
   │  ◄── GET /api/camera/state ─────────  polling (fase, reps, corrección)
   │  ──POST /api/camera/calibrate|next|stop──►  comandos
   Voz: speechSynthesis (es-ES) en el navegador
```

- **La cámara la lee la API** (server-side, igual que el CLI): `CameraController`
  (`app/vision/controller.py`) corre el detector en un hilo dentro de FastAPI y
  publica el último frame anotado como JPEG.
- El backend evalúa en-proceso (`evaluate_correction`) y guarda observaciones en
  `session_store`; el navegador **habla** los mensajes con Web Speech API.
- Botones: **Calibrar postura (C)**, **Siguiente (N)**, **Terminar (Q)**. Diseño de alto
  contraste, orientado a voz ("consola audible").
- Los ejercicios sin plantilla no se saltan: se muestran como **Guiado manual** y esperan **Siguiente**.
- **Probar sentadillas con cámara** fuerza temporalmente la sentadilla en entrenamiento sin cambiar el plan recomendado.
- El visor MJPEG usa relación 4:3 y muestra el cuadro completo sin recorte.
- El panel muestra IDs detectados, solicitud de calibración, visibilidad, fase, profundidad y repeticiones.
- Levantar todo: `scripts/dev.sh` (API :8000 + front :5173 con proxy `/api`).
  Ver `docs/07-frontend.md`.

### 3.1 Uso (CLI)

```bash
# 1. Backend corriendo (uvicorn)
# 2. Ejecutar el detector con un plan:
./venv/bin/python -m app.vision \
  --plan '{"calentamiento":"Marcha en el lugar con cuerda guía","entrenamiento":"Sentadillas asistidas con silla/barra","enfriamiento":"Respiraciones profundas"}'

# O unirse a una sesión ya creada:
./venv/bin/python -m app.vision --session-id <id>

# O con video en vez de cámara (para probar sin webcam):
./venv/bin/python -m app.vision --plan plan.json --source video.mp4
```

**Teclas durante la ejecución:**
| Tecla | Acción |
|-------|--------|
| `c` | Calibrar postura inicial con las etiquetas 0 y 1 visibles |
| `n` | Pasar al siguiente ejercicio (cuando se completa la meta) |
| `q` | Salir |

**Voz (TTS):** el detector habla en español con una **voz natural**. Por defecto usa `gTTS` (Google, requiere internet); si se instala `edge-tts` puede cambiarse con `--tts edge` (voces neurales como `es-ES-ElviraNeural`). `pyttsx3` queda solo como respaldo offline. Caché local de audio en `data/tts_cache/`.

- `--tts gtts|edge|pyttsx3` elige el motor (por defecto `gtts`).
- `--tts-voice es-XX-NombreNeural` elige la voz para edge-tts.
- Si `gTTS`/`edge` fallan o no hay internet, degrada automáticamente a `pyttsx3`.

## 4. Plantillas de ejercicio

Las plantillas viven en `data/exercise_templates.json` y son la **fuente única** de parámetros (las leen tanto el backend para las reglas como el detector para la máquina de estados). Hoy está implementada la **sentadilla**:

```json
{
  "Sentadillas asistidas con silla/barra": {
    "mecanica": "squat",
    "profundidad_objetivo_m": 0.35,
    "descenso_inicio_m": 0.1,
    "subida_completa_m": 0.15,
    "tolerancia_hombros_deg": 10,
    "repeticiones_objetivo": 10,
    "mensajes": {
      "ok": "Excelente, repetición válida ({reps}/{objetivo})",
      "postura": "Sube con la espalda recta, mantén los hombros nivelados",
      "profundidad": "Baja un poco más para completar la sentadilla",
      "hombros_no_visibles": "Colócate frente a la cámara para que pueda ver tus hombros",
      "completado": "¡Sentadillas completadas! Meta: {objetivo} repeticiones"
    }
  }
}
```

Para añadir un ejercicio nuevo basta con agregar su plantilla (y, cuando aplique, una nueva mecánica en `app/vision/engine.py`). Los placeholders `{reps}` y `{objetivo}` se interpolan en las reglas.

## 5. Corrección por voz

Para usuarios con discapacidad visual, la salida principal es **audio**:

| Opción | Dónde corre | Pros |
|--------|-------------|------|
| `gTTS` (predeterminado) | App escritorio | Voz natural en español, simple |
| `edge-tts` (`--tts edge`) | App escritorio | Voces neurales muy naturales |
| `pyttsx3` | App escritorio | Sin conexión, voz local (respaldo) |
| Web Speech API (`speechSynthesis`) | Navegador | Sin backend TTS |

El backend devuelve `message_es` y el cliente decide cómo reproducirlo.

## 6. Seguridad y privacidad

- La cámara se activa **únicamente** al pulsar "Comenzar" y con consentimiento explícito.
- Idealmente el procesamiento de video ocurre **en local** (app de escritorio), enviando solo métricas agregadas al backend, no frames.
- Los `session_id` deben ser aleatorios/no adivinables.
