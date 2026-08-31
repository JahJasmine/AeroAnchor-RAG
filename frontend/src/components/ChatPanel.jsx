import { useState, useRef, useEffect, useCallback } from 'react'
import { sendSegmentedMessage } from '../services/api'
import { speak, stopSpeaking } from '../services/tts'
import { startListening, isSupported as isSTTSupported } from '../services/speech'
import { t, join } from '../config/locale'

// Fixed highlight duration per segment in non-narration mode (seconds)
const SILENT_SEG_SEC = 2

export default function ChatPanel({
  selectedParts, availableParts, modelName, onClearSelection, onPartsHighlighted,
  voiceNarrationOn, voiceInputOn, onDigitalHumanState,
}) {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: t('greeting'),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [speakingIdx, setSpeakingIdx] = useState(null) // index of the message currently being read aloud
  const [recording, setRecording] = useState(false)
  const [interimText, setInterimText] = useState('')
  const [sttStatus, setSttStatus] = useState('') // '' | 'listening' | 'processing'
  const bottomRef = useRef(null)
  const inputRef = useRef(null)
  const stopSTTRef = useRef(null)
  const recordingRef = useRef(false) // use a ref to avoid stale-closure issues
  const presentGenRef = useRef(0)      // highlight timeline generation (increment on new message/stop to cancel the old one)
  const silentTimersRef = useRef([])   // timers for non-narration mode
  const segmentsByMsgRef = useRef({})  // segments for each assistant message
  const sendingRef = useRef(false)     // prevent duplicate sends (double-click / repeated Enter sets it true synchronously and immediately blocks the second one)

  // ── Auto-scroll to bottom ──
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // ── Read text aloud (with typewriter effect) ──
  const typeTimer = useRef(null)

  const startTyping = useCallback((fullText, msgIdx, durationSec) => {
    // clear the message text and type it out character by character
    const chars = [...fullText]  // use the spread operator to correctly handle multi-byte characters
    const delay = (durationSec * 1000) / chars.length
    let i = 0
    clearInterval(typeTimer.current)
    typeTimer.current = setInterval(() => {
      i++
      setMessages(prev => {
        const next = [...prev]
        if (next[msgIdx]) {
          next[msgIdx] = { ...next[msgIdx], content: chars.slice(0, i).join('') }
        }
        return next
      })
      if (i >= chars.length) clearInterval(typeTimer.current)
    }, delay)
  }, [])

  const stopTyping = useCallback((fullText, msgIdx) => {
    clearInterval(typeTimer.current)
    setMessages(prev => {
      const next = [...prev]
      if (next[msgIdx]) {
        next[msgIdx] = { ...next[msgIdx], content: fullText }
      }
      return next
    })
  }, [])

  const speakText = useCallback(async (text, msgIdx) => {
    stopSpeaking()
    setSpeakingIdx(msgIdx)
    // clear the text first, then type it out once the audio is ready
    setMessages(prev => {
      const next = [...prev]
      if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], content: '' }
      return next
    })
    let typed = false
    await speak(text, {
      onDuration: (dur) => {
        typed = true
        startTyping(text, msgIdx, dur)
      },
      onStart: () => onDigitalHumanState?.('speaking'),
      onEnd: () => {
        if (typed) {
          stopTyping(text, msgIdx)  // typewriter finished normally, fill in the full text
        } else {
          // TTS didn't provide a duration (browser fallback, etc.), show the full text directly as a fallback
          setMessages(prev => {
            const next = [...prev]
            if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], content: text }
            return next
          })
        }
        setSpeakingIdx(null)
        onDigitalHumanState?.('idle')
      },
    })
  }, [onDigitalHumanState])

  // ── Timeline highlighting: highlight segments in order (narration mode follows the voice, non-narration follows reading time) ──
  const playVoiceSegments = useCallback((segments, msgIdx) => {
    const myGen = ++presentGenRef.current
    silentTimersRef.current.forEach(clearTimeout)
    silentTimersRef.current = []
    setSpeakingIdx(msgIdx)
    onDigitalHumanState?.('speaking')

    const play = (i) => {
      if (presentGenRef.current !== myGen) return  // already cancelled by a new message/stop
      if (i >= segments.length) {
        setSpeakingIdx(null)
        onDigitalHumanState?.('idle')
        onPartsHighlighted([])
        return
      }
      const seg = segments[i]
      // speaking segment i: show text up to segment i and highlight that segment's parts
      const cumulative = segments.slice(0, i + 1).map(s => s.text).join('\n')
      setMessages(prev => {
        const next = [...prev]
        if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], content: cumulative }
        return next
      })
      onPartsHighlighted(seg.parts || [])
      speak(seg.text, {
        onStart: () => onDigitalHumanState?.('speaking'),
        onEnd: () => play(i + 1),
      })
    }
    play(0)
  }, [onDigitalHumanState, onPartsHighlighted])

  const playSilentSegments = useCallback((segments) => {
    const myGen = ++presentGenRef.current
    silentTimersRef.current.forEach(clearTimeout)
    silentTimersRef.current = []

    // In non-narration mode also make the digital human move its mouth, following the highlight timeline (simulating a "silent narration")
    onDigitalHumanState?.('speaking')

    let elapsed = 0
    segments.forEach((seg) => {
      const dur = SILENT_SEG_SEC
      silentTimersRef.current.push(setTimeout(() => {
        if (presentGenRef.current === myGen) onPartsHighlighted(seg.parts || [])
      }, elapsed * 1000))
      elapsed += dur
    })
    // finally clear the highlight + return the digital human to idle
    silentTimersRef.current.push(setTimeout(() => {
      if (presentGenRef.current === myGen) {
        onPartsHighlighted([])
        onDigitalHumanState?.('idle')
      }
    }, elapsed * 1000))
  }, [onPartsHighlighted, onDigitalHumanState])

  // ── Voice input: hold the spacebar to talk ──
  useEffect(() => {
    if (!voiceInputOn || !isSTTSupported()) return

    const handleKeyDown = (e) => {
      // don't trigger recording when focus is in the input (allow normal typing)
      if (document.activeElement === inputRef.current) return
      // prevent duplicate triggers (holding the key fires repeat events)
      if (e.repeat) return
      // already recording, ignore
      if (recordingRef.current) return

      if (e.code === 'Space') {
        e.preventDefault()
        stopSpeaking()
        recordingRef.current = true
        setRecording(true)
        setInterimText('')
        setSttStatus('listening')
        onDigitalHumanState?.('listening')

        stopSTTRef.current = startListening({
          onInterim: (t) => setInterimText(t),
          onFinal: (t) => {
            // recognition finished, fill into the input
            setInput(prev => prev ? prev + t : t)
            recordingRef.current = false
            setRecording(false)
            setInterimText('')
            setSttStatus('')
            onDigitalHumanState?.('idle')
          },
          onError: () => {
            recordingRef.current = false
            setRecording(false)
            setInterimText('')
            setSttStatus('')
            onDigitalHumanState?.('idle')
          },
        })
      }
    }

    const handleKeyUp = (e) => {
      if (e.code === 'Space' && recordingRef.current && stopSTTRef.current) {
        // manually stop recording so onend triggers onFinal
        stopSTTRef.current()
        stopSTTRef.current = null
        // show "processing" and wait for the onFinal callback
        setSttStatus('processing')
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('keyup', handleKeyUp)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('keyup', handleKeyUp)
      stopSTTRef.current?.()
    }
    // Note: only use voiceInputOn as a dependency to avoid repeated binding
  }, [voiceInputOn, onDigitalHumanState])

  // ── Send message ──
  const handleSend = async () => {
    if (sendingRef.current) return  // a request is already in flight, ignore (prevent double-click / repeated Enter from sending twice)
    const text = (input || interimText).trim()
    if (!text || loading) return

    sendingRef.current = true
    const userMsg = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setInterimText('')
    setLoading(true)
    stopSpeaking()
    onClearSelection?.()               // clear the white selection/highlight after sending a question to avoid clashing with blue
    onDigitalHumanState?.('idle')

    try {
      const history = [...messages, userMsg]
        .filter(m => m.role !== 'system')
        .map(m => ({ role: m.role, content: m.content }))

      const { segments = [] } = await sendSegmentedMessage(
        history,
        selectedParts,
        availableParts.map(p => typeof p === 'string' ? p : p.name),
        modelName
      )
      const fullText = segments.map(s => s.text).join('\n')
      const msgIdx = messages.length + 1  // index of the assistant message added this time
      segmentsByMsgRef.current[msgIdx] = segments
      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      if (!fullText) {
        setMessages(prev => {
          const next = [...prev]
          if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], content: t('errorGeneric') }
          return next
        })
      } else if (voiceNarrationOn) {
        // narration mode: play voice segment by segment, highlighting whichever segment is being spoken
        playVoiceSegments(segments, msgIdx)
      } else {
        // non-narration mode: show the text in one go, advance the highlight segment by segment by reading time
        setMessages(prev => {
          const next = [...prev]
          if (next[msgIdx]) next[msgIdx] = { ...next[msgIdx], content: fullText }
          return next
        })
        playSilentSegments(segments)
      }
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: t('errorGeneric'),
      }])
      console.error(err)
    } finally {
      sendingRef.current = false
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={{
      width: '100%', height: '100%', display: 'flex', flexDirection: 'column',
      background: '#1a1d27', borderLeft: '1px solid #2a2d37',
    }}>
      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid #2a2d37',
        display: 'flex', alignItems: 'center', gap: 10,
      }}>
        <span style={{ fontSize: 20 }}>🛩️</span>
        <div>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#e4e4e7' }}>{t('chatTitle')}</div>
          <div style={{ fontSize: 12, color: selectedParts.length > 0 ? '#60a5fa' : '#666', marginTop: 2 }}>
            {selectedParts.length > 0
              ? t('selectedPartsHeader', { n: selectedParts.length, names: join(selectedParts) })
              : t('clickToStart')}
          </div>
        </div>
      </div>

      {/* Message list */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '16px 20px',
        display: 'flex', flexDirection: 'column', gap: 12,
      }}>
        {messages.map((msg, i) => (
          <div key={i} style={{
            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
            maxWidth: '85%',
          }}>
            <div style={{
              padding: '10px 16px', borderRadius: 16,
              fontSize: 14, lineHeight: 1.6,
              background: msg.role === 'user' ? '#2563eb' : '#262a35',
              color: msg.role === 'user' ? '#fff' : '#d1d5db',
              borderBottomRightRadius: msg.role === 'user' ? 4 : 16,
              borderBottomLeftRadius: msg.role === 'assistant' ? 4 : 16,
            }}>
              {msg.content}
              {speakingIdx === i && <span className="ae-type-cursor" />}
            </div>

            {/* Read-aloud button — only shown on assistant messages */}
            {msg.role === 'assistant' && msg.content && (
              <button
                onClick={() => {
                  const segs = segmentsByMsgRef.current[i]
                  if (segs && segs.length) playVoiceSegments(segs, i)
                  else speakText(msg.content, i)
                }}
                disabled={speakingIdx === i}
                style={{
                  marginTop: 4,
                  padding: '3px 10px',
                  borderRadius: 10,
                  border: '1px solid #3a3d47',
                  background: speakingIdx === i ? '#1e3a5f' : 'transparent',
                  color: speakingIdx === i ? '#60a5fa' : '#666',
                  fontSize: 11,
                  cursor: speakingIdx === i ? 'default' : 'pointer',
                  fontFamily: 'inherit',
                  transition: 'all 0.2s',
                }}
                title={t('readAloud')}
              >
                {speakingIdx === i ? t('reading') : t('read')}
              </button>
            )}
          </div>
        ))}

        {loading && (
          <div style={{ alignSelf: 'flex-start', padding: '10px 16px' }}>
            <span style={{ color: '#666', fontSize: 14 }}>{t('thinking')}</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Voice input status bar */}
      {sttStatus && (
        <div style={{
          margin: '0 16px', padding: '8px 14px',
          borderRadius: 10,
          background: sttStatus === 'processing'
            ? 'rgba(96,165,250,0.1)'
            : 'rgba(245,158,11,0.12)',
          border: sttStatus === 'processing'
            ? '1px solid rgba(96,165,250,0.3)'
            : '1px solid rgba(245,158,11,0.3)',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          {sttStatus === 'processing' ? (
            <>
              <div className="ae-proc-spinner" />
              <span style={{ fontSize: 13, color: '#60a5fa', flex: 1 }}>
                {t('sttProcessing')}
              </span>
            </>
          ) : (
            <>
              <div className="ae-rec-dot" />
              <span style={{ fontSize: 13, color: '#f59e0b', flex: 1 }}>
                {interimText || t('listening')}
              </span>
              <span style={{ fontSize: 11, color: '#888' }}>{t('releaseToEnd')}</span>
            </>
          )}
        </div>
      )}

      {/* Selected parts bar */}
      {selectedParts.length > 0 && (
        <div style={{
          padding: '8px 16px', display: 'flex', flexWrap: 'wrap', gap: 6,
          alignItems: 'center', borderTop: '1px solid #2a2d37',
        }}>
          <span style={{ fontSize: 11, color: '#888', marginRight: 4 }}>{t('selectedLabel')}</span>
          {selectedParts.map(p => (
            <span key={p} style={{
              padding: '3px 10px', borderRadius: 12,
              background: '#1e3a5f', color: '#60a5fa',
              fontSize: 12, display: 'flex', alignItems: 'center', gap: 4,
            }}>
              {p}
            </span>
          ))}
          <button
            onClick={() => onClearSelection?.()}
            style={{
              marginLeft: 'auto', background: 'none', border: 'none',
              color: '#f87171', cursor: 'pointer', fontSize: 11,
              fontFamily: 'inherit',
            }}
          >
            {t('clear')}
          </button>
        </div>
      )}

      {/* Input box */}
      <div style={{
        padding: '12px 16px', borderTop: '1px solid #2a2d37',
        display: 'flex', gap: 8,
      }}>
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            sttStatus === 'processing' ? t('sttProcessing') :
            recording ? (interimText || t('listening')) :
            voiceInputOn ? t('placeholderType') :
            selectedParts.length > 0
              ? t('placeholderAsk', { parts: join(selectedParts.slice(0, 3)) })
              : t('placeholderSelectFirst')
          }
          disabled={loading}
          style={{
            flex: 1, padding: '10px 14px',
            borderRadius: 10, border: recording ? '1px solid #f59e0b' : '1px solid #3a3d47',
            background: '#0f1117', color: '#e4e4e7',
            fontSize: 14, outline: 'none',
            fontFamily: 'inherit',
            transition: 'border-color 0.2s',
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || (!input.trim() && !recording)}
          style={{
            padding: '10px 18px', borderRadius: 10,
            border: 'none', background: loading ? '#1e3a5f' : '#2563eb',
            color: '#fff', fontSize: 14, fontWeight: 500,
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading || (!input.trim() && !recording) ? 0.5 : 1,
            fontFamily: 'inherit',
          }}
        >
          {loading ? '...' : t('send')}
        </button>
      </div>
    </div>
  )
}
