import { useState, type ReactNode } from 'react'
import type { ProgressInfo } from '../types'
import useSteadyProgress from '../hooks/useSteadyProgress'
import ConfirmModal from './ConfirmModal'
import ActionButton, { type ActionTone } from './ActionButton'

// Live preview panel — loading style 2 of 3: the inline preview loader.
// Header carries the change count and the batch pair
// (top right): ✓ apply everything, = accept everything as-is — both valid
// ways to clear an area. Either action is optional, so worklists without a
// batch apply (e.g. the no-layer list) reuse the same panel. While
// `loading` with server `progress`, the content blurs and a monotonic
// progress bar shows what the plugin is fetching.
export default function Workbench({ title, count, loading, empty, applyLabel, applyTone = 'go', onApply, onAcceptAll, busy, note, hint, progress, extra, children }: {
  title: string
  count: number
  loading: boolean
  empty: ReactNode
  applyLabel?: string
  // What the batch apply DOES: it usually builds ('go'), but "Delete all
  // unused materials" removes — that one asks for the danger tone.
  applyTone?: ActionTone
  onApply?: () => void
  onAcceptAll?: () => void
  busy: boolean
  note?: string | null
  hint?: string
  progress?: ProgressInfo | null
  // Protected/informational rows rendered alongside the actionable ones
  // (e.g. only-on-hidden materials): counted in the header, keep the list
  // visible even when nothing is actionable, but batch buttons ignore them.
  extra?: { count: number; label: string } | null
  children?: ReactNode
}) {
  const steady = useSteadyProgress(progress)
  const prog = loading ? steady : null
  const pct = prog?.pct ?? null
  // Batch actions always confirm first — with the exact count on the table.
  const [confirm, setConfirm] = useState<'apply' | 'accept' | null>(null)
  const n = `${count} item${count === 1 ? '' : 's'}`
  return (
    <div className="wb-preview">
      <div className="wb-preview-head">
        <h3>{title}</h3>
        <span className="wb-count">
          {loading ? 'updating…' : count === 0 ? 'nothing to change' : `${count} change${count === 1 ? '' : 's'}`}
          {!loading && (extra?.count ?? 0) > 0 && ` · ${extra!.count} ${extra!.label}`}
        </span>
        {onApply && (
          <ActionButton tone={applyTone} disabled={busy || !count} onClick={() => setConfirm('apply')}
            title="Apply every suggestion in the list (one undo step)">
            {applyLabel || 'Apply all'}
          </ActionButton>
        )}
        {onAcceptAll && (
          <ActionButton disabled={busy || !count} onClick={() => setConfirm('accept')}
            title="Keep everything exactly as it is — nothing changes in the scene, the items stop counting as todos (restore below)">
            Keep all as-is
          </ActionButton>
        )}
      </div>
      {confirm === 'apply' && onApply && (
        <ConfirmModal title={applyLabel || 'Apply all'}
          message={`You are about to process ${n} in one go (one undo step in Cinema 4D). Continue?`}
          confirmLabel={`✓ ${applyLabel || 'Apply'} ${n}`}
          onConfirm={() => { setConfirm(null); onApply() }}
          onCancel={() => setConfirm(null)} />
      )}
      {confirm === 'accept' && onAcceptAll && (
        <ConfirmModal title="Keep all as-is"
          message={`You are about to accept ${n} as-is. Nothing changes in the scene — they just stop counting as todos (restore any time below). Continue?`}
          confirmLabel={`= Accept ${n}`}
          onConfirm={() => { setConfirm(null); onAcceptAll() }}
          onCancel={() => setConfirm(null)} />
      )}
      {note && <p className="wb-note">{note}</p>}
      {hint && count > 0 && !loading && <p className="hint-sm wb-hint">{hint}</p>}
      <div className={'wb-scroll' + (loading ? ' wb-loading' : '')}>
        {count === 0 && (extra?.count ?? 0) === 0 && !loading
          ? <div className="empty-note mid">{empty}</div>
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
