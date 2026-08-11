let cachedVoice = null

function pickSpanishVoice() {
  if (cachedVoice) return cachedVoice
  const voices = window.speechSynthesis?.getVoices?.() || []
  cachedVoice = voices.find((v) => v.lang?.toLowerCase().startsWith('es')) || null
  return cachedVoice
}

/**
 * Habla un texto con la voz del navegador en español.
 * Devuelve true si se pudo emitir.
 */
export function speak(text, { rate = 1, onStart, onEnd } = {}) {
  if (!('speechSynthesis' in window) || !text) return false
  window.speechSynthesis.cancel()
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'es-ES'
  utterance.rate = rate
  const voice = pickSpanishVoice()
  if (voice) utterance.voice = voice
  if (onStart) utterance.onstart = onStart
  if (onEnd) utterance.onend = onEnd
  window.speechSynthesis.speak(utterance)
  return true
}

export function cancelSpeech() {
  if ('speechSynthesis' in window) window.speechSynthesis.cancel()
}
