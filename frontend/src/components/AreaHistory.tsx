import { useState } from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import type { ChangeEntry, ChangeItem } from '../types'
import ChangeHistory from './ChangeHistory'
import InfoButton from './InfoButton'
import SectionIntro from './SectionIntro'
import './AcceptedSection.css'

// The change history of ONE area, at the foot of the tab where those changes
// are made: only the runs that touched this area, revertible right here. The
// complete cross-area log stays on the Misc tab.
//
// A one-click run (apply_all) mixes areas inside a single entry — `field`
// names the op field that belongs here ('name' | 'parent' | 'layer'), and the
// entry is shown (and run-reverted) reduced to exactly those ops.

export function areaChanges(changes: ChangeEntry[], kinds: string[],
  field?: ChangeItem['field']): ChangeEntry[] {
  return changes.filter((e) =>
    kinds.includes(e.kind)
    || (field != null && e.kind === 'apply_all'
      && e.items.some((it) => it.field === field)))
}

// "10:42:07" from a "YYYY-MM-DD HH:MM:SS" timestamp.
const clock = (at: string) => (at.length >= 19 ? at.slice(11, 19) : at)

export default function AreaHistory({ org, area, kinds, field }: {
  org: Organizer
  area: string                  // area name for the intro copy ("naming", …)
  kinds: string[]               // journal kinds that belong to this area
  field?: ChangeItem['field']   // this area's ops inside a mixed one-click run
}) {
  const [open, setOpen] = useState(false)
  const changes = areaChanges(org.changes, kinds, field)
  if (changes.length === 0) return null
  return (
    <>
      <SectionIntro title="History"
        desc={`What the tool changed in ${area}, newest first — revert a whole run or a single op right here. The full log across all areas lives on the Misc tab.`} />
      <section className="card kept-card">
        <div className="kept-head-row">
          <button className={'kept-toggle' + (open ? ' on' : '')} aria-expanded={open}
            title={open ? 'Hide the change history' : 'Show the change history'}
            onClick={() => setOpen(!open)}>
            <span className="kept-caret">▸</span>
            {open ? 'Hide' : 'Show'} {changes.length} change{changes.length === 1 ? '' : 's'}
            <span className="kept-areas">last {clock(changes[0].at)}</span>
          </button>
        </div>
        {open && (
          <div className="kept-groups">
            <ChangeHistory changes={changes} onRevert={org.doRevertChange} field={field} />
          </div>
        )}
        <InfoButton doc="area-history" />
      </section>
    </>
  )
}
