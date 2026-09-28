import type { Card } from "../../api"
import { layoutSpecs } from "../../layouts"
import { BlockRenderer } from "./BlockRenderer"

type DeckCardProps = {
  card: Card
  index: number
  total: number
  presentation?: boolean
}

export function DeckCard({
  card,
  index,
  total,
  presentation = false,
}: DeckCardProps) {
  return (
    <article
      className={`deck-card deck-layout--${card.layout}${presentation ? " deck-card--presentation" : ""}`}
      data-layout={card.layout}
      title={
        layoutSpecs.find((layout) => layout.id === card.layout)?.description
      }
      aria-label={`Card ${index + 1}: ${card.title}`}
    >
      <div className="deck-card__content">
        {card.blocks.map((block, blockIndex) => (
          <BlockRenderer
            block={block}
            key={`${card.id ?? index}-${block.type}-${blockIndex}`}
          />
        ))}
      </div>
      <footer className="deck-card__footer">
        <span>{card.title}</span>
        <span>
          {index + 1} / {total}
        </span>
      </footer>
    </article>
  )
}
