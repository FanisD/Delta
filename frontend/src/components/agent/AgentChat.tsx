import { useState } from "react"
import type { DeckDocument } from "../../api"

type Props = {
  deck: DeckDocument
  onAccept: (deck: DeckDocument) => void
}

export function AgentChat({ deck, onAccept }: Props) {
  const [message, setMessage] = useState("")
  const [preview, setPreview] = useState<{
    deck: DeckDocument
    operations: unknown[]
    requires_confirmation: boolean
    warnings: string[]
  } | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  const previewChanges = async () => {
    if (!message.trim()) return
    setBusy(true)
    setError("")
    try {
      const response = await fetch("/api/agent/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ deck, message }),
      })
      const data = await response.json()
      if (!response.ok)
        throw new Error(
          data.detail ?? "The assistant could not edit this deck.",
        )
      setPreview(data)
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Assistant unavailable.",
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <aside className="agent-panel" aria-label="AI presentation assistant">
      <h3>Ask Delta</h3>
      <p className="muted">Describe an edit and review it before applying.</p>
      <textarea
        value={message}
        onChange={(event) => setMessage(event.target.value)}
        placeholder="Move the introduction to the end…"
        aria-label="Assistant request"
      />
      <button
        className="primary-button"
        onClick={() => void previewChanges()}
        disabled={busy}
      >
        {busy ? "Preparing preview…" : "Preview changes"}
      </button>
      {error && <p className="error-message">{error}</p>}
      {preview && (
        <div className="agent-preview">
          <strong>
            {preview.warnings.length ? "Confirmation needed" : "Preview ready"}
          </strong>
          {preview.warnings.map((warning) => (
            <p key={warning}>{warning}</p>
          ))}
          <div className="agent-actions">
            <button
              className="primary-button"
              onClick={() => {
                onAccept(preview.deck)
                setPreview(null)
                setMessage("")
              }}
              disabled={preview.requires_confirmation}
            >
              Accept
            </button>
            {preview.requires_confirmation && (
              <button
                className="quiet-button"
                onClick={async () => {
                  const response = await fetch("/api/agent/preview", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                      deck,
                      message,
                      operations: preview.operations,
                      confirm_deletions: true,
                    }),
                  })
                  if (response.ok) setPreview(await response.json())
                }}
              >
                Confirm deletion
              </button>
            )}
            <button className="quiet-button" onClick={() => setPreview(null)}>
              Reject
            </button>
          </div>
        </div>
      )}
    </aside>
  )
}
