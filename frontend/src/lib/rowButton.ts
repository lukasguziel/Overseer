import type { KeyboardEvent } from 'react'

// Keyboard affordance for clickable rows that are not <button>s (data-grid
// rows, table rows, inline object names): Tab reaches them, Enter or Space
// activates. Key events bubbling up from real buttons INSIDE the row are
// ignored — the row only reacts to its own key press. The row keeps its own
// onClick; these props only add the keyboard path.
export function rowKeys(onActivate: () => void) {
  return {
    tabIndex: 0,
    onKeyDown: (e: KeyboardEvent<HTMLElement>) => {
      if (e.target !== e.currentTarget) return
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onActivate() }
    },
  }
}

// Same, for non-table elements (div/span rows) where the button role is safe.
// Never put role="button" on a <tr> — that breaks the table semantics; use
// rowKeys there instead.
export const rowButton = (onActivate: () => void) =>
  ({ role: 'button' as const, ...rowKeys(onActivate) })
