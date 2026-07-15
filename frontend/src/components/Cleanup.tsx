import { useState } from 'react'
import type { FocusFn } from './Treemap'
import Pager, { usePager } from './Pager'
import ConfirmModal from './ConfirmModal'
import ActionButton from './ActionButton'
import { IconCheck } from './icons'
import { plural } from '../lib/format'

export interface CleanupItem {
  guid: number
  name: string
  meta?: string
}

export interface CleanupBucket {
  key: string
  label: string
  items: CleanupItem[]
  hint?: string          // short "what is this & what to do" line shown when open
  empty?: string         // friendly all-done line (centered, like the Workbench empty state)
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
        <button className="rn-ok" title="Rename (undoable)" onClick={commit}><IconCheck /></button>
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
        <button className="rn-keep cl-keep" disabled={busy}
          title="Accept as-is — no longer counts as a todo (restore in the Accepted section)"
          onClick={() => onKeep(it.name)}><IconCheck /></button>
      )}
    </div>
  )
}

// One open bucket's body: hint + rows, paginated 10 per page.
function BucketBody({ b, onFocus, onRename, onKeep, busy }: {
  b: CleanupBucket
  onFocus?: FocusFn
  onRename?: (guid: number, name: string) => void
  onKeep?: (name: string) => void
  busy?: boolean
}) {
  const pager = usePager(b.items, 10)
  if (!b.items.length) {
    return <div className="empty-note mid">{b.empty || 'Nothing left to decide here'}</div>
  }
  return (
    <div className="cl-items">
      {pager.rows.map((it) => (
        <Row key={it.guid} it={it} onFocus={onFocus} onRename={onRename}
          onKeep={onKeep} busy={busy} />
      ))}
      <Pager pager={pager} />
    </div>
  )
}

// Cleanup panels: the problem groups side by side (50/50), all open at once —
// each with its own 10-per-page pager. With `onKeepAll`, every panel head
// carries a slim "keep all" button that accepts the whole bucket as-is
// (confirm modal with the exact count).
export default function Cleanup({ buckets, onFocus, onRename, onKeep, onKeepAll, busy }: {
  buckets: CleanupBucket[]
  onFocus?: FocusFn
  onRename?: (guid: number, name: string) => void
  onKeep?: (name: string) => void
  onKeepAll?: (names: string[], bucket: CleanupBucket) => void
  busy?: boolean
}) {
  const [confirm, setConfirm] = useState<CleanupBucket | null>(null)
  return (
    <div className="cleanup">
      {buckets.map((b) => (
        <div className="cl-bucket" key={b.key}>
          <div className="cl-head-row">
            <h3 className="cl-label">{b.label}</h3>
            {onKeepAll && b.items.length > 0 && (
              <ActionButton className="cl-keepall" disabled={busy}
                title={`Accept all ${b.items.length} as-is — they stop counting as todos (restore in the Accepted section)`}
                onClick={() => setConfirm(b)}>
                Keep all as-is
              </ActionButton>
            )}
            <span className={'cl-count' + (b.items.length ? ' warn' : '')}>
              {b.items.length ? `${plural(b.items.length, 'change')}` : 'no changes'}
            </span>
          </div>
          {b.hint && <p className="cl-hint">{b.hint}</p>}
          <BucketBody b={b} onFocus={onFocus} onRename={onRename}
            onKeep={onKeep} busy={busy} />
        </div>
      ))}
      {confirm && onKeepAll && (
        <ConfirmModal
          title={`Keep all as-is — ${confirm.label}`}
          message={`Accept all ${plural(confirm.items.length, 'item')} in “${confirm.label}” as-is. Nothing changes in the scene — they just stop counting as todos (restore any time in the Accepted section). Continue?`}
          confirmLabel={`✓ Accept ${confirm.items.length}`}
          onConfirm={() => {
            const b = confirm
            setConfirm(null)
            onKeepAll(b.items.map((it) => it.name), b)
          }}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  )
}
