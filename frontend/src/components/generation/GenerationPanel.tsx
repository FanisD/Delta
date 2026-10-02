import { useState } from "react"

type Settings = {
  card_count: number
  tone: string
  language: string
  audience: string
  density: "concise" | "balanced" | "detailed"
}
type Item = { id: string; title: string; summary: string }
type Card = { id: string; title: string; layout: string; blocks: unknown[] }
type Outline = { title: string; items: Item[] }

const defaults: Settings = {
  card_count: 6,
  tone: "clear",
  language: "English",
  audience: "general",
  density: "balanced",
}

export function GenerationPanel({ onDone }: { onDone: () => void }) {
  const [prompt, setPrompt] = useState("")
  const [settings, setSettings] = useState(defaults)
  const [outline, setOutline] = useState<Outline | null>(null)
  const [cards, setCards] = useState<Card[]>([])
  const [status, setStatus] = useState("")
  const [jobId, setJobId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const requestOutline = async () => {
    setBusy(true)
    const response = await fetch("/api/generation/outline", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, settings }),
    })
    if (response.ok) setOutline(await response.json())
    setBusy(false)
  }

  const generate = async () => {
    if (!outline) return
    setBusy(true)
    setCards([])
    const response = await fetch("/api/generation/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, settings, outline }),
    })
    if (!response.ok) {
      setStatus("Unable to start generation")
      setBusy(false)
      return
    }
    const job = await response.json()
    setJobId(job.id)
    const events = new EventSource(`/api/generation/jobs/${job.id}/events`)
    events.addEventListener("card", (event) => {
      setCards((current) => [...current, JSON.parse((event as MessageEvent).data)])
    })
    events.addEventListener("error", () => setStatus("Some cards could not be generated"))
    events.addEventListener("done", () => {
      events.close()
      setStatus("Presentation ready")
      setBusy(false)
      onDone()
    })
  }

  const regenerate = async (cardId: string) => {
    if (!jobId) return
    const response = await fetch(`/api/generation/jobs/${jobId}/cards/${cardId}/regenerate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    })
    if (response.ok) {
      const result = await response.json()
      const replacement = result.cards.find((card: Card) => card.id === cardId)
      if (replacement) setCards((current) => current.map((card) => card.id === cardId ? replacement : card))
      setStatus("Card regenerated")
    }
  }

  const updateItem = (index: number, patch: Partial<Item>) =>
    setOutline((current) =>
      current
        ? { ...current, items: current.items.map((item, i) => (i === index ? { ...item, ...patch } : item)) }
        : current,
    )
  const moveItem = (index: number, offset: number) =>
    setOutline((current) => {
      if (!current) return current
      const items = [...current.items]
      const target = index + offset
      ;[items[index], items[target]] = [items[target], items[index]]
      return { ...current, items }
    })

  return (
    <section className="generation-panel" aria-label="Create presentation">
      <span className="eyebrow">CREATE WITH AI</span>
      <h1>Start with an idea.</h1>
      <textarea
        aria-label="Presentation topic"
        placeholder="Describe the story you want to tell…"
        value={prompt}
        onChange={(event) => setPrompt(event.target.value)}
      />
      <div className="generation-settings">
        <label>Cards <input type="number" min={1} max={30} value={settings.card_count} onChange={(e) => setSettings({ ...settings, card_count: Number(e.target.value) })} /></label>
        <label>Tone <input value={settings.tone} onChange={(e) => setSettings({ ...settings, tone: e.target.value })} /></label>
        <label>Audience <input value={settings.audience} onChange={(e) => setSettings({ ...settings, audience: e.target.value })} /></label>
        <label>Density <select value={settings.density} onChange={(e) => setSettings({ ...settings, density: e.target.value as Settings["density"] })}><option>concise</option><option>balanced</option><option>detailed</option></select></label>
      </div>
      {!outline && <button className="primary-button" disabled={!prompt.trim() || busy} onClick={() => void requestOutline()}>Build outline</button>}
      {outline && (
        <>
          <input aria-label="Presentation title" value={outline.title} onChange={(e) => setOutline({ ...outline, title: e.target.value })} />
          <div className="outline-list">
            {outline.items.map((item, index) => (
              <div className="outline-item" key={item.id}>
                <input aria-label={`Card ${index + 1} title`} value={item.title} onChange={(e) => updateItem(index, { title: e.target.value })} />
                <textarea value={item.summary} onChange={(e) => updateItem(index, { summary: e.target.value })} />
                <button className="text-button" onClick={() => setOutline({ ...outline, items: outline.items.filter((_, i) => i !== index) })}>Delete</button>
                <button className="text-button" disabled={index === 0} onClick={() => moveItem(index, -1)}>↑</button>
                <button className="text-button" disabled={index === outline.items.length - 1} onClick={() => moveItem(index, 1)}>↓</button>
              </div>
            ))}
          </div>
          <button className="text-button" onClick={() => setOutline({ ...outline, items: [...outline.items, { id: crypto.randomUUID(), title: "New card", summary: "Add a summary." }] })}>+ Add card</button>
          <div><button className="primary-button" disabled={busy || outline.items.length === 0} onClick={() => void generate()}>Generate cards</button> <button className="quiet-button" onClick={() => setOutline(null)}>Start over</button></div>
        </>
      )}
      {cards.length > 0 && (
        <div className="notice">
          {cards.length} card{cards.length === 1 ? "" : "s"} generated… {status}
          <div>{cards.map((card) => <button className="text-button" key={card.id} onClick={() => void regenerate(card.id)}>Regenerate “{card.title}”</button>)}</div>
        </div>
      )}
      {status && cards.length === 0 && <p className="notice">{status}</p>}
    </section>
  )
}
