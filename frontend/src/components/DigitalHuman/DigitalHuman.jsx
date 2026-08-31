import { useState, useEffect, useRef } from 'react'
import './DigitalHuman.css'
import { t } from '../../config/locale'

/**
 * Digital human — uses PNG textures
 * when speaking, quickly switch between speaking.png (mouth open) and idle.png (mouth closed) to simulate lip movement
 */
export default function DigitalHuman({ state = 'idle', onClick }) {
  const [animClass, setAnimClass] = useState('dh-idle')
  const [mouthOpen, setMouthOpen] = useState(false)
  const mouthTimer = useRef(null)

  useEffect(() => {
    switch (state) {
      case 'speaking':
        setAnimClass('dh-speaking')
        break
      case 'listening':
        setAnimClass('dh-listening')
        break
      default:
        setAnimClass('dh-idle')
        break
    }
  }, [state])

  // when speaking, quickly switch between the talking/closed-mouth images to simulate lip movement
  useEffect(() => {
    if (state !== 'speaking') {
      clearInterval(mouthTimer.current)
      setMouthOpen(false)
      return
    }
    mouthTimer.current = setInterval(() => {
      setMouthOpen(prev => !prev)
    }, 280) // every 280ms, simulating speech pace
    return () => clearInterval(mouthTimer.current)
  }, [state])

  // image selection logic: in the speaking state alternate between the mouth-open and mouth-closed images; other states map directly
  const imgSrc =
    state === 'speaking' ? (mouthOpen ? '/speaking.png' : '/idle.png') :
    state === 'listening' ? '/listening.png' :
    '/idle.png'

  return (
    <div
      className={`digital-human ${animClass}`}
      onClick={onClick}
      title={state === 'speaking' ? t('dhSpeaking') : state === 'listening' ? t('dhListening') : t('dhIdle')}
      role="button"
      tabIndex={0}
    >
      <div className="dh-body">
        <img
          src={imgSrc}
          alt={t('dhIdle')}
          className="dh-img"
          draggable={false}
        />
      </div>

      <div className="dh-indicator">
        <div className={`dh-dot${state === 'listening' ? ' dh-dot--listen' : ''}`} />
        <span className="dh-status-text">
          {state === 'speaking' ? t('dhSpeaking') : state === 'listening' ? t('dhListening') : t('dhIdle')}
        </span>
      </div>
    </div>
  )
}
