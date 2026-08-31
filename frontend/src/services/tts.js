/**
 * TTS voice synthesis service — prefer the backend TTS endpoint, fall back to the browser's built-in speechSynthesis on failure.
 */

const API = import.meta.env.VITE_API_URL ?? ''

let currentAudio = null
let speakGen = 0

/** Stop the voice currently playing */
export function stopSpeaking() {
  speakGen++
  if (currentAudio) { currentAudio.pause(); currentAudio = null }
  window.speechSynthesis?.cancel()
}

/**
 * Read text aloud
 * @param {string} text - the text to read
 * @param {object} opts
 * @param {function} opts.onStart    - playback start callback
 * @param {function} opts.onEnd      - playback end callback
 * @param {function} opts.onDuration - gets the audio duration (seconds), used to sync the typewriter effect
 */
export async function speak(text, { onStart, onEnd, onDuration } = {}) {
  const gen = ++speakGen
  if (currentAudio) { currentAudio.pause(); currentAudio = null }
  window.speechSynthesis?.cancel()

  const stale = () => gen !== speakGen

  // ── Try the backend TTS endpoint ──
  let blob = null
  try {
    const res = await fetch(`${API}/api/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text }),
    })
    if (stale()) return
    if (res.ok) {
      blob = await res.blob()
    }
  } catch {
    // network error — fall back to browser TTS
  }

  if (blob && !stale()) {
    const played = await new Promise((resolve) => {
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      currentAudio = audio

      audio.onloadedmetadata = () => {
        if (audio.duration && isFinite(audio.duration)) {
          onDuration?.(audio.duration)
        }
      }
      audio.onplay = () => onStart?.()
      audio.onended = () => {
        URL.revokeObjectURL(url)
        if (currentAudio === audio) currentAudio = null
        onEnd?.()
        resolve(true)
      }

      const handleFail = () => {
        URL.revokeObjectURL(url)
        if (currentAudio === audio) currentAudio = null
        resolve(false) // fallback signal
      }

      audio.onerror = handleFail
      audio.play().catch(handleFail)
    })

    if (played) return
  }

  // ── Fallback: the browser's built-in speech synthesis ──
  if (stale()) { onEnd?.(); return }
  return browserSpeak(text, onStart, onEnd)
}

function browserSpeak(text, onStart, onEnd) {
  if (!window.speechSynthesis) {
    onStart?.(); onEnd?.()
    return Promise.resolve()
  }

  return new Promise((resolve) => {
    const utter = new SpeechSynthesisUtterance(text)
    const voices = window.speechSynthesis.getVoices()

    // prefer an English voice
    const preferred = voices.find(v => v.lang.startsWith('en'))
    if (preferred) utter.voice = preferred

    utter.lang  = 'en-US'
    utter.rate  = 0.95
    utter.pitch = 1.05
    utter.onstart = () => onStart?.()
    utter.onend   = () => { onEnd?.(); resolve() }
    utter.onerror = () => { onEnd?.(); resolve() }
    window.speechSynthesis.speak(utter)
  })
}
