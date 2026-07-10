import { useState } from 'react'
import Pager, { usePager } from './Pager'

// Collapsed accordion listing everything the user accepted as-is in this
// area. Identical in every tab; entries can be pulled back with "restore".
export default function AcceptedSection({ items, onRestore, onRestoreAll, hint }: {
  items: string[]
  onRestore: (key: string) => void
  onRestoreAll?: () => void
  hint?: string
}) {
  const [open, setOpen] = useState(false)
  const pager = usePager([...items].sort())
  if (!items.length) return null
  return (
    <section className="card">
      <div className="kept-head-row">
        <button className="kept-head" onClick={() => setOpen(!open)}>
          <span className="cl-caret">{open ? '▾' : '▸'}</span>
          Accepted as-is <span className="kept-count">{pager.total}</span>
        </button>
        {onRestoreAll && (
          <button className="kept-restore-all"
            title="Restore every accepted item in this area — they all become todos again"
            onClick={onRestoreAll}>restore all ✕</button>
        )}
      </div>
      {open && (
        <>
          <div className="kept-list">
            {pager.rows.map((k) => (
              <div className="kept-row" key={k}>
                <span className="fl-name" title={k}>{k}</span>
                <button className="kept-restore" title="Restore — treat as a todo again"
                  onClick={() => onRestore(k)}>restore</button>
              </div>
            ))}
          </div>
          <Pager pager={pager} />
        </>
      )}
      <p className="hint-sm" style={{ marginTop: 8 }}>
        {hint || 'Accepted items are remembered (config) and never counted as todos. Items with the same name are accepted together.'}
      </p>
    </section>
  )
}
