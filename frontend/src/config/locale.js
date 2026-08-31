// src/config/locale.js
// The UI copy below is English-only. The frontend has no language toggle.
export const LANG = 'en'

// Prefer the English value, falling back to the base string when unavailable
// (kept for compatibility with parts.js label/label_en and desc/desc_en).
export function pick(zh, en) {
  return en ?? zh
}

// List separator
export function join(arr) {
  return arr.join(', ')
}

// ── Copy table ──
const EN = {
  // App.jsx
  speakingBadge: 'Explaining: ',
  voiceNarration: 'Voice narration',
  voiceInput: 'Voice input',
  voiceHint: '💡 Hold Space to talk when the input is not focused',
  unlabeledParts: '🔍 Unlabeled parts (click to highlight, {n} total)',
  partsList: 'Parts (multi-select, {n} total)',
  unlabeledTitle: '⚠️ This model’s parts are not labeled yet',
  unlabeledBody: 'Click a 🔍 name to highlight it on the model. Once confirmed, paste the config below into config/parts.js.',
  placeholderName: 'Enter part name here',
  copyConfig: '📋 Copy config to clipboard',
  resetSelection: 'Reset selection',
  selectedCount: '📍 {n} part(s) selected',
  hintClick: '🖱️ Click the model or list to select parts',
  resetView: '🔄 Reset view',
  modelLabel: 'Model: ',
  glbNode: 'GLB node: ',

  // ChatPanel.jsx
  greeting: 'Hi! I’m your aircraft knowledge assistant 🛩️\n\nClick parts on the aircraft model (multi-select), then ask me anything!',
  errorGeneric: 'Sorry, something went wrong. Please try again later 😥',
  chatTitle: 'Aircraft Q&A',
  selectedPartsHeader: '{n} selected: {names}',
  clickToStart: 'Click parts on the model to start',
  readAloud: 'Read this message aloud',
  reading: '🔊 Reading...',
  read: '🔈 Read',
  sttProcessing: 'Recognizing...',
  listening: '🎤 Listening...',
  releaseToEnd: 'Release Space to stop',
  selectedLabel: 'Selected: ',
  clear: 'Clear',
  placeholderType: 'Type, or hold Space while not focused to talk...',
  placeholderAsk: 'Ask about {parts}...',
  placeholderSelectFirst: 'Click parts on the aircraft first (multi-select)...',
  send: 'Send',
  thinking: 'Thinking...',

  // DigitalHuman.jsx
  dhSpeaking: 'Speaking...',
  dhListening: 'Listening...',
  dhIdle: 'Flight Instructor',
}

export function t(key, vars = {}) {
  const s = EN[key] ?? key
  return s.replace(/\{(\w+)\}/g, (_, k) => (vars[k] ?? ''))
}
