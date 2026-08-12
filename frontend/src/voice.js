let cachedVoice = null
let pendingSpeakTimer = null

function pickSpanishVoice() {
  if (cachedVoice) return cachedVoice
  const voices = window.speechSynthesis?.getVoices?.() || []
  cachedVoice = voices.find((v) => v.lang?.toLowerCase().startsWith('es')) || null
  return cachedVoice
}

function refreshVoice() {
  cachedVoice = null
  pickSpanishVoice()
}

// En Chrome las voces se cargan de forma asíncrona; hay que re-intentar
// cuando el navegador notifica que ya están disponibles.
if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
  const synth = window.speechSynthesis
  synth.addEventListener?.('voiceschanged', refreshVoice)
  if (synth.getVoices?.().length) refreshVoice()
}

/**
 * Habla un texto con la voz del navegador en español.
 * Devuelve true si se pudo emitir.
 */
export function speak(text, { rate = 1, onStart, onEnd } = {}) {
  if (!('speechSynthesis' in window) || !text) return false

  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'es-ES'
  utterance.rate = rate
  const voice = pickSpanishVoice()
  if (voice) utterance.voice = voice
  if (onStart) utterance.onstart = onStart
  if (onEnd) utterance.onend = onEnd

  // `cancel()` seguido de `speak()` en el mismo tick puede tragarse la frase
  // en algunos navegadores; un pequeño retardo lo evita.
  window.speechSynthesis.cancel()
  if (pendingSpeakTimer !== null) clearTimeout(pendingSpeakTimer)
  pendingSpeakTimer = setTimeout(() => {
    pendingSpeakTimer = null
    window.speechSynthesis.speak(utterance)
  }, 50)
  return true
}

export function cancelSpeech() {
  if (pendingSpeakTimer !== null) {
    clearTimeout(pendingSpeakTimer)
    pendingSpeakTimer = null
  }
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}
