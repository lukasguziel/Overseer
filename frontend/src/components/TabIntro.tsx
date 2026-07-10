// Per-tab intro band: a headline plus a one-line description, same rule/line
// look as the Naming tab's section bands, so every area explains itself.
export default function TabIntro({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="sec-band tab-intro">
      <div className="misc-sec"><span>{title}</span><hr /></div>
      <p className="sec-desc">{desc}</p>
    </div>
  )
}
