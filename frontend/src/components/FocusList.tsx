import { catColor } from '../lib/colors'
import type { FocusFn } from './Treemap'

export interface FocusItem {
  guid: number
  name: string
  category?: string
  meta?: string
}

// Compact clickable list (cleanup targets).
export default function FocusList({ items, onFocus, empty, max = 8 }: {
  items: FocusItem[]
  onFocus?: FocusFn
  empty?: string
  max?: number
}) {
  if (!items.length) return <div className="fl-empty">{empty || 'None 🎉'}</div>
  return (
    <div className="focuslist">
      {items.slice(0, max).map((n, i) => (
        <button key={n.guid ?? i} className="fl-row" onClick={() => onFocus?.(n.guid, n.name)}
          title="Select & frame in viewport">
          <span className="fl-dot" style={{ background: catColor(n.category || 'other') }} />
          <span className="fl-name">{n.name}</span>
          {n.meta && <span className="fl-meta">{n.meta}</span>}
        </button>
      ))}
      {items.length > max && <div className="fl-more">+{items.length - max} more</div>}
    </div>
  )
}
