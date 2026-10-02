import { useEffect, useRef, useState } from "react"
import {
  ArrowDown,
  ArrowUp,
  Check,
  Copy,
  Plus,
  Redo2,
  Trash2,
  Undo2,
  Wand2,
} from "lucide-react"
import type { Card, DeckDocument, Layout, Theme } from "../../api"
import { layoutSpecs } from "../../layouts"
import { DeckCard } from "./DeckCard"

type Props = {
  deck: DeckDocument
  onChange: (deck: DeckDocument) => void
  onBack: () => void
  onPresent: () => void
}
const themes: Theme[] = ["ocean", "sunset", "forest"]

export function DeckEditor({ deck, onChange, onBack, onPresent }: Props) {
  const [selected, setSelected] = useState(0)
  const [history, setHistory] = useState<DeckDocument[]>([])
  const [future, setFuture] = useState<DeckDocument[]>([])
  const [aiText, setAiText] = useState("")
  const timer = useRef<number | undefined>(undefined)
  const mounted = useRef(false)
  const card = deck.cards[selected]
  const update = (next: DeckDocument) => {
    setHistory((items) => [...items.slice(-29), deck])
    setFuture([])
    onChange(next)
  }
  useEffect(() => () => window.clearTimeout(timer.current), [])
  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true
      return
    }
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(() => {
      const request = new Request(
        `${window.location.origin}/api/decks/${deck.id}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: deck.title,
            theme: deck.theme,
            cards: deck.cards,
            version: deck.version,
          }),
        },
      )
      void fetch(request).then(async (response) => {
        if (response.ok) onChange(await response.json())
      })
    }, 700)
  }, [deck, onChange])
  const editCard = (patch: Partial<Card>) =>
    update({
      ...deck,
      cards: deck.cards.map((item, i) =>
        i === selected ? { ...item, ...patch } : item,
      ),
    })
  const editBlock = (text: string) => {
    const blocks = card.blocks.map((block, i) =>
      i === 0 && "text" in block ? { ...block, text } : block,
    )
    editCard({ blocks })
  }
  const addCard = () => {
    const next: Card = {
      id: crypto.randomUUID(),
      title: "New card",
      layout: "single_column",
      blocks: [
        { type: "heading", text: "New card", level: 1 },
        { type: "paragraph", text: "Start writing here." },
      ],
    }
    update({ ...deck, cards: [...deck.cards, next] })
    setSelected(deck.cards.length)
  }
  const moveCard = (from: number, to: number) => {
    if (to < 0 || to >= deck.cards.length) return
    const cards = [...deck.cards]
    ;[cards[from], cards[to]] = [cards[to], cards[from]]
    update({ ...deck, cards })
    setSelected(to)
  }
  const undo = () => {
    const previous = history.at(-1)
    if (!previous) return
    setFuture((items) => [deck, ...items])
    setHistory((items) => items.slice(0, -1))
    onChange(previous)
  }
  const redo = () => {
    const next = future[0]
    if (!next) return
    setHistory((items) => [...items, deck])
    setFuture((items) => items.slice(1))
    onChange(next)
  }
  const aiEdit = async (action: string) => {
    const response = await fetch("/api/ai/edit", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        deck_id: deck.id,
        card_id: card.id,
        block_index: 0,
        action,
      }),
    })
    if (response.ok) setAiText((await response.json()).text)
  }
  return (
    <section className="editor-workspace">
      <header className="editor-toolbar">
        <button className="quiet-button" onClick={onBack}>
          ← Library
        </button>
        <input
          className="editor-title"
          value={deck.title}
          onChange={(e) => update({ ...deck, title: e.target.value })}
          aria-label="Presentation title"
        />
        <span className="save-status">
          <Check size={14} /> Autosaved
        </span>
        <button
          className="quiet-button"
          onClick={undo}
          disabled={!history.length}
        >
          <Undo2 size={16} /> Undo
        </button>
        <button
          className="quiet-button"
          onClick={redo}
          disabled={!future.length}
        >
          <Redo2 size={16} /> Redo
        </button>
        <button className="primary-button" onClick={onPresent}>
          Present
        </button>
      </header>
      <div className="editor-body">
        <aside className="card-sidebar">
          <div className="sidebar-heading">
            <strong>Cards</strong>
            <button
              className="icon-button"
              onClick={addCard}
              aria-label="Add card"
            >
              <Plus size={16} />
            </button>
          </div>
          {deck.cards.map((item, i) => (
            <div
              className={`card-sidebar__item ${i === selected ? "is-selected" : ""}`}
              key={item.id}
              onClick={() => setSelected(i)}
            >
              <span>{i + 1}</span>
              <strong>{item.title}</strong>
              <div className="sidebar-actions">
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    moveCard(i, i - 1)
                  }}
                  aria-label="Move card up"
                >
                  <ArrowUp size={13} />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    moveCard(i, i + 1)
                  }}
                  aria-label="Move card down"
                >
                  <ArrowDown size={13} />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    const copy = {
                      ...item,
                      id: crypto.randomUUID(),
                      title: `${item.title} copy`,
                    }
                    update({
                      ...deck,
                      cards: [
                        ...deck.cards.slice(0, i + 1),
                        copy,
                        ...deck.cards.slice(i + 1),
                      ],
                    })
                    setSelected(i + 1)
                  }}
                  aria-label="Duplicate card"
                >
                  <Copy size={13} />
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation()
                    if (deck.cards.length > 1) {
                      update({
                        ...deck,
                        cards: deck.cards.filter((_, index) => index !== i),
                      })
                      setSelected(Math.max(0, i - 1))
                    }
                  }}
                  aria-label="Delete card"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
          ))}
        </aside>
        <main className="editor-canvas">
          <div className="editor-controls">
            <label>
              Theme{" "}
              <select
                aria-label="Presentation theme"
                value={deck.theme}
                onChange={(e) =>
                  update({ ...deck, theme: e.target.value as Theme })
                }
              >
                {themes.map((theme) => (
                  <option key={theme}>{theme}</option>
                ))}
              </select>
            </label>
            <label>
              Layout{" "}
              <select
                value={card.layout}
                onChange={(e) => editCard({ layout: e.target.value as Layout })}
              >
                {layoutSpecs.map((layout) => (
                  <option value={layout.id} key={layout.id}>
                    {layout.label}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="quiet-button"
              onClick={() => void aiEdit("rewrite")}
            >
              <Wand2 size={15} /> AI rewrite
            </button>
          </div>
          <div className="editable-card" data-theme={deck.theme}>
            <DeckCard card={card} index={selected} total={deck.cards.length} />
            <input
              className="inline-card-title"
              value={card.title}
              onChange={(e) => editCard({ title: e.target.value })}
              aria-label="Card title"
            />
            {card.blocks[0] && "text" in card.blocks[0] && (
              <textarea
                className="inline-block-editor"
                value={card.blocks[0].text}
                onChange={(e) => editBlock(e.target.value)}
                aria-label="Card content"
              />
            )}
            {aiText && (
              <div className="ai-suggestion">
                <strong>AI suggestion</strong>
                <p>{aiText}</p>
                <button
                  className="primary-button"
                  onClick={() => {
                    editBlock(aiText)
                    setAiText("")
                  }}
                >
                  Accept
                </button>
                <button className="quiet-button" onClick={() => setAiText("")}>
                  Reject
                </button>
              </div>
            )}
          </div>
        </main>
      </div>
    </section>
  )
}
