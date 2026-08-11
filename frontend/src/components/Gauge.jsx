const R = 84
const C = 2 * Math.PI * R

export default function Gauge({ state, speaking }) {
  const reps = state?.repeticiones ?? 0
  const objetivo = state?.objetivo ?? 10
  const depth = state?.desplazamiento_y ?? 0
  const posturaOk = state?.postura_ok ?? true
  const visibles = state?.hombros_visibles ?? false
  const fase = state?.fase ?? ''

  const completion = objetivo > 0 ? Math.min(reps / objetivo, 1) : 0
  const descent = Math.max(0, Math.min(depth / 0.35, 1))
  const color = !visibles ? '#5A6B7D' : posturaOk ? '#1E7A46' : '#C63D3D'

  const dashed = `${descent * C} ${C}`
  const completed = `${completion * C} ${C}`
  const movementLabel = fase === 'SQUAT_PROFUNDO'
    ? 'VUELVE DE PIE'
    : fase === 'BAJANDO'
      ? 'SIGUE BAJANDO'
      : 'REPETICIONES'

  return (
    <div className={`gauge ${speaking ? 'gauge--speaking' : ''}`} aria-hidden="true">
      <svg viewBox="0 0 200 200" className="gauge-svg">
        <circle className="gauge-track" cx="100" cy="100" r={R} />
        <circle
          className="gauge-depth"
          cx="100"
          cy="100"
          r={R}
          strokeDasharray={dashed}
          transform="rotate(-90 100 100)"
        />
        <circle
          className="gauge-complete"
          cx="100"
          cy="100"
          r={R - 12}
          strokeDasharray={completed}
          stroke={color}
          transform="rotate(-90 100 100)"
        />
      </svg>
      <div className="gauge-center">
        <span className="gauge-number" style={{ color }}>
          {reps}
        </span>
        <span className="gauge-total">/ {objetivo}</span>
        <span className="gauge-label">{movementLabel}</span>
      </div>
      <div className="gauge-ripple" />
    </div>
  )
}
