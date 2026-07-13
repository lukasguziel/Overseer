import { useEffect, useState } from 'react'
import { SECTION_DOCS, type SectionDoc } from '../lib/sectionDocs'
import './InfoButton.css'

// The little "i" in the bottom-left corner of every section: opens that
// section's guide (lib/sectionDocs.ts) in a modal. Deliberately inconspicuous —
// it must never compete with the section's real actions, only be findable
// when the artist wonders what the area can do.
//
// Drop it as the LAST child of a `section.card` / `.wb-preview` (both are
// position:relative); it positions itself. Unknown doc keys render nothing,
// so a typo can never break a tab.

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
          {d.features.map((f) => (
            <div className="doc-feature" key={f.name}>
              <span className="doc-feature-name">{f.name}</span>
              <span className="doc-feature-desc">{f.desc}</span>
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
      {open && <InfoModal d={d} onClose={() => setOpen(false)} />}
    </>
  )
}
