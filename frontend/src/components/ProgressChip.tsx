import type { ProgressInfo } from '../types'
import useSteadyProgress from '../hooks/useSteadyProgress'

// Non-blocking loading indicator (bottom left): shown whenever the plugin
// is working in the BACKGROUND — debounced re-analyses after row actions,
// overview preloads, batch jobs — i.e. progress is active but no overlay or
// inline preview loader owns it. Same visual language as the other loaders
// (phase + pl-track bar), so "something is loading" always looks the same.
export default function ProgressChip({ progress }: { progress: ProgressInfo | null }) {
  const p = useSteadyProgress(progress)
  if (!p) return null
  return (
    <div className="progress-chip" role="status">
      <div className="pc-spinner" />
      <div className="pc-text">
        <span className="pc-phase">{p.phase}</span>
        {p.detail && <span className="pc-detail">{p.detail}</span>}
      </div>
      <div className={'pl-track pc-track' + (p.pct == null ? ' indeterminate' : '')}>
        <div className="pl-fill" style={p.pct != null ? { width: p.pct + '%' } : undefined} />
      </div>
      {p.pct != null && <span className="pc-pct">{p.pct}%</span>}
    </div>
  )
}
