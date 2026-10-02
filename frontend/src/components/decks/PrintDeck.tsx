import { useEffect, useState } from "react"
import type { DeckDocument } from "../../api"
import { DeckCard } from "./DeckCard"

export function PrintDeck({ deckId }: { deckId: string }) {
  const [deck, setDeck] = useState<DeckDocument | null>(null)
  const [error, setError] = useState("")
  useEffect(() => {
    fetch(`/api/decks/${encodeURIComponent(deckId)}`)
      .then((response) => {
        if (!response.ok) throw new Error("Deck not found")
        return response.json() as Promise<DeckDocument>
      })
      .then(setDeck)
      .catch((reason: Error) => setError(reason.message))
  }, [deckId])
  if (error) return <p role="alert">{error}</p>
  if (!deck) return <p>Loading presentation…</p>
  return (
    <main className="print-deck" data-theme={deck.theme}>
      {deck.cards.map((card, index) => (
        <DeckCard
          key={card.id}
          card={card}
          index={index}
          total={deck.cards.length}
        />
      ))}
    </main>
  )
}
