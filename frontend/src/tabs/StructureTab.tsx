import type { Organizer } from '../hooks/useOrganizer'
import Workbench from '../components/Workbench'

export default function StructureTab({ org }: { org: Organizer }) {
  const { tidy, safe, rules, structure, busy, previewing } = org
  return (
    <div className="workbench">
      <aside className="wb-side">
        <h3>Options</h3>
        <label className="check">
          <input type="checkbox" checked={tidy} onChange={(e) => org.setTidy(e.target.checked)} />
          Tidy mode
        </label>
        <p className="hint-sm">
          Only collects <b>loose</b> objects into their group. Objects already
          inside a (even nested) group are left untouched — your hierarchy is
          never flattened. Turn off for aggressive flat regrouping.
        </p>
        <label className="check">
          <input type="checkbox" checked={safe} onChange={(e) => org.setSafe(e.target.checked)} />
          Safety filter
        </label>
        <p className="hint-sm">Protects generator children (Cloner, Boole, Sweep …) from being moved.</p>
        {!tidy && <p className="wb-note" style={{ padding: '8px 0' }}>⚠ Aggressive mode can pull objects out of existing groups and flatten spatial nesting.</p>}

        <h3>Target groups</h3>
        {rules?.groups?.length
          ? <ul className="grouplist">
              {rules.groups.map((g) => <li key={g.name}><b>{g.name}</b><span>{g.priority}</span></li>)}
            </ul>
          : <p className="hint-sm">No rules yet.</p>}
        <button className="ghost" onClick={() => org.setTab('rules')}>Edit rules →</button>
      </aside>

      <Workbench
        title="Regroup preview" count={structure?.count ?? 0} loading={previewing}
        empty="Everything is already in the right place."
        applyLabel="Apply structure" onApply={org.applyStructure} busy={busy}
        note={
          structure?.applied != null ? `${structure.applied} moved (undoable).`
            : (structure?.skipped ?? 0) > 0 ? `${structure?.skipped} protected by the safety filter.` : null
        }
      >
        <table className="diff"><tbody>
          {(structure?.diff || []).slice(0, 300).map((d, i) => (
            <tr key={i}>
              <td>{d.name}</td><td className="dim">{d.from || '(root)'}</td>
              <td className="arrow">→</td><td>{d.to}</td>
            </tr>
          ))}
        </tbody></table>
      </Workbench>
    </div>
  )
}
