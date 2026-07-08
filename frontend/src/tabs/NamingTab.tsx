import type { Organizer } from '../hooks/useOrganizer'
import { CASINGS, exampleName } from '../lib/constants'
import Workbench from '../components/Workbench'

export default function NamingTab({ org }: { org: Organizer }) {
  const { casing, numberPad, naming, busy, previewing } = org
  return (
    <div className="workbench">
      <aside className="wb-side">
        <h3>Convention</h3>
        <label>Casing
          <select value={casing} onChange={(e) => org.setCasing(e.target.value)}>
            {CASINGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
        <label>Numbering <b>{numberPad === 0 ? 'no padding' : numberPad + '-digit'}</b>
          <input type="range" min="0" max="4" value={numberPad}
            onChange={(e) => org.setNumberPad(Number(e.target.value))} />
        </label>
        <div className="example">e.g. <code>{exampleName(casing, numberPad)}</code></div>
        <button className="ghost" onClick={org.doDetect} disabled={busy}>Detect from scene</button>
        <p className="hint-sm">Only casing &amp; numbering — this never changes the
          language. To translate names, use the <b>Translate</b> tab.</p>
      </aside>

      <Workbench
        title="Rename preview" count={naming?.count ?? 0} loading={previewing}
        empty="Every name already matches this convention."
        applyLabel="Apply naming" onApply={org.applyNaming} busy={busy}
        note={naming?.applied != null ? `${naming.applied} applied (undoable).` : null}
      >
        <table className="diff"><tbody>
          {(naming?.diff || []).slice(0, 300).map((d, i) => (
            <tr key={i}><td className="dim">{d.old}</td><td className="arrow">→</td><td>{d.new}</td></tr>
          ))}
        </tbody></table>
      </Workbench>
    </div>
  )
}
