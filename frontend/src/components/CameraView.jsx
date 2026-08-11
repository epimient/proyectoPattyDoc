import { STREAM_URL } from '../api.js'

export default function CameraView() {
  return (
    <figure className="camera">
      <img className="camera-feed" src={STREAM_URL} alt="Transmisión de la cámara con los marcadores de tus hombros" />
    </figure>
  )
}
