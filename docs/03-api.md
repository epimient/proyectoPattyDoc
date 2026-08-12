# API - Referencia completa

## 1. Información general

| Propiedad | Valor |
|-----------|-------|
| **Base URL** | `http://127.0.0.1:8000` |
| **Esquema** | HTTP/REST |
| **Formato** | JSON (`application/json`) |
| **Framework** | FastAPI |
| **Documentación interactiva** | `GET /docs` (Swagger UI); `GET /redoc` |
| **Prefijo común** | `/api` |
| **Autenticación** | No requerida (API interna del proyecto) |

## 2. Estructura de respuesta

### 2.1 Respuestas exitosas
Se devuelve el cuerpo JSON del contrato correspondiente al endpoint (ver secciones por endpoint) con código `200 OK`.

### 2.2 Errores (códigos HTTP)

| Código | Significado | Cuándo ocurre |
|--------|-------------|---------------|
| `422` | **Error de validación** | El cuerpo no cumple el contrato: falta un campo, tipo incorrecto o valor fuera de rango |
| `503` | **Servicio no disponible** | El modelo no está cargado en memoria (p. ej. `modelo5.keras` o `preprocessors.pkl` ausentes al arrancar) |
| `422` (con mensaje) | **Error de generación** | Fallo interno al preprocesar/predictir (mismo código, `detail` descriptivo) |
| `500` | **Error interno** | Excepción no controlada |

### 2.3 Formato del error de validación (`422`)

