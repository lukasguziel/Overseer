import type { ProgressInfo } from '../types'
import { humanNum } from '../lib/format'

// Fullscreen overlay while the plugin scans a (large) scene: shows the
// current phase, a progress bar and the object being read. Data comes from
// GET /api/progress, which the bridge answers off the main thread.
export default function Preloader({ progress }: { progress: ProgressInfo }) {
  const { phase, current, total, detail } = progress
  const pct = total > 0 ? Math.min(100, Math.round(current / total * 100)) : null
  return (
    <div className="preloader">
      <div className="pl-box">
        <div className="pl-spinner" />
        <div className="pl-phase">{phase || 'Working…'}</div>
        <div className={'pl-track' + (pct == null ? ' indeterminate' : '')}>
          <div className="pl-fill" style={pct != null ? { width: pct + '%' } : undefined} />
        </div>
        <div className="pl-meta">
          {pct != null
            ? <><b>{pct}%</b> · {humanNum(current)} / {humanNum(total)} objects</>
            : 'Please wait…'}
        </div>
        {detail && <div className="pl-detail" title={detail}>{detail}</div>}
      </div>
    </div>
  )
}
