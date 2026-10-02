import type { CSSProperties } from "react"
import type {
  BulletsBlock,
  ChartBlock,
  ColumnsBlock,
  Card,
  HeadingBlock,
  ImageBlock,
  ParagraphBlock,
  QuoteBlock,
  StatBlock,
  TableBlock,
} from "../../api"
import { icons } from "lucide-react"

type Block = Card["blocks"][number]

function Heading({ block }: { block: HeadingBlock }) {
  const className =
    block.level === 1 ? "deck-heading deck-heading--large" : "deck-heading"
  if (block.level === 1) return <h1 className={className}>{block.text}</h1>
  if (block.level === 3) return <h3 className={className}>{block.text}</h3>
  return <h2 className={className}>{block.text}</h2>
}

function Paragraph({ block }: { block: ParagraphBlock }) {
  return <p className="deck-paragraph">{block.text}</p>
}

function Bullets({ block }: { block: BulletsBlock }) {
  return (
    <ul className="deck-bullets">
      {block.items.map((item, index) => (
        <li key={`${item}-${index}`}>{item}</li>
      ))}
    </ul>
  )
}

function Columns({ block }: { block: ColumnsBlock }) {
  return (
    <div
      className="deck-columns"
      style={{ "--column-count": block.columns.length } as CSSProperties}
    >
      {block.columns.map((column, index) => (
        <article className="deck-column" key={`${column.title}-${index}`}>
          <h3>{column.title}</h3>
          <p>{column.body}</p>
        </article>
      ))}
    </div>
  )
}

function Quote({ block }: { block: QuoteBlock }) {
  return (
    <figure className="deck-quote">
      <blockquote>{block.text}</blockquote>
      {block.attribution && <figcaption>{block.attribution}</figcaption>}
    </figure>
  )
}

function Stat({ block }: { block: StatBlock }) {
  return (
    <div className="deck-stat">
      <strong>{block.value}</strong>
      <span>{block.label}</span>
      {block.context && <p>{block.context}</p>}
    </div>
  )
}

function Table({ block }: { block: TableBlock }) {
  return (
    <div className="deck-table-wrap">
      <table className="deck-table">
        <thead>
          <tr>
            {block.headers.map((header) => (
              <th key={header} scope="col">
                {header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {block.rows.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${row[0]}`}>
              {row.map((cell, cellIndex) => (
                <td key={`${rowIndex}-${cellIndex}`}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Image({ block }: { block: ImageBlock }) {
  if (block.asset_id) {
    return (
      <figure className="deck-image">
        <img
          src={`/api/assets/${encodeURIComponent(block.asset_id)}`}
          alt={block.alt || block.prompt}
        />
        {block.alt && <figcaption>{block.alt}</figcaption>}
      </figure>
    )
  }
  return (
    <div
      className="deck-image-placeholder"
      role="img"
      aria-label={block.alt || block.prompt}
    >
      <span>Image placeholder</span>
      <p>{block.alt || block.prompt}</p>
    </div>
  )
}

function Chart({ block }: { block: ChartBlock }) {
  const maximum = Math.max(...block.values, 1)

  return (
    <figure className="deck-chart">
      <figcaption>{block.title}</figcaption>
      <div className="deck-chart__bars">
        {block.labels.map((label, index) => {
          const value = block.values[index] ?? 0
          const height = Math.max((value / maximum) * 100, 3)
          return (
            <div className="deck-chart__item" key={label}>
              <span className="deck-chart__value">{value}</span>
              <div className="deck-chart__track">
                <div
                  className="deck-chart__bar"
                  style={{ height: `${height}%` }}
                />
              </div>
              <span className="deck-chart__label">{label}</span>
            </div>
          )
        })}
      </div>
      {block.illustrative && (
        <p className="deck-chart__note">Illustrative data</p>
      )}
    </figure>
  )
}

function Mermaid({ block }: { block: Extract<Block, { type: "mermaid" }> }) {
  return (
    <figure className="deck-mermaid">
      <pre aria-label={block.caption ?? "Diagram"}>{block.code}</pre>
      {block.caption && <figcaption>{block.caption}</figcaption>}
    </figure>
  )
}

function Icon({ block }: { block: Extract<Block, { type: "icon" }> }) {
  const IconComponent = icons[block.name as keyof typeof icons]
  return IconComponent ? (
    <span className="deck-icon" aria-label={block.label ?? block.name}>
      <IconComponent aria-hidden="true" />
      {block.label && <span>{block.label}</span>}
    </span>
  ) : (
    <span className="deck-icon-fallback" aria-label={block.label ?? block.name}>
      ✦
    </span>
  )
}

export function BlockRenderer({ block }: { block: Block }) {
  switch (block.type) {
    case "heading":
      return <Heading block={block} />
    case "paragraph":
      return <Paragraph block={block} />
    case "bullets":
      return <Bullets block={block} />
    case "columns":
      return <Columns block={block} />
    case "quote":
      return <Quote block={block} />
    case "stat":
      return <Stat block={block} />
    case "table":
      return <Table block={block} />
    case "image":
      return <Image block={block} />
    case "chart":
      return <Chart block={block} />
    case "mermaid":
      return <Mermaid block={block} />
    case "icon":
      return <Icon block={block} />
  }
}
