import { useEffect, useState } from 'react'
import ActionButton from './ActionButton'
import { plural } from '../lib/format'

// Copy the out-of-project textures INTO the project and relink them relatively.
// The destination subfolder is asked for right here: it is the one thing this
// action needs, and it belongs next to the button that runs it — not parked in
// a sidebar the artist has to find first.
// With `file` set the modal collects that ONE texture: it names the file, and
// `materials` lists every material the relink will touch (null = still being
// looked up) — the artist sees the blast radius before confirming.
export default function CollectModal({ count, file, materials, initialDir, busy, onConfirm, onCancel }: {
  count: number
  file?: string
  materials?: string[] | null
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
        <h3 className="confirm-title">
          {file ? 'Copy this texture into the project' : 'Copy textures into the project'}
        </h3>
        <p className="confirm-msg">
          {file
            ? <>“{file}” lives outside the project folder, so it has no
                relative form. It is copied into the subfolder below and every
                material using it is relinked to the copy (one undo step). The
                original stays where it is.</>
            : <>{plural(count, 'texture')} live outside the project folder,
                so {count === 1 ? 'it has' : 'they have'} no relative form. {count === 1 ? 'It is' : 'They are'} copied
                into the subfolder below and the materials are relinked to the copies
                (one undo step). The originals stay where they are.</>}
        </p>
        {file && (
          <p className="confirm-msg">
            {materials == null
              ? 'Checking which materials use this texture…'
              : materials.length
                ? <>Relinks {plural(materials.length, 'material')}: <b>{materials.join(', ')}</b></>
                : 'No material currently holds this exact path — nothing may get relinked.'}
          </p>
        )}
        <label className="collect-dir">
          <span>Destination subfolder</span>
          <input className="nl-input" value={dir} autoFocus
            onChange={(e) => setDir(e.target.value)}
            placeholder="tex" />
        </label>
        <p className="hint-sm collect-preview">
          → <code>{'<project>'}/{clean || 'tex'}/{file || ''}</code>
        </p>
        <div className="confirm-actions">
          <button className="ghost" onClick={onCancel}>Cancel</button>
          <ActionButton tone="go" disabled={busy || !clean}
            onClick={() => onConfirm(clean || 'tex')}>
            {file ? 'Copy & relink' : `Copy & relink ${count}`}
          </ActionButton>
        </div>
      </div>
    </div>
  )
}