FastAPI/Pydantic devuelven una lista de errores. Ejemplo (falta el campo `IMC`):

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "IMC"],
      "msg": "Field required",
      "input": { "Edad": 51 }
    }
  ]
}
```

Campos relevantes de cada elemento:

| Campo | Descripción |
|-------|-------------|
| `type` | Tipo de error (`missing`, `int_type`, `float_type`, `greater_than_equal`, `less_than_equal`, ...) |
| `loc` | Ruta del campo fallido (`["body", "<campo>"]`) |
| `msg` | Descripción legible |
| `input` | Valor recibido que falló |

### 2.4 Errores de negocio

```json
{
  "detail": "Error generando plan: <mensaje>"
}
```

## 3. Contrato del perfil de usuario (`UserProfile`)

Este objeto es el cuerpo de `POST /api/plan` y parte de `POST /api/feedback`.

### 3.1 Nombres de campo

La API acepta **dos convenciones** para cada campo (aliases):

| Campo (alias en español) | Atributo (snake_case) | Tipo | Validación |
|--------------------------|------------------------|------|-----------|
| `Edad` | `edad` | `int` | `10 <= x <= 120` |
| `Género` | `genero` | `str` | - |
| `IMC` | `imc` | `float` | `10 <= x <= 70` |
| `Nivel de Visión` | `nivel_vision` | `str` | - |
| `Condición Física` | `condicion_fisica` | `str` | - |
| `Tiempo de Actividad Física` | `tiempo_actividad_fisica` | `float` | `0 <= x <= 500` |
| `Condición Comórbida` | `condicion_comorbida` | `str` | - |
| `Preferencia de Accesibilidad` | `preferencia_accesibilidad` | `str` | - |
| `Entorno de Ejercicio` | `entorno_ejercicio` | `str` | - |
| `Motivación` | `motivacion` | `str` | - |

> **Importante:** los campos categóricos aceptan cualquier string. Los **desconocidos** se sustituyen por el valor más frecuente del dataset (ver [`01-modelo-de-ia.md`](01-modelo-de-ia.md#5-artefactos)).

### 3.2 Ejemplo (español)

```json
{
  "Edad": 51,
  "Género": "Femenino",
  "IMC": 27.4,
  "Nivel de Visión": "Hipermetropía",
  "Condición Física": "Moderada",
  "Tiempo de Actividad Física": 30,
  "Condición Comórbida": "Diabetes Tipo 2",
  "Preferencia de Accesibilidad": "Guías auditivas",
  "Entorno de Ejercicio": "Gimnasio",
  "Motivación": "Moderada"
}
```

### 3.3 Ejemplo equivalente (snake_case)

```json
{
  "edad": 51,
  "genero": "Femenino",
  "imc": 27.4,
  "nivel_vision": "Hipermetropía",
  "condicion_fisica": "Moderada",
  "tiempo_actividad_fisica": 30,
  "condicion_comorbida": "Diabetes Tipo 2",
  "preferencia_accesibilidad": "Guías auditivas",
  "entorno_ejercicio": "Gimnasio",
  "motivacion": "Moderada"
}
```

---

## 4. Endpoints

### 4.1 `GET /api/health` - Estado del servicio

Verifica que el modelo y los preprocesadores están cargados.

**Respuesta `200 OK`:**

```json
{
  "model_loaded": true,
  "model_path": "<ruta-del-proyecto>/artifacts/modelo5.keras",
  "preprocessors_path": "<ruta-del-proyecto>/artifacts/preprocessors.pkl",
  "num_classes": {
    "Ejercicios Fase 1 de Calentamiento": 9,
    "Ejercicios Fase 2 de Entrenamiento": 9,
    "Ejercicios Fase 3 de Enfriamiento": 7
  }
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `model_loaded` | `boolean` | `true` si la red neuronal está en memoria |
| `model_path` | `string` | Ruta del archivo `.keras` |
| `preprocessors_path` | `string` | Ruta del archivo `preprocessors.pkl` |
| `num_classes` | `object` | Nº de clases por fase (útil para saber si el feedback expandió alguna) |

**Errores:** ninguno esperado. Si el servicio no arrancó con el modelo, `model_loaded` será `false` (aunque en la práctica el lifespan lanza el error de carga en el log).

---

### 4.2 `POST /api/plan` - Generar plan de ejercicio

Genera los 3 ejercicios personalizados a partir del perfil del usuario.

**Request body:** [`UserProfile`](#3-contrato-del-perfil-de-usuario-userprofile)

**Respuesta `200 OK`:**

```json
{
  "calentamiento": "Marcha en el lugar con cuerda guía",
  "entrenamiento": "(Fuerza y Resistencia) Flexiones en pared",
  "enfriamiento": "Estiramiento de espalda baja"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `calentamiento` | `string` | Ejercicio fase 1 (calentamiento) |
| `entrenamiento` | `string` | Ejercicio fase 2 (entrenamiento) |
| `enfriamiento` | `string` | Ejercicio fase 3 (enfriamiento) |

**Ejemplo con `curl`:**

```bash
curl -X POST http://127.0.0.1:8000/api/plan \
  -H "Content-Type: application/json" \
  -d '{
    "Edad": 51,
    "Género": "Femenino",
    "IMC": 27.4,
    "Nivel de Visión": "Hipermetropía",
    "Condición Física": "Moderada",
    "Tiempo de Actividad Física": 30,
    "Condición Comórbida": "Diabetes Tipo 2",
    "Preferencia de Accesibilidad": "Guías auditivas",
    "Entorno de Ejercicio": "Gimnasio",
    "Motivación": "Moderada"
  }'
```

**Errores:**

| Código | Caso | Ejemplo de `detail` |
|--------|------|---------------------|
| `422` | Campo faltante / tipo incorrecto / fuera de rango | `[{"type": "missing", "loc": ["body", "IMC"], "msg": "Field required"}]` |
| `503` | Modelo no cargado | `{"detail": "Modelo no disponible"}` |
| `422` | Error interno de predicción | `{"detail": "Error generando plan: <mensaje>"}` |

---

### 4.3 `GET /api/exercises` - Catálogo de ejercicios

Devuelve todos los ejercicios disponibles, agrupados por fase. Es el catálogo que el frontend usa para el flujo "Comenzar".

**Respuesta `200 OK`:**

```json
{
  "Calentamiento": [
    "Balanceo de brazos",
    "Balanceo de brazos cruzado",
    "Círculos con los tobillos (sentado o de pie)",
    "Elevación de rodillas alternadas",
    "Marcha en el lugar con cuerda guía",
    "Movimientos de brazos en forma de \u201calas\u201d",
    "Paso lateral con toque en piso",
    "Respiraciones profundas con movilidad de brazos",
    "Rotaciones articulares suaves"
  ],
  "Entrenamiento": [
    "(Equilibrio y Coordinación) Caminar en línea recta guiada voz/cuerda",
    "(Equilibrio y Coordinación) Postura de árbol adaptada",
    "(Fuerza y Resistencia) Elevaciones de talones con apoyo",
    "(Fuerza y Resistencia) Extensión de pierna sentado",
    "(Fuerza y Resistencia) Flexiones en pared",
    "(Fuerza y Resistencia) Press de hombros con botellas de agua",
    "(Fuerza y Resistencia) Remo con banda elástica/toalla",
    "(Fuerza y Resistencia) Sentadillas asistidas con silla/barra",
    "(Fuerza y resistencia) Puente de glúteos"
  ],
  "Enfriamiento": [
    "Estiramiento de brazos cruzados sobre el pecho",
    "Estiramiento de cuello guiíado",
    "Estiramiento de espalda baja",
    "Estiramientos estáticos (cuádriceps)",
    "Estiramientos estáticos (isquiotibiales)",
    "Movilidad suave (balanceo de brazos)",
    "Respiraciones profundas"
  ]
}
```

| Clave | Tipo | Descripción |
|-------|------|-------------|
| `Calentamiento` | `string[]` | 9 ejercicios de fase 1 |
| `Entrenamiento` | `string[]` | 9 ejercicios de fase 2 |
| `Enfriamiento` | `string[]` | 7 ejercicios de fase 3 |

> **Nota:** Las claves usan **mayúscula inicial** (`Calentamiento`), mientras que la respuesta de `/api/plan` usa **minúsculas** (`calentamiento`). Esto es intencional y debe respetarse al consumir la API.

**Errores:** `503` si el modelo no está cargado.

---

### 4.4 `POST /api/feedback` - Enviar feedback y reentrenar

Permite que el usuario corrija el plan. Si `suitable` es `false`, el sistema **reentrena el modelo** con la corrección y guarda los artefactos actualizados.

**Request body (`FeedbackRequest`):**

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `suitable` | `boolean` | `true` si el plan fue adecuado (no reentrena) / `false` si se corrige |
| `input_data` | `UserProfile` | Perfil del usuario (mismo contrato de `/api/plan`) |
| `corrected_exercises` | `object` | Ejercicios corregidos por fase |

**`corrected_exercises`:**

| Campo | Tipo |
|-------|------|
| `Calentamiento` | `string` (ejercicio) |
| `Entrenamiento` | `string` (ejercicio) |
| `Enfriamiento` | `string` (ejercicio) |

**Ejemplo:**

```json
{
  "suitable": false,
  "input_data": {
    "Edad": 51,
    "Género": "Femenino",
    "IMC": 27.4,
    "Nivel de Visión": "Hipermetropía",
    "Condición Física": "Moderada",
    "Tiempo de Actividad Física": 30,
    "Condición Comórbida": "Diabetes Tipo 2",
    "Preferencia de Accesibilidad": "Guías auditivas",
    "Entorno de Ejercicio": "Gimnasio",
    "Motivación": "Moderada"
  },
  "corrected_exercises": {
    "Calentamiento": "Rotaciones articulares suaves",
    "Entrenamiento": "Caminata en el lugar",
    "Enfriamiento": "Respiraciones profundas"
  }
}
```

**Respuesta `200 OK` (reentrenado):**

```json
{
  "status": "ok",
  "retrained": true,
  "message": "Modelo reentrenado y guardado"
}
```

**Respuesta `200 OK` (plan adecuado):**

```json
{
  "status": "ok",
  "retrained": false,
  "message": "Plan adecuado, no se requiere reentrenamiento"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `status` | `string` | Siempre `"ok"` |
| `retrained` | `boolean` | `true` si el modelo fue reentrenado y guardado |
| `message` | `string` | Mensaje legible |

**Comportamiento del reentrenamiento:**
1. El nuevo ejemplo se preprocesa con la misma pipeline (codificación + escalado).
2. Si un ejercicio corregido **no existe** en la fase, se **expande el encoder** (`num_classes` crece) y queda disponible en `/api/exercises`.
3. Se reentrena la red (10 épocas, batch 32) con el dataset completo + el nuevo ejemplo.
4. Se guardan `artifacts/modelo5.keras` y `artifacts/preprocessors.pkl`.

**Errores:**

| Código | Caso |
|--------|------|
| `422` | Contrato inválido (falta `input_data`, `suitable` no booleano, etc.) |
| `503` | Modelo no cargado |
| `422` | Error interno al reentrenar |

---

## 5. Endpoints de sesión (Fase 2 - gemelo digital)

Prefijo: `/api/session`. Permiten que el detector (o cualquier cliente) abra una sesión ligada a un plan, envíe observaciones de ejecución y reciba **correcciones** en español. Las sesiones se persisten en **SQLite** (`data/sessions.db`, se crea al arrancar).

### 5.1 `POST /api/session/start` - Crear sesión

**Request body:**

```json
{
  "plan": {
    "calentamiento": "Marcha en el lugar con cuerda guía",
    "entrenamiento": "Sentadillas asistidas con silla/barra",
    "enfriamiento": "Respiraciones profundas"
  }
}
```

**Respuesta `200 OK`:**

```json
{
  "session_id": "43da54c2b4734d63b13f63ffc745e888",
  "plan": { "calentamiento": "...", "entrenamiento": "...", "enfriamiento": "..." },
  "status": "active"
}
```

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `session_id` | `string` | Identificador único (hex 32) |
| `plan` | `object` | El plan recibido |
| `status` | `string` | `active` |

### 5.2 `GET /api/session/{session_id}` - Consultar sesión

**Respuesta `200 OK`:**

```json
{
  "session_id": "43da54c2b4734d63b13f63ffc745e888",
  "status": "active",
  "plan": { "..." },
  "current_exercise": "Sentadillas asistidas con silla/barra",
  "created_at": "2026-08-11T17:35:08.150700+00:00",
  "completed_at": null
}
```

**Error:** `404` -> `{"detail": "Sesión no encontrada"}`

### 5.3 `POST /api/session/{session_id}/observation` - Enviar observación y recibir corrección

El endpoint central del gemelo digital: **el backend evalúa** la observación contra la plantilla del ejercicio (`data/exercise_templates.json`) y devuelve la corrección.

**Request body (`ObservationRequest`):**

| Campo | Tipo | Validación | Descripción |
|-------|------|-----------|-------------|
| `exercise` | `string` | requerido | Nombre del ejercicio (del plan) |
| `frame_ts` | `float` | `>= 0` | Marca de tiempo del frame |
| `fase` | `string` | - | Fase de la máquina de estados (`DE_PIE`, `BAJANDO`, `SQUAT_PROFUNDO`, ...) |
| `desplazamiento_y` | `float` | - | Descenso del torso en metros |
| `postura_correcta` | `boolean` | - | Hombros nivelados (dentro de tolerancia) |
| `hombros_visibles` | `boolean` | - | Si los tags de los hombros están visibles |
| `repeticiones` | `int` | `>= 0` | Repeticiones válidas contadas |
| `rep_valid` | `boolean` | - | Indica que el último ciclo acaba de contar una repetición |
| `rep_rejected` | `boolean` | - | Indica que el último ciclo terminó sin contar por postura |

```json
{
  "exercise": "Sentadillas asistidas con silla/barra",
  "frame_ts": 12.345,
  "fase": "BAJANDO",
  "desplazamiento_y": 0.25,
  "postura_correcta": true,
  "hombros_visibles": true,
  "repeticiones": 3
}
```

**Respuesta `200 OK` (`CorrectionResponse`):**

| Campo | Tipo | Valores |
|-------|------|---------|
| `level` | `string` | `ok`; `warning`; `error` |
| `message_es` | `string` | Corrección en español (para TTS) |
| `siguiente_paso` | `string` | `CONTINUAR`; `REPETIR`; `AVANZAR` |
| `evento_voz` | `string \| null` | `repeticion_contada`; `repeticion_rechazada`; `profundidad_alcanzada`; `ejercicio_completado` |
| `mensaje_voz` | `string \| null` | Mensaje prioritario para anunciar por voz una sola vez |
| `id_evento_voz` | `string \| null` | Identificador único para no repetir ni perder el evento durante el polling |

Ejemplos:

```json
{ "level": "ok", "message_es": "Excelente, repetición válida (3/10)", "siguiente_paso": "CONTINUAR" }
{ "level": "warning", "message_es": "Baja un poco más para completar la sentadilla", "siguiente_paso": "CONTINUAR" }
{ "level": "warning", "message_es": "Sube con la espalda recta, mantén los hombros nivelados", "siguiente_paso": "REPETIR" }
{ "level": "warning", "message_es": "La repetición no contó porque la postura no era correcta.", "siguiente_paso": "REPETIR", "evento_voz": "repeticion_rechazada", "mensaje_voz": "La repetición no contó. Mantén los hombros nivelados y vuelve a intentarlo." }
{ "level": "error", "message_es": "Colócate frente a la cámara para que pueda ver tus hombros", "siguiente_paso": "CONTINUAR" }
{ "level": "ok", "message_es": "¡Sentadillas completadas! Meta: 10 repeticiones", "siguiente_paso": "AVANZAR" }
```

Si el ejercicio **no tiene plantilla**: `{ "level": "ok", "message_es": "Ejercicio sin plantilla de evaluación aún", "siguiente_paso": "CONTINUAR" }`.

Cada observación queda registrada en el historial y actualiza `current_exercise`.

**Errores:** `404` sesión inexistente; `422` contrato inválido.

### 5.4 `GET /api/session/{session_id}/observations` - Historial

Devuelve todas las observaciones con su corrección (útil para el reporte de fin de sesión).

**Respuesta `200 OK`:** array de registros con `id`, `exercise`, `fase`, `desplazamiento_y`, `postura_correcta`, `hombros_visibles`, `repeticiones`, `level`, `message_es`, `siguiente_paso`, `created_at`.

### 5.5 `POST /api/session/{session_id}/complete` - Cerrar sesión

Marca la sesión como `completed` (y rellena `completed_at`).

**Respuesta `200 OK`:** `SessionResponse` con `status: "completed"`.

> **Estados posibles de `status`:** `active` (creada, en curso), `completed` (terminada de forma natural) y `abandoned` (terminada a medias: el usuario pulsa Terminar o el hilo de la cámara falla). Cuando el gemelo digital abandona una sesión, `completed_at` se rellena con la marca de fin.

### 5.6 Ejemplo de flujo completo (curl)

```bash
BASE=http://127.0.0.1:8000

# 1. Crear sesión
SID=$(curl -s -X POST $BASE/api/session/start -H "Content-Type: application/json" \
  -d '{"plan":{"calentamiento":"Marcha en el lugar con cuerda guía","entrenamiento":"Sentadillas asistidas con silla/barra","enfriamiento":"Respiraciones profundas"}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")

# 2. Enviar observaciones y ver correcciones
curl -s -X POST $BASE/api/session/$SID/observation -H "Content-Type: application/json" \
  -d '{"exercise":"Sentadillas asistidas con silla/barra","fase":"SQUAT_PROFUNDO","desplazamiento_y":0.38,"postura_correcta":false,"hombros_visibles":true}'

# 3. Cerrar sesión
curl -s -X POST $BASE/api/session/$SID/complete
```

---

## 6. Endpoints de cámara (flujo web, Fase 2)

El backend también ejecuta el **detector de tags en un hilo propio** y lo expone
al frontend web. El navegador solo muestra el video (MJPEG) y envía comandos.

### 6.1 `GET /api/camera/state` - Estado en tiempo real

Devuelve el estado del controlador de cámara (para polling cada ~200 ms):

```json
{
  "status": "running",
  "session_id": "...",
  "plan": { "calentamiento": "...", "entrenamiento": "...", "enfriamiento": "..." },
  "phase": "entrenamiento",
  "exercise": "(Fuerza y Resistencia) Sentadillas asistidas con silla/barra",
  "fase": "SQUAT_PROFUNDO",
  "repeticiones": 3,
  "objetivo": 10,
  "profundidad_objetivo_m": 0.35,
  "desplazamiento_y": 0.38,
  "postura_ok": false,
  "hombros_visibles": true,
  "calibrado": true,
  "tracking_available": true,
  "calibration_requested": false,
  "detected_tags": [0, 1],
  "correction": { "level": "warning", "message_es": "...", "siguiente_paso": "REPETIR" },
  "error": null,
  "completed_naturally": false
}
```

`status`: `idle`; `running`; `waiting_next`; `completed`; `stopped`; `error`.

Campos de diagnóstico:

- `tracking_available`: el ejercicio actual tiene plantilla de seguimiento automático.
- `calibration_requested`: el usuario pulsó calibrar y el detector espera pose válida.
- `detected_tags`: IDs AprilTag reconocidos en el frame, aunque la pose 3D falle.
- `hombros_visibles`: existen poses 3D válidas simultáneas para los IDs `0` y `1`.
- `fase`: `MANUAL`, `ESPERANDO`, `DE_PIE`, `BAJANDO` o `SQUAT_PROFUNDO`.
- `profundidad_objetivo_m`: descenso objetivo del ejercicio actual (de su plantilla). Permite al frontend dibujar el medidor de profundidad sin valores fijos.

### 6.2 `GET /api/camera/stream` - Video MJPEG

Streaming `multipart/x-mixed-replace` con el frame anotado (tags dibujados,
fase y repeticiones). Se consume con un `<img src="/api/camera/stream">`.
Mientras no hay sesión muestra un placeholder ("Cámara apagada").

### 6.3 `POST /api/camera/start` - Iniciar sesión con cámara

Crea la sesión (`POST /api/session/start`) y arranca el loop de detección.

**Cuerpo:** `SessionStartRequest` (`{"plan": {calentamiento, entrenamiento, enfriamiento}}`)
**Query opcional:** `?source=0` (webcam) o `?source=/ruta/video.mp4` (pruebas).

**Respuesta `200 OK`:** estado inicial del `CameraController`, con `status=running`, `session_id`, plan y campos de diagnóstico. La cámara ya está abierta cuando responde. **Errores:** `503` si la fuente de video no está disponible o si ya existe una sesión activa.

### 6.4 `POST /api/camera/calibrate` - Calibrar postura inicial

Requiere `status=running`, `tracking_available=true` y una calibración aún pendiente. Marca `calibration_requested=true` y busca las AprilTag `tag36h11` ID `0` y `1`. Cuando ambas tienen pose 3D, guarda la altura inicial, cambia a `calibrado=true` y entra en `DE_PIE`. **Errores `409`:** ejercicio manual, sesión inactiva o postura ya calibrada.

### 6.5 `POST /api/camera/next` - Pasar al siguiente ejercicio

Requiere `status=waiting_next`, tanto para una meta automática cumplida como para confirmar el final de un ejercicio manual. El estado cambia inmediatamente a `running` para impedir que un doble clic adelante dos fases. **Errores:** `409` fuera de esa espera.

### 6.6 `POST /api/camera/stop` - Terminar

Detiene el loop y libera la cámara.; **Errores:** `409` sin sesión activa.

---

## 7. Ejemplos de flujo completo

### 7.1 Generar plan y verificarlo contra el catálogo

```bash
# 1) Generar plan
PLAN=$(curl -s -X POST http://127.0.0.1:8000/api/plan -H "Content-Type: application/json" -d '{"Edad":80,"Género":"Femenino","IMC":38,"Nivel de Visión":"Ceguera Total","Condición Física":"Baja","Tiempo de Actividad Física":15,"Condición Comórbida":"Obesidad Severa","Preferencia de Accesibilidad":"Supervisión humana","Entorno de Ejercicio":"Hogar","Motivación":"Baja"}')
echo "$PLAN"
# 2) Ver ejercicios válidos
curl -s http://127.0.0.1:8000/api/exercises
```

### 7.2 Reentrenar con un ejercicio nuevo

```bash
curl -s -X POST http://127.0.0.1:8000/api/feedback -H "Content-Type: application/json" -d '{
  "suitable": false,
  "input_data": {"Edad": 40, "Género": "Masculino", "IMC": 25, "Nivel de Visión": "Miopía", "Condición Física": "Alta", "Tiempo de Actividad Física": 60, "Condición Comórbida": "Ninguna", "Preferencia de Accesibilidad": "Guías táctiles", "Entorno de Ejercicio": "Exterior", "Motivación": "Alta"},
  "corrected_exercises": {"Calentamiento": "Balanceo de brazos", "Entrenamiento": "Caminata en el lugar", "Enfriamiento": "Respiraciones profundas"}
}'
```

---

## 8. CORS

Orígenes permitidos (configurables en `app/core/config.py`):

| Origen |
|--------|
| `http://localhost:3000` |
| `http://127.0.0.1:3000` |
| `http://localhost:5173` |
| `http://127.0.0.1:5173` |

Se permiten todos los métodos y cabeceras (`allow_methods=["*"]`, `allow_headers=["*"]`), con `allow_credentials=True`.

---

## 9. Contratos Pydantic (código fuente)

Todos los contratos están definidos en `app/schemas/plan.py` y `app/schemas/session.py`:

| Clase | Archivo | Uso |
|-------|---------|-----|
| `UserProfile` | `schemas/plan.py` | Cuerpo de `/api/plan` y `input_data` de `/api/feedback` |
| `PlanResponse` | `schemas/plan.py` | Respuesta de `/api/plan` |
| `CorrectedExercises` | `schemas/plan.py` | `corrected_exercises` de `/api/feedback` |
| `FeedbackRequest` | `schemas/plan.py` | Cuerpo de `/api/feedback` |
| `FeedbackResponse` | `schemas/plan.py` | Respuesta de `/api/feedback` |
| `Plan` | `schemas/session.py` | Plan dentro de las sesiones |
| `SessionStartRequest` | `schemas/session.py` | Cuerpo de `/api/session/start` |
| `SessionStartResponse` | `schemas/session.py` | Respuesta de `/api/session/start` |
| `SessionResponse` | `schemas/session.py` | Respuesta de consulta/completar sesión |
| `ObservationRequest` | `schemas/session.py` | Cuerpo de `observation` |
| `CorrectionResponse` | `schemas/session.py` | Respuesta de corrección |
