import { useEffect, useState } from 'react'

// Transient toast (bottom right) surfacing the organizer's status line —
// "Renamed “X” ✓ (undoable)" etc. Sticks while busy, fades out afterwards.
//
// EXCEPT when the message is bad news: a failure or an action that did nothing
// must NOT vanish after four seconds. It stays until the artist dismisses it,
// wraps instead of truncating, and can be copied — that message is the only
// explanation they get.
const isBadNews = (s: string) =>
  s.endsWith('✗') || s.startsWith('Nothing') || s.startsWith('No ')

export default function StatusBar({ status, busy }: {
  status: string
  busy: boolean
}) {
  const [visible, setVisible] = useState(false)
  const sticky = isBadNews(status)

  useEffect(() => {
    if (!status || status === 'Ready.') { setVisible(false); return }
    setVisible(true)
    if (busy || isBadNews(status)) return
    const t = setTimeout(() => setVisible(false), 4000)
    return () => clearTimeout(t)
  }, [status, busy])

  if (!visible) return null
  const failed = status.endsWith('✗')
  return (
    <div className={'statusbar' + (failed ? ' err' : busy ? ' busy' : '')
        + (sticky ? ' sticky' : '')} role="status">
      <span className="statusbar-text">{status}</span>
      {sticky && (
        <button className="statusbar-close" title="Dismiss"
          onClick={() => setVisible(false)}>✕</button>
      )}
    </div>
  )
}
