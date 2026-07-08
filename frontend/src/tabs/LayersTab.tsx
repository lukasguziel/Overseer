import type { Organizer } from '../hooks/useOrganizer'
import Workbench from '../components/Workbench'
import LayerTree from '../components/LayerTree'

export default function LayersTab({ org }: { org: Organizer }) {
  const { layers, report, busy, previewing } = org
  const lr = report?.layers_report

  return (
    <div className="layers-tab">
      {/* ---- Layer overview (read-only analysis) ---------------------- */}
      <section className="card ly-overview">
        <div className="card-head">
          <h3>Layer overview</h3>
          {lr && (
            <span className="hint-sm" style={{ margin: 0 }}>
              {lr.total_layers} layer{lr.total_layers === 1 ? '' : 's'}
              {lr.empty_layers > 0 && ` · ${lr.empty_layers} empty`}
              {lr.no_layer > 0 && ` · ${lr.no_layer} on no layer`}
            </span>
          )}
        </div>
        {lr
          ? (
            <LayerTree
              layers={lr.layers} noLayer={lr.no_layer}
              nodes={report?.nodes || []} onFocus={org.doFocus}
            />
          )
          : <div className="fl-empty">Run an analysis to see the layer usage.</div>}
      </section>

      {/* ---- Layer tagging (write) ----------------------------------- */}
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
              <h3>Would tag</h3>
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
    </div>
  )
}
