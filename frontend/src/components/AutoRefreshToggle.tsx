import { IconRefresh } from './icons'

// Watches the C4D scene: when on, the app polls a cheap change token and
// re-analyzes automatically whenever the scene changes (object added, geometry
// edited, reparented) — no manual "Refresh analysis" click needed.
export default function AutoRefreshToggle({ autoRefresh, setAutoRefresh, busy }: {
  autoRefresh: boolean
  setAutoRefresh: (v: boolean) => void
  busy?: boolean
}) {
  return (
    <button
      className={'auto-toggle' + (autoRefresh ? ' on' : '') + (autoRefresh && busy ? ' spin' : '')}
      onClick={() => setAutoRefresh(!autoRefresh)}
      title={autoRefresh
        ? 'Auto-refresh on — the analysis follows scene changes in C4D. Click to stop.'
        : 'Auto-refresh off — click to watch the scene and update the stats automatically on every change.'}>
      <IconRefresh />
      <span>Auto<small>{autoRefresh ? 'watching scene' : 'manual'}</small></span>
    </button>
  )
}
