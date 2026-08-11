#!/usr/bin/env bash
# Levanta la API (FastAPI, :8000) y el frontend (Vite, :5173) juntos.
# Uso: scripts/dev.sh   (Ctrl+C detiene ambos)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PORT_API="${PORT_API:-8000}"
PORT_FRONT="${PORT_FRONT:-5173}"
PYTHON="${PYTHON:-./venv/bin/python}"

cleanup() {
  echo ""
  echo "Deteniendo procesos..."
  if [[ -n "${PID_API:-}" ]]; then
    kill "$PID_API" 2>/dev/null || true
    wait "$PID_API" 2>/dev/null || true
  fi
}
trap cleanup EXIT INT TERM

echo "1/2 · Arrancando API en http://127.0.0.1:${PORT_API}"
"$PYTHON" -m uvicorn app.main:app --port "$PORT_API" &
PID_API=$!

for _ in $(seq 1 60); do
  if curl -sf -m 1 "http://127.0.0.1:${PORT_API}/api/health" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "2/2 · Arrancando frontend en http://127.0.0.1:${PORT_FRONT}"
cd frontend
npm run dev -- --port "$PORT_FRONT" --strictPort
