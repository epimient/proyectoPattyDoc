import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api.js'
import { cancelSpeech, speak } from '../voice.js'
import CameraView from './CameraView.jsx'
import ControlButtons from './ControlButtons.jsx'
import Gauge from './Gauge.jsx'
import StatusPanel from './StatusPanel.jsx'

const POLL_MS = 200

// Misma lógica de habilitación que ControlButtons.jsx.
function canDo(state) {
  const status = state?.status ?? 'idle'
  const trackingAvailable = state?.tracking_available === true
  return {
    calibrate: status === 'running' && trackingAvailable && !state?.calibrado && state?.calibration_requested !== true,
    next: status === 'waiting_next',
    stop: status === 'running' || status === 'waiting_next',
  }
}

export default function SessionView({ plan, onExit }) {
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(true)
  const [sessionStarted, setSessionStarted] = useState(false)
  const [speaking, setSpeaking] = useState(false)

  const lastMessage = useRef('')
  const lastPhase = useRef('')
  const lastStatus = useRef('')

  const say = useCallback(
    (text) => {
      if (!text) return
      speak(text, {
        onStart: () => setSpeaking(true),
        onEnd: () => setSpeaking(false),
      })
    },
    [],
  )

  const announce = useCallback(
    (s) => {
      if (!s) return
      const { status, phase, correction } = s
      const message = correction?.message_es || ''

      if (status === 'waiting_next' && lastStatus.current !== 'waiting_next') {
        say(
          s.tracking_available
            ? 'Ejercicio completado. Pulsa Siguiente para continuar o Terminar para salir.'
            : 'Realiza este ejercicio a tu ritmo. Cuando termines, pulsa Siguiente.',
        )
      } else if (status === 'completed' && lastStatus.current !== 'completed') {
        say('Sesión completada. Excelente trabajo.')
      }
      lastStatus.current = status

      if (phase && phase !== lastPhase.current) {
        say(`Fase ${phase}.`)
      }
      lastPhase.current = phase

      if (message && message !== lastMessage.current) {
        say(message)
      }
      lastMessage.current = message
    },
    [say],
  )

  useEffect(() => {
    if (!sessionStarted) return undefined
    let cancelled = false

    const poll = async () => {
      try {
        const s = await api.getState()
        if (cancelled) return
        setState(s)
        if (s.status === 'error' && s.error) setError(s.error)
        announce(s)
      } catch (e) {
        if (!cancelled) setError(String(e.message || e))
      }
    }

    poll()
    const id = setInterval(poll, POLL_MS)
    return () => {
      cancelled = true
      clearInterval(id)
      cancelSpeech()
    }
  }, [announce, sessionStarted])

  useEffect(() => {
    let cancelled = false
    let started = false
    setState(null)
    setError(null)
    setStarting(true)
    setSessionStarted(false)
    api
      .startCamera(plan)
      .then((initialState) => {
        started = true
        if (cancelled) {
          api.stop().catch(() => {})
          return
        }
        setState(initialState)
        setSessionStarted(true)
        setStarting(false)
        say('Empieza la sesión. Sigue las indicaciones del ejercicio actual.')
      })
      .catch((e) => {
        if (cancelled) return
        setStarting(false)
        setError(String(e.message || e))
        say('No se pudo iniciar la cámara. Revisa que esté conectada e inténtalo de nuevo.')
      })
    return () => {
      cancelled = true
      if (started) api.stop().catch(() => {})
    }
  }, [plan, say])

  const onCalibrate = useCallback(() => {
    api.calibrate().then(setState).catch((e) => {
      if (e.status !== 409) setError(String(e.message || e))
    })
  }, [])

  const onNext = useCallback(() => {
    api.next().then(setState).catch((e) => {
      if (e.status !== 409) setError(String(e.message || e))
    })
  }, [])

  const onStop = useCallback(async () => {
    try {
      await api.stop()
    } catch {
      /* ya estaba detenido */
    }
    cancelSpeech()
    onExit()
  }, [onExit])

  useEffect(() => {
    const onKey = (e) => {
      const k = e.key.toLowerCase()
      const allowed = canDo(state)
      if (k === 'c' && allowed.calibrate) onCalibrate()
      else if (k === 'n' && allowed.next) onNext()
      else if (k === 'q' && allowed.stop) onStop()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCalibrate, onNext, onStop, state])

  const status = state?.status
  const completed = sessionStarted && status === 'completed'

  return (
    <main className="session">
      <div className="session-stage">
        <CameraView />
        {starting && <p className="session-banner">Activando cámara…</p>}
        {completed && (
          <div className="session-completed">
            <p className="session-completed-title">Sesión completada</p>
            <button className="btn btn--primary" onClick={onExit} autoFocus>
              Volver a mi plan
            </button>
          </div>
        )}
      </div>

      <aside className="session-console">
        <Gauge state={state} speaking={speaking} />
        <StatusPanel state={state} />
        <ControlButtons
          state={state}
          onCalibrate={onCalibrate}
          onNext={onNext}
          onStop={onStop}
          busy={starting}
        />
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
      </aside>
    </main>
  )
}
