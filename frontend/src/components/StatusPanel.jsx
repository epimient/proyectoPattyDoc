const FASE_LABELS = {
  ESPERANDO: 'Esperando',
  MANUAL: 'Guiado manual',
  DE_PIE: 'De pie',
  BAJANDO: 'Bajando',
  SQUAT_PROFUNDO: 'En la posición',
}

const LEVEL_LABEL = {
  ok: 'En orden',
  warning: 'Ajusta',
  error: 'Atención',
  info: 'Nota',
}

export default function StatusPanel({ state }) {
  if (!state) return null
  const {
    phase,
    exercise,
    fase,
    hombros_visibles,
    calibrado,
    tracking_available,
    calibration_requested,
    detected_tags = [],
    correction,
    status,
  } = state
  const level = correction?.level ?? 'info'
  const message = correction?.message_es ?? ''

  return (
    <div className="status" aria-live="polite">
      <div className="status-phase">
        <p className="status-eyebrow">{phase ? `FASE ${phase.toUpperCase()}` : 'FASE'}</p>
        <p className="status-exercise">{exercise || '—'}</p>
      </div>

      <dl className="status-grid">
        <div className="status-cell">
          <dt>Estado</dt>
          <dd>{FASE_LABELS[fase] || fase || '—'}</dd>
        </div>
        <div className="status-cell">
          <dt>Etiquetas</dt>
          <dd className={tracking_available ? (hombros_visibles ? 'ok-text' : 'alert-text') : ''}>
            {tracking_available
              ? (detected_tags.length ? detected_tags.join(', ') : 'Ninguna')
              : 'No requeridas'}
          </dd>
        </div>
        <div className="status-cell">
          <dt>Calibración</dt>
          <dd className={calibrado ? 'ok-text' : ''}>
            {tracking_available
              ? (calibrado ? 'Lista' : calibration_requested ? 'Buscando' : 'Pendiente')
              : 'No requerida'}
          </dd>
        </div>
      </dl>

      <p className={`status-message status-message--${level}`}>
        <span className="status-level">{LEVEL_LABEL[level]}</span>
        {message}
      </p>

      {status === 'waiting_next' && (
        <p className="status-note">
          {tracking_available
            ? 'Completado. Pulsa Siguiente para continuar o Terminar para salir.'
            : 'Cuando termines este ejercicio, pulsa Siguiente.'}
        </p>
      )}
    </div>
  )
}
