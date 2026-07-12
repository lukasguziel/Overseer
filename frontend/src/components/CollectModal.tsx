import { useEffect, useState } from 'react'
import ActionButton from './ActionButton'

// Copy the out-of-project textures INTO the project and relink them relatively.
// The destination subfolder is asked for right here: it is the one thing this
// action needs, and it belongs next to the button that runs it — not parked in
// a sidebar the artist has to find first.
export default function CollectModal({ count, initialDir, busy, onConfirm, onCancel }: {
  count: number
  initialDir: string
  busy?: boolean
  onConfirm: (dir: string) => void
  onCancel: () => void
}) {
  const [dir, setDir] = useState(initialDir || 'tex')

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onCancel() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])

  const clean = dir.trim().replace(/^[\\/]+|[\\/]+$/g, '')
  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-box" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <h3 className="confirm-title">Copy textures into the project</h3>
        <p className="confirm-msg">
          {count} texture{count === 1 ? '' : 's'} live outside the project folder,
          so {count === 1 ? 'it has' : 'they have'} no relative form. {count === 1 ? 'It is' : 'They are'} copied
          into the subfolder below and the materials are relinked to the copies
          (one undo step). The originals stay where they are.
        </p>
        <label className="collect-dir">
          <span>Destination subfolder</span>
          <input className="nl-input" value={dir} autoFocus
            onChange={(e) => setDir(e.target.value)}
            placeholder="tex" />
        </label>
        <p className="hint-sm collect-preview">
          → <code>{'<project>'}/{clean || 'tex'}/</code>
        </p>
        <div className="confirm-actions">
          <button className="ghost" onClick={onCancel}>Cancel</button>
          <ActionButton tone="go" disabled={busy || !clean}
            onClick={() => onConfirm(clean || 'tex')}>
            Copy &amp; relink {count}
          </ActionButton>
        </div>
      </div>
    </div>
  )
}
