import type { ReactNode } from 'react'

// Live-Preview-Panel mit sticky Apply-Leiste. Zeigt eine Diff-Tabelle.
export default function Workbench({ title, count, loading, empty, applyLabel, onApply, busy, note, children }: {
  title: string
  count: number
  loading: boolean
  empty: string
  applyLabel: string
  onApply: () => void
  busy: boolean
  note?: string | null
  children?: ReactNode
}) {
  return (
    <div className="wb-preview">
      <div className="wb-preview-head">
        <h3>{title}</h3>
        <span className="wb-count">
          {loading ? 'updating…' : count === 0 ? 'nothing to change' : `${count} change${count === 1 ? '' : 's'}`}
        </span>
      </div>
      {note && <p className="wb-note">{note}</p>}
      <div className="wb-scroll">
        {count === 0 && !loading
          ? <div className="wb-empty">{empty}</div>
          : children}
      </div>
      <div className="wb-applybar">
        <button className="apply lg" disabled={busy || !count} onClick={onApply}>
          {applyLabel} {count ? `(${count})` : ''}
        </button>
      </div>
    </div>
  )
}
