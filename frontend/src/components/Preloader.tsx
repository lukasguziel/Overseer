import type { ProgressInfo } from '../types'
import { humanNum } from '../lib/format'
import useSteadyProgress from '../hooks/useSteadyProgress'

// Loading style 1 of 3 — fullscreen overlay for BLOCKING operations
// (analyze, apply-all, …): shows the current phase, a monotonic progress
// bar and the item being processed. Data comes from GET /api/progress,
// which the bridge answers off the main thread.
export default function Preloader({ progress }: { progress: ProgressInfo }) {
  const p = useSteadyProgress(progress)
  if (!p) return null
  return (
    <div className="preloader">
      <div className="pl-box">
        <div className="pl-spinner" />
        <div className="pl-phase">{p.phase}</div>
        <div className={'pl-track' + (p.pct == null ? ' indeterminate' : '')}>
          <div className="pl-fill" style={p.pct != null ? { width: p.pct + '%' } : undefined} />
        </div>
        <div className="pl-meta">
          {p.pct != null
            ? <><b>{p.pct}%</b> · {humanNum(p.current)} / {humanNum(p.total)}</>
            : 'Please wait…'}
        </div>
        {p.detail && <div className="pl-detail" title={p.detail}>{p.detail}</div>}
      </div>
    </div>
  )
}
