import type { ReactNode } from 'react'
import type { ProgressInfo } from '../types'

// Live preview panel. Header carries the change count and the batch pair
// (top right): ✓ apply everything, ✕ accept everything as-is — both valid
// ways to clear an area. While `loading` with server `progress`, the
// content blurs and a progress bar shows what the plugin is fetching.
export default function Workbench({ title, count, loading, empty, applyLabel, onApply, onAcceptAll, busy, note, progress, children }: {
  title: string
  count: number
  loading: boolean
  empty: string
  applyLabel: string
  onApply: () => void
  onAcceptAll?: () => void
  busy: boolean
  note?: string | null
  progress?: ProgressInfo | null
  children?: ReactNode
}) {
  const prog = loading && progress?.active ? progress : null
  const pct = prog && prog.total > 0
    ? Math.min(100, Math.round(prog.current / prog.total * 100)) : null
  return (
    <div className="wb-preview">
      <div className="wb-preview-head">
        <h3>{title}</h3>
        <span className="wb-count">
          {loading ? 'updating…' : count === 0 ? 'nothing to change' : `${count} change${count === 1 ? '' : 's'}`}
        </span>
        <button className="apply wb-apply" disabled={busy || !count} onClick={onApply}
          title="Apply every suggestion in the list (one undo step)">
          ✓ {applyLabel}
        </button>
        {onAcceptAll && (
          <button className="wb-accept-all" disabled={busy || !count} onClick={onAcceptAll}
            title="Accept everything as-is — nothing changes in the scene, the items stop counting as todos (restore below)">
            ✕ Accept all
          </button>
        )}
      </div>
      {note && <p className="wb-note">{note}</p>}
      <div className={'wb-scroll' + (loading ? ' wb-loading' : '')}>
        {count === 0 && !loading
          ? <div className="wb-empty">{empty}</div>
          : children}
        {prog && (
          <div className="wb-progress">
            <div className="wb-progress-box">
              <div className="pl-phase">{prog.phase}</div>
              <div className={'pl-track' + (pct == null ? ' indeterminate' : '')}>
                <div className="pl-fill" style={pct != null ? { width: pct + '%' } : undefined} />
              </div>
              <div className="pl-meta">
                {pct != null ? <><b>{pct}%</b> · {prog.detail}</> : 'Please wait…'}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
