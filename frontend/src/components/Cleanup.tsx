import { useState } from 'react'
import type { FocusFn } from './Treemap'

export interface CleanupItem {
  guid: number
  name: string
  meta?: string
}

export interface CleanupBucket {
  key: string
  label: string
  items: CleanupItem[]
}

// One row: click the name to select & frame in C4D, ✎ opens an inline rename
// editor (Enter/✓ applies via the API, Esc cancels), ✕ accepts the name
// as-is — it stops counting as a todo and the area score goes up.
function Row({ it, onFocus, onRename, onKeep, busy }: {
  it: CleanupItem
  onFocus?: FocusFn
  onRename?: (guid: number, name: string) => void
  onKeep?: (name: string) => void
  busy?: boolean
}) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(it.name)

  const commit = () => {
    const v = value.trim()
    if (v && v !== it.name) onRename?.(it.guid, v)
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="cl-item cl-edit">
        <input autoFocus value={value} onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit()
            else if (e.key === 'Escape') setEditing(false)
          }} />
        <button className="rn-ok" title="Rename (undoable)" onClick={commit}>✓</button>
        <button className="rn-no" title="Cancel" onClick={() => setEditing(false)}>✕</button>
      </div>
    )
  }
  return (
    <div className="cl-item">
      <button className="cl-focus" onClick={() => onFocus?.(it.guid, it.name)}
        title="Select & frame in viewport">
        <span className="fl-name">{it.name}</span>
        {it.meta && <span className="fl-meta">{it.meta}</span>}
      </button>
      {onRename && (
        <button className="cl-rename" title="Rename this object"
          onClick={() => { setValue(it.name); setEditing(true) }}>✎</button>
      )}
      {onKeep && (
        <button className="rn-no cl-keep" disabled={busy}
          title="Accept as-is — no longer counts as a todo (restore in the Accepted section)"
          onClick={() => onKeep(it.name)}>✕</button>
      )}
    </div>
  )
}

// Cleanup accordion: compact list of problem groups, one open at a time.
export default function Cleanup({ buckets, onFocus, onRename, onKeep, busy }: {
  buckets: CleanupBucket[]
  onFocus?: FocusFn
  onRename?: (guid: number, name: string) => void
  onKeep?: (name: string) => void
  busy?: boolean
}) {
  const [open, setOpen] = useState<string | null>(
    () => buckets.find((b) => b.items.length)?.key || null)
  return (
    <div className="cleanup">
      {buckets.map((b) => {
        const isOpen = open === b.key
        return (
          <div className={'cl-bucket' + (isOpen ? ' open' : '')} key={b.key}>
            <button className="cl-head" onClick={() => setOpen(isOpen ? null : b.key)}>
              <span className="cl-caret">{isOpen ? '▾' : '▸'}</span>
              <span className="cl-label">{b.label}</span>
              <span className={'cl-count' + (b.items.length ? ' warn' : '')}>{b.items.length}</span>
            </button>
            {isOpen && (b.items.length
              ? <div className="cl-items">
                  {b.items.slice(0, 40).map((it) => (
                    <Row key={it.guid} it={it} onFocus={onFocus} onRename={onRename}
                      onKeep={onKeep} busy={busy} />
                  ))}
                  {b.items.length > 40 && <div className="fl-more">+{b.items.length - 40} more</div>}
                </div>
              : <div className="cl-clean">Clean 🎉</div>)}
          </div>
        )
      })}
    </div>
  )
}
