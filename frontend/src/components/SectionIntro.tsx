import type { ReactNode } from 'react'
import InfoButton from './InfoButton'
import './SectionIntro.css'

// A section head plus the one-line description of what that section is for —
// the titled opening of an area. See frontend/STYLEGUIDE.md.
//
// `lead` is ONLY for the tab intro App.tsx renders ABOVE the tab: it adds the
// bottom gap that a flex parent would otherwise provide. Inside a tab (a
// `.stacked` container) the parent's gap already spaces it — passing `lead`
// there doubles the gap to 32px.
//
// `doc` renders the section-guide "i" between the title and the rule line —
// the ONE place area docs are reachable from (never inside the boxes).
//
// `aside` docks a widget at the right edge, vertically centered over both
// lines (the area score ring lives here); the head's rule stops short of it.
export default function SectionIntro({ title, desc, lead, doc, aside }: {
  title: string
  desc: string
  lead?: boolean
  doc?: string
  aside?: ReactNode
}) {
  const intro = (
    <div className={'section-intro' + (lead && !aside ? ' lead' : '')}>
      <div className="section-head">
        <span>{title}</span>
        {doc && <InfoButton doc={doc} />}
      </div>
      <p className="section-intro-desc">{desc}</p>
    </div>
  )
  if (!aside) return intro
  return (
    <div className={'section-intro-row' + (lead ? ' lead' : '')}>
      {intro}
      {aside}
    </div>
  )
}
