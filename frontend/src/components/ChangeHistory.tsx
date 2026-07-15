import { useState } from 'react'
import type { ChangeEntry, ChangeItem } from '../types'
import HistoryList, { type HistoryRow } from './HistoryList'
import { plural } from '../lib/format'

const KIND_LABEL: Record<string, string> = {
  naming: 'Rename',
  translate: 'Translate',
  structure: 'Restructure',
  layers: 'Layers',
  apply_all: 'One-click',
  materials_delete: 'Materials',
  textures_relative: 'Textures',
  textures_collect: 'Textures',
  textures_relink: 'Textures',
  textures_edit: 'Textures',
  textures_repath: 'Textures',
  textures_resize: 'Textures',
  textures_clear: 'Textures',
  plan: 'Plan',
}

// "10:42:07" from a "YYYY-MM-DD HH:MM:SS" timestamp.
function clock(at: string): string {
  return at.length >= 19 ? at.slice(11, 19) : at
}

// One op inside a run: its before→after diff plus a per-op revert control.
function ItemRow({ it, canRevert, onRevert }: {
  it: ChangeItem
  canRevert: boolean
  onRevert?: () => void
}) {
  const arrow = it.field === 'parent' || it.field === 'layer'
  const base = (p: string) => p.split(/[/\\]/).pop() || p
  const before = it.field === 'texpath' ? base(it.before)
    : it.before || (it.field === 'layer' ? '(no layer)' : '(root)')
  const after = it.field === 'texpath' ? base(it.after)
    : it.after || (it.field === 'layer' ? '(no layer)' : '(root)')
  return (
    <tr className={it.reverted ? 'ch-item-reverted' : undefined}>
      <td className="ch-field dim">{it.field}</td>
      <td className="dim">{before}</td>
      <td className="arrow">{arrow ? '⇒' : '→'}</td>
      <td>{after}</td>
      <td className="ch-item-action">
        {it.reverted
          ? <span className="ch-reverted">reverted</span>
          : canRevert && onRevert
            ? <button className="ch-revert" title="Revert just this op (one undo step)"
                onClick={onRevert}>revert</button>
            : null}
      </td>
    </tr>
  )
}

// Run-level revert with inline confirm. Reverts the whole run — or, in an
// area view of a mixed one-click run, only this area's ops (`indices`).
function RevertAction({ e, indices, onRevert }: {
  e: ChangeEntry
  indices?: number[]
  onRevert: (id: string, items?: number[]) => void
}) {
  const [confirm, setConfirm] = useState(false)
  const done = e.reverted || (indices != null
    && indices.every((i) => e.items[i]?.reverted))
  if (done) return <span className="ch-reverted">reverted</span>
  if (!e.revertible) return null
  return confirm ? (
    <span className="mat-confirm">
      revert {indices ? `${plural(indices.length, 'op')}` : 'all'}?
      <button className="mat-yes" onClick={() => { onRevert(e.id, indices); setConfirm(false) }}>✓</button>
      <button className="mat-no" onClick={() => setConfirm(false)}>✕</button>
    </span>
  ) : (
    <button className="ch-revert"
      title={indices
        ? "Revert this area's ops within the run (one undo step)"
        : 'Revert the whole run (one undo step)'}
      onClick={() => setConfirm(true)}>{indices ? 'revert ops' : 'revert run'}</button>
  )
}

export default function ChangeHistory({ changes, onRevert, field }: {
  changes: ChangeEntry[]
  onRevert: (id: string, items?: number[]) => void
  field?: ChangeItem['field']  // area view: reduce mixed one-click runs to this op field
}) {
  if (changes.length === 0) return <div className="empty-note">No tool changes recorded yet.</div>
  const rows: HistoryRow[] = changes.map((e) => {
    // An area view shows a mixed one-click run reduced to its own ops — kept
    // with their ORIGINAL indices, so a per-op revert hits the right item.
    const mixed = field != null && e.kind === 'apply_all'
    const items = e.items
      .map((it, i) => ({ it, i }))
      .filter(({ it }) => !mixed || it.field === field)
    return {
      id: e.id,
      time: clock(e.at),
      kind: e.kind,
      kindLabel: KIND_LABEL[e.kind] || e.kind,
      summary: mixed ? `${e.summary} · ${items.length} here` : e.summary,
      dimmed: e.reverted || (mixed && items.every(({ it }) => it.reverted)),
      action: <RevertAction e={e} onRevert={onRevert}
        indices={mixed ? items.map(({ i }) => i) : undefined} />,
      details: items.length > 0 ? (
        <table className="diff ch-items"><tbody>
          {items.slice(0, 500).map(({ it, i }) => (
            <ItemRow key={i} it={it} canRevert={e.revertible && !e.reverted}
              onRevert={() => onRevert(e.id, [i])} />
          ))}
        </tbody></table>
      ) : undefined,
    }
  })
  return <HistoryList rows={rows} perPage={10} />
}
