import type { ReactNode } from 'react'

// One suggestion with the uniform pair of actions every area shares:
// ✓ applies just this row (undoable), ✕ accepts the current state as-is —
// the item is remembered in the config and stops counting as a todo.
export default function SuggestionRow({ onApply, onAcceptAsIs, busy, applyTitle, children }: {
  onApply: () => void
  onAcceptAsIs: () => void
  busy: boolean
  applyTitle: string
  children: ReactNode
}) {
  return (
    <div className="sg-row rename-row">
      {children}
      <span className="rn-actions">
        <button className="rn-ok" title={applyTitle} onClick={onApply} disabled={busy}>✓</button>
        <button className="rn-keep" title="Accept as-is — no longer counts as a todo (restore below)"
          onClick={onAcceptAsIs} disabled={busy}>=</button>
      </span>
    </div>
  )
}
