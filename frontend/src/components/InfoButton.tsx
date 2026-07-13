import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { SECTION_DOCS, type DocFeature, type SectionDoc } from '../lib/sectionDocs'
import './InfoButton.css'

// The little "i" in an area's SectionIntro, between the title and the rule
// line: opens that area's guide (lib/sectionDocs.ts) in a modal. Deliberately
// inconspicuous — it is a reference, not an action, and must never compete
// with the area's real controls.
//
// Rendered by SectionIntro via its `doc` prop — don't place it inside boxes.
// Unknown doc keys render nothing, so a typo can never break a tab.

function Features({ features }: { features: DocFeature[] }) {
  return (
    <>
      {features.map((f) => (
        <div className="doc-feature" key={f.name}>
          <span className="doc-feature-name">{f.name}</span>
          <span className="doc-feature-desc">{f.desc}</span>
        </div>
      ))}
    </>
  )
}

function InfoModal({ d, onClose }: { d: SectionDoc; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="confirm-overlay" onClick={onClose}>
      <div className="doc-box" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <div className="doc-head">
          <div>
            <div className="doc-kicker">Section guide</div>
            <h3 className="doc-title">{d.title}</h3>
          </div>
          <button className="doc-close" onClick={onClose} title="Close (Esc)">✕</button>
        </div>
        <p className="doc-tagline">{d.tagline}</p>
        <div className="doc-list">
          {d.features && <Features features={d.features} />}
          {d.groups?.map((g) => (
            <div className="doc-group" key={g.head}>
              <div className="doc-group-head">{g.head}</div>
              <Features features={g.features} />
            </div>
          ))}
        </div>
        {d.tip && <p className="doc-tip"><b>Tip</b> {d.tip}</p>}
      </div>
    </div>
  )
}

export default function InfoButton({ doc }: { doc: string }) {
  const [open, setOpen] = useState(false)
  const d = SECTION_DOCS[doc]
  if (!d) return null
  return (
    <>
      <button className="info-dot" aria-label={`What “${d.title}” can do`}
        title={`What “${d.title}” can do`}
        onClick={(e) => { e.stopPropagation(); setOpen(true) }}>i</button>
      {/* Portal to <body>: the intros sit inside transform-animated tab
          containers — a transformed ancestor becomes the containing block for
          position:fixed, so rendered in place the overlay would be clipped
          (e.g. inside the Translate preview). Same escape hatch as the
          Overview zoom overlay. */}
      {open && createPortal(
        <InfoModal d={d} onClose={() => setOpen(false)} />, document.body)}
    </>
  )
}
