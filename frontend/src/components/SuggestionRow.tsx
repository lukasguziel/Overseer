import type { ReactNode } from 'react'
import { IconCheck, IconTrash } from './icons'

// One suggestion with the uniform pair of actions every area shares:
// the green ✓ applies just this row (undoable), the grey one accepts the current state as-is —
// the item is remembered in the config and stops counting as a todo.
// When the apply action DELETES the item (unused materials), pass `deletes`
// so the button shows a trash can — a ✓ next to "delete" reads like "keep".
// With `onFocus` the row body is clickable and selects & frames the object
// in the C4D viewport — the same affordance as every other list in the app.
export default function SuggestionRow({ onApply, onAcceptAsIs, onFocus, busy, applyTitle, deletes, children }: {
  onApply: () => void
  onAcceptAsIs?: () => void // omit where "keep as-is" has no meaning (e.g. tag fixes)
  onFocus?: () => void
  busy: boolean
  applyTitle: string
  deletes?: boolean // the apply action removes the item -> trash icon
  children: ReactNode
}) {
  return (
    <div className={'sg-row rename-row' + (onFocus ? ' sg-focusable' : '')}>
      <span className="sg-body" onClick={onFocus}
        title={onFocus ? 'Click to select & frame it in Cinema 4D' : undefined}>
        {children}
      </span>
      <span className="rn-actions">
        <button className="rn-ok" title={applyTitle} onClick={onApply} disabled={busy}>
          {deletes ? <IconTrash /> : <IconCheck />}
        </button>
        {onAcceptAsIs && (
          <button className="rn-keep" title="Accept as-is — no longer counts as a todo (restore below)"
            onClick={onAcceptAsIs} disabled={busy}><IconCheck /></button>
        )}
      </span>
    </div>
  )
}
