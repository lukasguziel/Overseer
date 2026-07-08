import { useEffect, useState } from 'react'

// Transient toast (bottom right) surfacing the organizer's status line —
// "Renamed “X” ✓ (undoable)" etc. Sticks while busy, fades out afterwards.
export default function StatusBar({ status, busy }: {
  status: string
  busy: boolean
}) {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    if (!status || status === 'Ready.') { setVisible(false); return }
    setVisible(true)
    if (busy) return
    const t = setTimeout(() => setVisible(false), 4000)
    return () => clearTimeout(t)
  }, [status, busy])
  if (!visible) return null
  const failed = status.endsWith('✗')
  return (
    <div className={'statusbar' + (failed ? ' err' : busy ? ' busy' : '')} role="status">
      {status}
    </div>
  )
}
