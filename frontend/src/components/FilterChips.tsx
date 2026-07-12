import type { ReactNode } from 'react'
import Tip from './Tip'

// One facet: its name plus a row of toggle chips. No "All" chip — an unset
// facet means all, and clicking the active chip toggles it back off. A chip with
// 0 matches under the OTHER active filters is disabled instead of hidden, so the
// facet never jumps around while filtering.
export interface ChipOption<T> {
  key: T
  label: string
  count: number
  // Tooltip for the inactive chip ("Show only …"); the disabled and active
  // states have one fixed wording everywhere.
  title?: string
  cls?: string
}

export default function FilterChips<T extends string | number>({
  label, tip, options, value, empty, onChange,
}: {
  label: string
  tip?: string
  options: ChipOption<T>[]
  value: T
  empty: T
  onChange: (v: T) => void
}) {
  const head: ReactNode = tip
    ? <Tip text={tip}><span>{label}</span></Tip>
    : <span>{label}</span>
  // A fragment, NOT a wrapper div: the head and the chip row have to stay direct
  // children of the sidebar, or the sibling selectors that space them out
  // (.section-head.sm:first-of-type, the row's own margin) stop matching.
  return (
    <>
      <div className="section-head sm">{head}</div>
      <div className="chip-row side">
        {options.map((o) => {
          const on = value === o.key
          const off = o.count === 0 && !on
          return (
            <button key={String(o.key)} disabled={off}
              className={'chip-btn' + (on ? ' on' : '') + (o.cls ? ' ' + o.cls : '')}
              title={off ? 'No matches with the current filters'
                : on ? 'Click again to clear this filter'
                  : o.title || `Show only ${o.label}`}
              onClick={() => onChange(on ? empty : o.key)}>
              {o.label} <em>{o.count}</em>
            </button>
          )
        })}
      </div>
    </>
  )
}
