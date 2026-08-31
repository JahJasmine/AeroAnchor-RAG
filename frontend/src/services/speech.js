/**
 * Speech recognition service — based on the browser Web Speech API.
 */

const SR = window.SpeechRecognition || window.webkitSpeechRecognition

/** Check whether speech recognition is available */
export const isSupported = () => !!SR

/**
 * Start speech recognition (push-to-talk mode)
 * @param {object} opts
 * @param {function} opts.onInterim - real-time recognition result callback (interimText)
 * @param {function} opts.onFinal   - final recognition result callback (finalText)
 * @param {function} opts.onError   - error callback (errorCode)
 * @returns {function} cleanup function that stops recording
 */
export function startListening({ onInterim, onFinal, onError } = {}) {
  if (!SR) { onError?.('not-supported'); return () => {} }

  let accumulated  = ''
  let explicitStop = false
  let restarts     = 0
  let currentRec   = null
  const MAX_RESTARTS = 3

  function start() {
    const rec = new SR()
    rec.lang           = 'en-US'
    rec.continuous     = true
    rec.interimResults = true
    currentRec = rec

    rec.onresult = (e) => {
      let interim = ''
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i]
        if (r.isFinal) {
          accumulated += r[0].transcript
        } else {
          interim += r[0].transcript
        }
      }
      onInterim?.(accumulated + interim)
    }

    rec.onerror = (e) => {
      // no-speech is not a real error, ignore it
      if (e.error !== 'no-speech') {
        onError?.(e.error)
      }
    }

    rec.onend = () => {
      if (explicitStop) {
        const text = accumulated.trim()
        if (text) onFinal?.(text)
        return
      }

      const text = accumulated.trim()
      if (text) {
        // result already captured — deliver it
        onFinal?.(text)
      } else if (restarts < MAX_RESTARTS) {
        // no result yet — silently restart to keep the mic active
        restarts++
        try { start() } catch { onError?.('ended') }
      } else {
        onError?.('ended')
      }
    }

    try { rec.start() } catch { onError?.('ended') }
  }

  start()

  return () => {
    explicitStop = true
    try { currentRec?.stop() } catch { /* already stopped */ }
  }
}
