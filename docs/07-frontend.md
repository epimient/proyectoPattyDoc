# Frontend (React + Vite)

La interfaz web del producto. Se ejecuta **separada** de la API: el backend
(FastAPI) solo expone endpoints `/api/*` (incluida la cámara) y el frontend se
sirve con Vite, que **proxy** `/api` hacia el backend en desarrollo.

## Estructura

```
frontend/
├── index.html           # Punto de entrada (carga las fuentes)
├── package.json
├── vite.config.js       # puerto 5173 + proxy /api -> 127.0.0.1:8000
└── src/
    ├── main.jsx         # bootstrap de React
    ├── App.jsx          # pantallas: perfil -> plan -> sesión
    ├── api.js           # cliente fetch hacia /api
    ├── voice.js         # Web Speech API (speechSynthesis en español)
    ├── styles.css       # tokens de diseño ("consola audible")
    └── components/
        ├── ProfileForm.jsx      # ficha del usuario -> POST /api/plan
        ├── PlanSummary.jsx      # plan + sesión normal + prueba de sentadillas
        ├── SessionView.jsx      # orquesta cámara, estado, voz y botones
        ├── CameraView.jsx       # <img src="/api/camera/stream">
        ├── Gauge.jsx            # firma: aro de repeticiones que "oye" la voz
        ├── StatusPanel.jsx      # fase, etiquetas detectadas, calibración y corrección
        └── ControlButtons.jsx   # Calibrar postura (C); Siguiente (N); Terminar (Q)
```

## Flujo implementado

1. El perfil genera un plan personalizado de tres fases.
2. **Empezar sesión** ejecuta ese plan sin alterarlo.
3. **Probar sentadillas con cámara** crea un plan temporal que sustituye solo el entrenamiento por `Sentadillas asistidas con silla/barra`.
4. La API abre la cámara antes de confirmar el inicio; si falla, el frontend muestra el error y no reutiliza el estado de una sesión anterior.
5. Los ejercicios sin plantilla usan estado `MANUAL`, no requieren calibración y esperan **Siguiente**; nunca avanzan por temporizador.
6. La sentadilla habilita **Calibrar postura**. Durante la búsqueda se muestran los IDs AprilTag detectados.
7. La repetición se cuenta al completar **de pie -> bajada profunda -> vuelta de pie**, con las etiquetas `0` y `1` visibles.
8. El visor conserva el cuadro completo en relación 4:3 (`object-fit: contain`), sin recortar la cámara.

### Estados relevantes

| Estado | Interfaz | Acción disponible |
|--------|----------|-------------------|
| `waiting_next` + ejercicio manual | Espera explícita | Siguiente o Terminar |
| `running` + seguimiento | Etiquetas y calibración | Calibrar postura |
| `SQUAT_PROFUNDO` | “VUELVE DE PIE” | Mantener tags visibles y subir |
| `waiting_next` + meta alcanzada | Ejercicio completado | Siguiente o Terminar |
| `completed` | Sesión completada | Volver al plan |

## Ejecutar

```bash
# 1. (solo la primera vez) instalar dependencias
cd frontend && npm install

# 2. Levantar API + front juntos
scripts/dev.sh
# API  -> http://127.0.0.1:8000  (y su Swagger en /docs)
# Front -> http://127.0.0.1:5173

# O en dos terminales por separado:
./venv/bin/python -m uvicorn app.main:app --port 8000   # terminal 1
cd frontend && npm run dev -- --port 5173                # terminal 2
```

El proxy de Vite redirige `/api/*` a `http://127.0.0.1:8000`, así que el front funciona sin configurar CORS. Para usar otra API durante desarrollo:

```bash
VITE_API_TARGET=http://127.0.0.1:8001 npm run dev -- --port 5174
```

## Diseño: "consola audible"

- **Paleta:** fondo hielo `#F5F7FA`, tinta `#0D1B2A`, señal ámbar `#FFB000`,
  ok `#1E7A46`, alerta `#C63D3D`.
- **Tipografía:** Archivo (display), IBM Plex Sans (cuerpo), JetBrains Mono (datos).
- **Firma:** el **gauge** de repeticiones pulsa como una onda sonora cada vez que
  el asistente habla (clase `gauge--speaking` + `prefers-reduced-motion`).
- Accesibilidad: botones >= 64 px, foco visible, `aria-live` en el panel de estado,
  atajos de teclado C/N/Q, y toda la información también por voz.

## Voz (Web Speech API)

El servidor no sintetiza audio en el flujo web: envía el texto de la corrección
en `/api/camera/state` y el navegador lo habla con `speechSynthesis` en español
(`src/voice.js`). Si no hay voz en español disponible, el texto sigue visible
en pantalla.

## Producción

```bash
cd frontend && npm run build        # genera frontend/dist/
```

Sírvelo con cualquier servidor estático y proxifica `/api` hacia la API, o usa
`npm run preview` para un vistazo local.
