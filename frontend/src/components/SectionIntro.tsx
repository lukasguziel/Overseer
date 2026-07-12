import './SectionIntro.css'

// A section head plus the one-line description of what that section is for —
// the titled opening of an area. `lead` marks the variant that opens a whole
// tab (it carries its own bottom gap); inside a tab the flex gap spaces it.
// See frontend/STYLEGUIDE.md.
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
