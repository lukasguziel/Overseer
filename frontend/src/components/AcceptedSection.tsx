import { useState } from 'react'
import Pager, { usePager } from './Pager'
import SectionIntro from './SectionIntro'
import ActionButton from './ActionButton'
import './AcceptedSection.css'

// Everything the user accepted as-is in one area. Same block in every tab: a
// section intro says what the area is, and one toggle opens the list — the
// entries themselves are the only thing behind the fold.
export default function AcceptedSection({ items, onRestore, onRestoreAll, hint, title }: {
  items: string[]
  onRestore: (key: string) => void
  onRestoreAll?: () => void
  hint?: string
  // A tab with SEVERAL accepted lists (Materials: materials + textures) names
  // each one, so two identical "Accepted as-is" heads cannot sit on top of
  // each other. A tab with one list leaves it at the default.
  title?: string
}) {
  const [open, setOpen] = useState(false)
  const pager = usePager([...items].sort())
  if (!items.length) return null
  const n = pager.total
  return (
    <>
    <SectionIntro title={title || 'Accepted as-is'}
      desc={hint || 'Accepted items are remembered (config) and never counted as todos. Items with the same name are accepted together.'} />
    <section className="card kept-card">
      <div className="kept-head-row">
        <button className={'kept-toggle' + (open ? ' on' : '')} aria-expanded={open}
          title={open ? 'Hide the accepted items' : 'Show the accepted items'}
          onClick={() => setOpen(!open)}>
          <span className="kept-caret">▸</span>
          {open ? 'Hide' : 'Show'} {n} accepted item{n === 1 ? '' : 's'}
        </button>
        {onRestoreAll && (
          <ActionButton
            title="Restore every accepted item in this area — they all become todos again"
            onClick={onRestoreAll}>Restore all</ActionButton>
        )}
      </div>
      {open && (
        <>
          <div className="kept-list">
            {pager.rows.map((k) => (
              <div className="kept-row" key={k}>
                <span className="fl-name" title={k}>{k}</span>
                <ActionButton title="Restore — treat as a todo again"
                  onClick={() => onRestore(k)}>Restore</ActionButton>
              </div>
            ))}
          </div>
          <Pager pager={pager} />
        </>
      )}
    </section>
    </>
  )
}
