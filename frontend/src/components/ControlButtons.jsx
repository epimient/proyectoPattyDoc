export default function ControlButtons({ state, onCalibrate, onNext, onStop, busy }) {
  const status = state?.status ?? 'idle'
  const trackingAvailable = state?.tracking_available === true
  const calibrationRequested = state?.calibration_requested === true
  const canCalibrate = status === 'running' && trackingAvailable && !state?.calibrado && !calibrationRequested
  const canNext = status === 'waiting_next'
  const canStop = status === 'running' || status === 'waiting_next'

  return (
    <div className="controls">
      <button
        className="btn btn--primary"
        onClick={onCalibrate}
        disabled={!canCalibrate || busy}
        title={trackingAvailable ? 'Usa las etiquetas de ambos hombros como referencia inicial' : 'Este ejercicio no tiene seguimiento automático'}
      >
        {calibrationRequested
          ? 'Buscando etiquetas…'
          : trackingAvailable
            ? 'Calibrar postura'
            : 'No requiere calibración'}
        <span className="btn-key">C</span>
      </button>
      <button className="btn btn--ok" onClick={onNext} disabled={!canNext || busy}>
        Siguiente
        <span className="btn-key">N</span>
      </button>
      <button className="btn btn--danger" onClick={onStop} disabled={!canStop || busy}>
        Terminar
        <span className="btn-key">Q</span>
      </button>
    </div>
  )
}
