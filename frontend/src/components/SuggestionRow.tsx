import type { ReactNode } from 'react'

// One suggestion with the uniform pair of actions every area shares:
// ✓ applies just this row (undoable), = accepts the current state as-is —
// the item is remembered in the config and stops counting as a todo.
// With `onFocus` the row body is clickable and selects & frames the object
// in the C4D viewport — the same affordance as every other list in the app.
export default function SuggestionRow({ onApply, onAcceptAsIs, onFocus, busy, applyTitle, children }: {
  onApply: () => void
  onAcceptAsIs?: () => void // omit where "keep as-is" has no meaning (e.g. tag fixes)
  onFocus?: () => void
  busy: boolean
  applyTitle: string
  children: ReactNode
}) {
  return (
    <div className={'sg-row rename-row' + (onFocus ? ' sg-focusable' : '')}>
      <span className="sg-body" onClick={onFocus}
        title={onFocus ? 'Click to select & frame it in Cinema 4D' : undefined}>
        {children}
      </span>
      <span className="rn-actions">
        <button className="rn-ok" title={applyTitle} onClick={onApply} disabled={busy}>✓</button>
        {onAcceptAsIs && (
          <button className="rn-keep" title="Accept as-is — no longer counts as a todo (restore below)"
            onClick={onAcceptAsIs} disabled={busy}>=</button>
        )}
      </span>
    </div>
  )
}
