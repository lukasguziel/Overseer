import { useState } from 'react'
import type { ChangeEntry, ChangeItem } from '../types'

const KIND_LABEL: Record<string, string> = {
  naming: 'Rename',
  translate: 'Translate',
  structure: 'Restructure',
  layers: 'Layers',
  apply_all: 'One-click',
  materials_delete: 'Materials',
  textures_relative: 'Textures',
  plan: 'Plan',
}

// "10:42:07" from a "YYYY-MM-DD HH:MM:SS" timestamp.
function clock(at: string): string {
  return at.length >= 19 ? at.slice(11, 19) : at
}

function ItemRow({ it }: { it: ChangeItem }) {
  const arrow = it.field === 'parent' || it.field === 'layer'
  const before = it.before || (it.field === 'layer' ? '(no layer)' : '(root)')
  const after = it.after || (it.field === 'layer' ? '(no layer)' : '(root)')
  return (
    <tr>
      <td className="ch-field dim">{it.field}</td>
      <td className="dim">{before}</td>
      <td className="arrow">{arrow ? '⇒' : '→'}</td>
      <td>{after}</td>
    </tr>
  )
}

function Entry({ e, onRevert }: { e: ChangeEntry; onRevert: (id: string) => void }) {
  const [open, setOpen] = useState(false)
  const [confirm, setConfirm] = useState(false)
  const n = e.items.length
  return (
    <div className={'ch-entry' + (e.reverted ? ' reverted' : '')}>
      <div className="ch-head">
        <button className="ch-toggle" onClick={() => setOpen(!open)} disabled={!n}>
          <span className="cl-caret">{n ? (open ? '▾' : '▸') : '·'}</span>
          <span className="ch-time">{clock(e.at)}</span>
          <span className={'ch-kind k-' + e.kind}>{KIND_LABEL[e.kind] || e.kind}</span>
          <span className="ch-summary">{e.summary}</span>
        </button>
        {e.reverted
          ? <span className="ch-reverted">reverted</span>
          : e.revertible && (
            confirm ? (
              <span className="mat-confirm">
                revert?
                <button className="mat-yes" onClick={() => { onRevert(e.id); setConfirm(false) }}>✓</button>
                <button className="mat-no" onClick={() => setConfirm(false)}>✕</button>
              </span>
            ) : (
              <button className="ch-revert" title="Undo this change (one undo step)"
                onClick={() => setConfirm(true)}>revert</button>
            )
          )}
      </div>
      {open && n > 0 && (
        <table className="diff ch-items"><tbody>
          {e.items.slice(0, 500).map((it, i) => <ItemRow key={i} it={it} />)}
        </tbody></table>
      )}
    </div>
  )
}

export default function ChangeHistory({ changes, onRevert }: {
  changes: ChangeEntry[]
  onRevert: (id: string) => void
}) {
  if (changes.length === 0) return <div className="fl-empty">No tool changes recorded yet.</div>
  return (
    <div className="ch-list">
      {changes.map((e) => <Entry key={e.id} e={e} onRevert={onRevert} />)}
    </div>
  )
}
