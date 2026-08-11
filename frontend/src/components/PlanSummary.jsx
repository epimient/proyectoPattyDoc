import { useEffect, useRef } from 'react'
import { speak } from '../voice.js'

const TRACKED_SQUAT = 'Sentadillas asistidas con silla/barra'

const PHASES = [
  { key: 'calentamiento', label: 'Calentamiento', order: '1º' },
  { key: 'entrenamiento', label: 'Entrenamiento', order: '2º' },
  { key: 'enfriamiento', label: 'Enfriamiento', order: '3º' },
]

export default function PlanSummary({ plan, onBack, onStart }) {
  const announced = useRef(false)

  useEffect(() => {
    if (!plan || announced.current) return
    announced.current = true
    const texto = `Este es tu plan. Primero, ${plan.calentamiento}. Después, ${plan.entrenamiento}. Y para terminar, ${plan.enfriamiento}.`
    speak(texto)
  }, [plan])

  return (
    <main className="shell shell--narrow">
      <section className="hero hero--compact">
        <p className="hero-kicker">Tu plan está listo</p>
        <h1 className="hero-title">Tres fases, en orden</h1>
      </section>

      <ol className="plan-list">
        {PHASES.map((phase, i) => (
          <li className="plan-item" key={phase.key}>
            <span className="plan-order" aria-hidden="true">
              {phase.order}
            </span>
            <div className="plan-body">
              <p className="plan-label">{phase.label}</p>
              <p className="plan-exercise">{plan[phase.key]}</p>
            </div>
          </li>
        ))}
      </ol>

      <button className="btn btn--primary btn--block" onClick={() => onStart(plan)} autoFocus>
        Empezar sesión
      </button>
      <button
        className="btn btn--ok btn--block"
        onClick={() => onStart({ ...plan, entrenamiento: TRACKED_SQUAT })}
      >
        Probar sentadillas con cámara
      </button>
      <button className="btn btn--ghost btn--block" onClick={onBack}>
        Volver y cambiar mis datos
      </button>
    </main>
  )
}
