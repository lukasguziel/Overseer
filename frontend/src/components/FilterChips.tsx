// One facet = one row of toggle chips. No "All" chip needed: an unset facet
// means all, and clicking the active chip toggles it back off. A chip with 0
// matches under the OTHER active filters is disabled instead of hidden, so the
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

export default function FilterChips<T extends string | number>({ options, value, empty, onChange }: {
  options: ChipOption<T>[]
  value: T
  empty: T
  onChange: (v: T) => void
}) {
  return (
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
  )
}
