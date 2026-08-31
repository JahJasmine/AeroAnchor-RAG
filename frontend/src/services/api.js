const API = import.meta.env.VITE_API_URL ?? ''

export async function sendSegmentedMessage(messages, selectedParts = [], availableParts = [], modelName = '') {
  const res = await fetch(`${API}/api/chat-parts`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      messages,
      selected_parts: selectedParts.map(p => typeof p === 'string' ? p : p.name),
      available_parts: availableParts.map(p => typeof p === 'string' ? p : p.name),
      model_name: modelName,
    }),
  })
  if (!res.ok) throw new Error(`Chat error ${res.status}`)
  return await res.json()  // { segments: [{ text, parts }] }
}

export async function fetchParts() {
  const res = await fetch(`${API}/api/parts`)
  if (!res.ok) return []
  const { parts } = await res.json()
  return parts
}
