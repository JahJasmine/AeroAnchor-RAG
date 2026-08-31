import { useState, useEffect, useCallback } from 'react'
import './App.css'
import AirplaneViewer from './components/AirplaneViewer'
import ChatPanel from './components/ChatPanel'
import DigitalHuman from './components/DigitalHuman/DigitalHuman'
import ToggleSwitch from './components/ToggleSwitch/ToggleSwitch'
import { MODELS, DEFAULT_MODEL_INDEX } from './config/parts'
import { t, join } from './config/locale'

export default function App() {
  const [modelIndex, setModelIndex] = useState(DEFAULT_MODEL_INDEX)
  const [selectedParts, setSelectedParts] = useState([])
  const [hoveredPart, setHoveredPart] = useState(null)
  const [discoveredParts, setDiscoveredParts] = useState([])
  const [highlightedParts, setHighlightedParts] = useState([]) // parts highlighted by the AI

  // ── Voice feature state ──
  const [voiceNarrationOn, setVoiceNarrationOn] = useState(false)
  const [voiceInputOn, setVoiceInputOn] = useState(false)
  const [digitalHumanState, setDigitalHumanState] = useState('idle') // 'idle' | 'speaking' | 'listening'

  const currentModel = MODELS[modelIndex]

  // Clear selection when switching models
  useEffect(() => {
    setSelectedParts([])
    setDiscoveredParts([])
    setHighlightedParts([])
  }, [modelIndex])

  // Debug: track whether the AI highlighted-parts state is being set
  useEffect(() => {
    console.log('[App] highlightedParts =', JSON.stringify(highlightedParts))
  }, [highlightedParts])

  const matchedParts = discoveredParts.filter(d => d.matched)
  const unmatchedParts = discoveredParts.filter(d => !d.matched)
  // If there are no configured parts, the model hasn't been calibrated yet; show all nodes for identification
  const showAllParts = matchedParts.length === 0
  const displayParts = showAllParts ? unmatchedParts : matchedParts

  const togglePart = (name) => {
    setSelectedParts(prev =>
      prev.includes(name) ? prev.filter(p => p !== name) : [...prev, name]
    )
  }

  return (
    <div className="ae-root">
      <div className="ae-viewer">
        {/* ── Top control bar: model selector + voice switches ── */}
        <div className="ae-top-bar">
          <div className="ae-model-selector">
            <div className="ae-model-row">
              <span className="ae-model-label">{t('modelLabel')}</span>
              <select
                value={modelIndex}
                onChange={e => setModelIndex(Number(e.target.value))}
                className="ae-model-select"
              >
                {MODELS.map((m, i) => (
                  <option key={i} value={i}>{m.name}</option>
                ))}
              </select>
            </div>
            {highlightedParts.length > 0 && (
              <div className="ae-speaking-badge">
                🔴 {t('speakingBadge')}{join(highlightedParts)}
              </div>
            )}
          </div>

          <div className="ae-voice-controls">
            <ToggleSwitch
              checked={voiceNarrationOn}
              onChange={setVoiceNarrationOn}
              label={t('voiceNarration')}
            />
            <ToggleSwitch
              checked={voiceInputOn}
              onChange={setVoiceInputOn}
              label={t('voiceInput')}
            />
          </div>

          {voiceInputOn && (
            <div className="ae-voice-hint">
              {t('voiceHint')}
            </div>
          )}
        </div>

        <AirplaneViewer
          key={modelIndex}
          modelPath={currentModel.file}
          partMap={currentModel.partMap}
          patterns={currentModel.patterns}
          hide={currentModel.hide}
          modelScale={currentModel.scale}
          selectedParts={selectedParts}
          highlightedParts={highlightedParts}
          hoveredPart={hoveredPart}
          onPartHover={setHoveredPart}
          onPartClick={togglePart}
          onPartsDiscovered={setDiscoveredParts}
        />

        {displayParts.length > 0 && (
          <div className="ae-parts-list" style={{ top: 40 }}>
            <div style={{ fontSize: 10, color: '#666', marginBottom: 4, paddingLeft: 4 }}>
              {showAllParts
                ? t('unlabeledParts', { n: displayParts.length })
                : t('partsList', { n: displayParts.length })}
            </div>
            {displayParts.map(p => (
              <button
                key={p.name}
                className={`ae-part-chip${selectedParts.includes(p.name) ? ' selected' : ''}`}
                onClick={() => togglePart(p.name)}
                title={p.desc || `${t('glbNode')}${p.name}`}
                style={p.matched ? {} : { borderColor: '#f59e0b', color: '#f59e0b' }}
              >
                {p.matched ? p.label : `🔍 ${p.name}`}
              </button>
            ))}
          </div>
        )}

        {showAllParts && unmatchedParts.length > 0 && (
          <div style={{
            position: 'absolute', top: 40, right: 16, zIndex: 10,
            background: 'rgba(15,17,23,0.95)', backdropFilter: 'blur(12px)',
            border: '1px solid #f59e0b', borderRadius: 12,
            padding: '14px 16px', maxWidth: 320, maxHeight: '50vh',
            overflow: 'auto', fontSize: 12,
          }}>
            <div style={{ color: '#f59e0b', fontWeight: 600, marginBottom: 8 }}>
              {t('unlabeledTitle')}
            </div>
            <div style={{ color: '#aaa', marginBottom: 10, lineHeight: 1.6 }}>
              {t('unlabeledBody')}
            </div>
            <div style={{
              background: '#0f1117', border: '1px solid #333', borderRadius: 8,
              padding: '10px 12px', marginBottom: 8,
              fontFamily: 'monospace', fontSize: 11, color: '#60a5fa',
              whiteSpace: 'pre-wrap', wordBreak: 'break-all',
              maxHeight: 180, overflow: 'auto',
            }}>
              {`  // ${currentModel.name}\n${unmatchedParts.map(d => `  '${d.name}': { label: '${t('placeholderName')}', desc: '' },`).join('\n')}`}
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(
                `  // ${currentModel.name}\n${unmatchedParts.map(d => `  '${d.name}': { label: '${t('placeholderName')}', desc: '' },`).join('\n')}`
              )}
              style={{
                padding: '6px 14px', borderRadius: 6,
                border: '1px solid #f59e0b', background: 'transparent',
                color: '#f59e0b', cursor: 'pointer', fontSize: 12,
                fontFamily: 'inherit', width: '100%',
              }}
            >
              {t('copyConfig')}
            </button>
          </div>
        )}

        <div className="ae-toolbar">
          <button onClick={() => setSelectedParts([])}>{t('resetSelection')}</button>
          <span className="divider" />
          <span style={{ padding: '8px 12px', color: selectedParts.length > 0 ? '#60a5fa' : '#666', fontSize: 13 }}>
            {selectedParts.length > 0 ? t('selectedCount', { n: selectedParts.length }) : t('hintClick')}
          </span>
        </div>
      </div>

      <div className="ae-chat">
        <ChatPanel
          selectedParts={selectedParts}
          availableParts={matchedParts}
          modelName={currentModel.name}
          onClearSelection={() => setSelectedParts([])}
          onPartsHighlighted={setHighlightedParts}
          voiceNarrationOn={voiceNarrationOn}
          voiceInputOn={voiceInputOn}
          onDigitalHumanState={setDigitalHumanState}
        />
      </div>

      {/* ── Digital human ── */}
      <DigitalHuman state={digitalHumanState} />
    </div>
  )
}
