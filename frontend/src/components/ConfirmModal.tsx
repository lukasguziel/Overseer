import { useEffect } from 'react'

// "Are you sure?" dialog for batch actions. One shared look everywhere:
// title, an explicit count of what is about to happen, cancel/confirm.
// Escape cancels, the confirm button carries the destructive weight.
// `danger` (deletes, clears): focus starts on CANCEL, so a habitual Enter
// right after opening cannot destroy anything — confirming a build/repair
// action with Enter stays one keystroke.
export default function ConfirmModal({ title, message, confirmLabel, danger, onConfirm, onCancel }: {
  title: string
  message: string
  confirmLabel: string
  danger?: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onCancel() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])
  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-box" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <h3 className="confirm-title">{title}</h3>
        <p className="confirm-msg">{message}</p>
        <div className="confirm-actions">
          <button className="ghost" autoFocus={danger} onClick={onCancel}>Cancel</button>
          <button className="apply" autoFocus={!danger} onClick={onConfirm}>{confirmLabel}</button>
        </div>
      </div>
    </div>
  )
}
