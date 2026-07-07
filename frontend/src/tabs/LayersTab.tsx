import type { Organizer } from '../hooks/useOrganizer'
import Workbench from '../components/Workbench'

export default function LayersTab({ org }: { org: Organizer }) {
  const { layers, busy, previewing } = org
  return (
    <div className="workbench">
      <aside className="wb-side">
        <h3>Layer tagging</h3>
        <p className="hint-sm">
          Assigns objects to C4D <b>layers</b> by type — the right axis for
          “toggle/render everything of one kind”. This never moves objects, so
          your spatial null hierarchy stays exactly as is.
        </p>
        <h3>Scheme</h3>
        <ul className="grouplist">
          <li><b>Lights</b><span>all lights</span></li>
          <li><b>Cameras</b><span>all cameras</span></li>
          <li><b>Proxies</b><span>instances</span></li>
        </ul>
        {layers?.by_layer && (
          <>
            <h3>This scene</h3>
            <ul className="grouplist">
              {Object.entries(layers.by_layer).map(([k, v]) => (
                <li key={k}><b>{k}</b><span>{v}</span></li>
              ))}
            </ul>
          </>
        )}
      </aside>

      <Workbench
        title="Layer assignment preview" count={layers?.count ?? 0} loading={previewing}
        empty="No taggable objects (lights / cameras / instances) found."
        applyLabel="Apply layers" onApply={org.applyLayers} busy={busy}
        note={layers?.applied != null ? `${layers.applied} objects tagged (undoable).` : null}
      >
        <table className="diff"><tbody>
          {(layers?.diff || []).slice(0, 300).map((d, i) => (
            <tr key={i}><td>{d.name}</td><td className="arrow">→</td><td className="dim">layer: {d.layer}</td></tr>
          ))}
        </tbody></table>
      </Workbench>
    </div>
  )
}
