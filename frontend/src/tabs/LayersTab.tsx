import type { Organizer } from '../hooks/useOrganizer'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedSection from '../components/AcceptedSection'
import LayerTree from '../components/LayerTree'
import Pager, { usePager } from '../components/Pager'

export default function LayersTab({ org }: { org: Organizer }) {
  const { layers, keeps, report, busy, previewing } = org
  const lr = report?.layers_report
  const pager = usePager(layers?.diff || [])

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
          empty="Every light, camera and instance is already on its layer 🎉"
          applyLabel="Process all" onApply={org.applyLayers} busy={busy}
          progress={org.progress}
          note={layers?.applied != null ? `${layers.applied} applied (undoable).` : null}
        >
          <div className="rename-list">
            {pager.rows.map((d) => (
              <SuggestionRow key={d.guid} busy={busy}
                applyTitle="Apply — tag now (undoable)"
                onApply={() => org.applyLayerOne(d.guid, d.name)}
                onAcceptAsIs={() => org.keep('layers', d.name)}
              >
                <span className="rn-old" title={d.name}>{d.name}</span>
                <span className="rn-arrow">→</span>
                <span className="rn-new dim">layer: {d.layer}</span>
              </SuggestionRow>
            ))}
          </div>
          <Pager pager={pager} />
        </Workbench>
      </div>

      <AcceptedSection items={Array.from(keeps.layers)}
        onRestore={(nm) => org.unkeep('layers', nm)} />
    </div>
  )
}
