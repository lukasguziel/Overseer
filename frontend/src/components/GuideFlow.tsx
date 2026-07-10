import { useState, type ReactNode } from 'react'

// One card of a guided walk-through. `onYes` runs the backend action for this
// finding; No/Skip just advance. `key` must be stable per finding.
export interface GuideCard {
  key: string
  headline: ReactNode
  body: ReactNode
  yesLabel: string
  onYes: () => void
}

// Reusable sequential card flow (feature: guided mode). Shows ONE card at a
// time with Yes / No / Skip and a progress readout, then a done panel. Kept
// generic (cards + labels are injected) so every area guide can reuse it.
// `header` (optional) renders above the progress row and gets the current
// index plus a jump function — the hand guide uses it for its area chips.
export default function GuideFlow({ cards, onExit, labels, header }: {
  cards: GuideCard[]
  onExit: () => void
  labels: { no: string; skip: string; exit: string; done: string; empty: string }
  header?: (state: { index: number; jump: (i: number) => void }) => ReactNode
}) {
  const [index, setIndex] = useState(0)
  const card = cards[index]

  const advance = () => setIndex((i) => i + 1)
  const yes = () => { card.onYes(); advance() }
  const jump = (i: number) => setIndex(Math.max(0, Math.min(cards.length, i)))

  if (!cards.length) {
    return (
      <div className="guide">
        <div className="guide-done">{labels.empty}</div>
        <div className="guide-foot">
          <button className="ghost" onClick={onExit}>{labels.exit}</button>
        </div>
      </div>
    )
  }

  if (!card) {
    return (
      <div className="guide">
        {header?.({ index, jump })}
        <div className="guide-done">{labels.done}</div>
        <div className="guide-foot">
          <button className="apply" onClick={onExit}>{labels.exit}</button>
        </div>
      </div>
    )
  }

  return (
    <div className="guide">
      {header?.({ index, jump })}
      <div className="guide-progress">
        <span>{index + 1} / {cards.length}</span>
        <span className="guide-bar">
          <span className="guide-bar-fill" style={{ width: (index / cards.length) * 100 + '%' }} />
        </span>
        <button className="guide-exit" onClick={onExit} title={labels.exit}>✕</button>
      </div>
      <div className="guide-card" key={card.key}>
        <h3 className="guide-headline">{card.headline}</h3>
        <div className="guide-body">{card.body}</div>
      </div>
      <div className="guide-actions">
        <button className="apply guide-yes" onClick={yes}>{card.yesLabel}</button>
        <button className="ghost" onClick={advance}>{labels.no}</button>
        <button className="ghost guide-skip" onClick={advance}>{labels.skip}</button>
      </div>
    </div>
  )
}
