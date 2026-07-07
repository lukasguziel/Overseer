import { useState } from 'react'

// Liste ungenutzter Materialien mit inline-Loeschbestaetigung (kein window.confirm
// -> im eingebetteten QtWebEngine unzuverlaessig).
export default function UnusedMaterials({ names, onDelete, max = 20 }: {
  names: string[]
  onDelete: (name: string) => void
  max?: number
}) {
  const [confirm, setConfirm] = useState<string | null>(null)
  if (!names.length) return <div className="fl-empty">Every material is in use 🎉</div>
  return (
    <div className="focuslist">
      {names.slice(0, max).map((nm, i) => (
        <div className="fl-row static mat-row" key={i}>
          <span className="fl-dot" style={{ background: 'var(--dim2)' }} />
          <span className="fl-name">{nm}</span>
          {confirm === nm ? (
            <span className="mat-confirm">
              delete?
              <button className="mat-yes" title="Confirm delete"
                onClick={() => { onDelete(nm); setConfirm(null) }}>✓</button>
              <button className="mat-no" title="Cancel" onClick={() => setConfirm(null)}>✕</button>
            </span>
          ) : (
            <button className="mat-x" title="Delete this material (undoable)"
              onClick={() => setConfirm(nm)}>×</button>
          )}
        </div>
      ))}
      {names.length > max && <div className="fl-more">+{names.length - max} more</div>}
    </div>
  )
}
