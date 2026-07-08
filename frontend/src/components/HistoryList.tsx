import { useState, type ReactNode } from 'react'
import Pager, { usePager } from './Pager'

// One generic history row in the change-history look: time · kind chip ·
// summary, optionally expandable (details) with an action slot on the right.
export interface HistoryRow {
  id: string
  time: string          // short clock/date shown first
  kind: string          // chip css key (k-<kind>)
  kindLabel: string     // chip text
  summary: string
  dimmed?: boolean      // e.g. reverted entries
  action?: ReactNode    // right side (revert button, badge, …)
  details?: ReactNode   // expandable body; row is expandable iff set
}

function Entry({ r }: { r: HistoryRow }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={'ch-entry' + (r.dimmed ? ' reverted' : '')}>
      <div className="ch-head">
        <button className="ch-toggle" onClick={() => setOpen(!open)} disabled={!r.details}>
          <span className="cl-caret">{r.details ? (open ? '▾' : '▸') : '·'}</span>
          <span className="ch-time">{r.time}</span>
          <span className={'ch-kind k-' + r.kind}>{r.kindLabel}</span>
          <span className="ch-summary">{r.summary}</span>
        </button>
        {r.action}
      </div>
      {open && r.details}
    </div>
  )
}

// Shared list shell: change-history styling + 10-per-page pagination.
export default function HistoryList({ rows, perPage = 10 }: {
  rows: HistoryRow[]
  perPage?: number
}) {
  const pager = usePager(rows, perPage)
  return (
    <div className="ch-list">
      {pager.rows.map((r) => <Entry key={r.id} r={r} />)}
      <Pager pager={pager} />
    </div>
  )
}
