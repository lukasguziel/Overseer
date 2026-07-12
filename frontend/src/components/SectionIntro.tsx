import './SectionIntro.css'

// A section head plus the one-line description of what that section is for —
// the titled opening of an area. See frontend/STYLEGUIDE.md.
//
// `lead` is ONLY for the tab intro App.tsx renders ABOVE the tab: it adds the
// bottom gap that a flex parent would otherwise provide. Inside a tab (a
// `.stacked` container) the parent's gap already spaces it — passing `lead`
// there doubles the gap to 32px.
export default function SectionIntro({ title, desc, lead }: {
  title: string
  desc: string
  lead?: boolean
}) {
  return (
    <div className={'section-intro' + (lead ? ' lead' : '')}>
      <div className="section-head"><span>{title}</span></div>
      <p className="section-intro-desc">{desc}</p>
    </div>
  )
}
