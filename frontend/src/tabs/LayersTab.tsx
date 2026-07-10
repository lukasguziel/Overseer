import React, { useState } from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import type { SceneNode } from '../types'
import { catColor } from '../lib/colors'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedSection from '../components/AcceptedSection'
import LayerTree from '../components/LayerTree'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import Pager, { usePager } from '../components/Pager'
import Tip from '../components/Tip'
import GuideFlow, { type GuideCard } from '../components/GuideFlow'
import { buildLayerGuideSteps } from '../lib/layerGuide'

// One object without a layer: ✓ opens the inline layer picker (choose an
// existing layer or type a new name — it is created on assign), ✕ accepts
// "no layer" as fine for this object (score counts it as decided).
function NoLayerRow({ n, busy, suggestion, onAssign, onKeep, onFocus }: {
  n: SceneNode
  busy: boolean
  suggestion?: string
  onAssign: (guid: number, layer: string) => void
  onKeep: (name: string) => void
  onFocus: (guid: number, name: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState(suggestion || '')
  const commit = () => {
    const v = value.trim()
    if (v) { onAssign(n.guid, v); setEditing(false) }
  }
  return (
    <div className="rename-row">
      <span className="cat-dot" style={{ background: catColor(n.category) }} />
      <span className="rn-old fl-clickable" title="Click to select & frame it in Cinema 4D"
        onClick={() => onFocus(n.guid, n.name)}>{n.name}</span>
      <span className="rn-arrow">→</span>
      {editing
        ? (
          <input className="nl-input" autoFocus list="nl-layers" placeholder="layer name…"
            value={value} onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commit()
              else if (e.key === 'Escape') setEditing(false)
            }} />
        )
        : suggestion
          ? <span className="rn-new" title="Inherited from the nearest parent that has a layer">layer: {suggestion}</span>
          : <span className="rn-new dim">no layer</span>}
      <span className="rn-actions">
        {editing
          ? (
            <>
              <button className="rn-ok" disabled={busy || !value.trim()} onClick={commit}
                title="Assign to this layer (created if missing, undoable)">✓</button>
              <button className="rn-no" title="Cancel" onClick={() => setEditing(false)}>✕</button>
            </>
          )
          : suggestion
            ? (
              <>
                <button className="rn-ok" disabled={busy} onClick={() => onAssign(n.guid, suggestion)}
                  title={`Assign the suggested layer “${suggestion}” (undoable)`}>✓</button>
                <button className="rn-ok" disabled={busy} onClick={() => setEditing(true)}
                  title="Pick a different layer instead">✎</button>
                <button className="rn-keep" disabled={busy} onClick={() => onKeep(n.name)}
                  title="Accept as-is — fine without a layer (restore below)">=</button>
              </>
            )
            : (
              <>
                <button className="rn-ok" disabled={busy} onClick={() => setEditing(true)}
                  title="Assign a layer — pick an existing one or type a new name">✓</button>
                <button className="rn-keep" disabled={busy} onClick={() => onKeep(n.name)}
                  title="Accept as-is — fine without a layer (restore below)">=</button>
              </>
            )}
      </span>
    </div>
  )
}

// Scheme-based layer tagging (Lights/Cameras/Proxies preview) is parked —
// the tab focuses on the no-layer worklist. Kept behind this flag.
const SHOW_TAGGING = false

export default function LayersTab({ org }: { org: Organizer }) {
  const { layers, keeps, report, busy, previewing, layerSuggestions, layerMismatches } = org
  const lr = report?.layers_report
  const pager = usePager(layers?.diff || [])

  // guid -> suggested (ancestor) layer, from the pure planner.
  const suggestionByGuid = React.useMemo(() => {
    const m = new Map<number, string>()
    for (const d of layerSuggestions?.diff || []) m.set(d.guid, d.layer)
    return m
  }, [layerSuggestions])

  // Objects without any layer, keeps filtered out — the first thing to work
  // through on this tab (they drive the coverage score).
  const noLayer = React.useMemo(
    () => (report?.nodes || []).filter((n) => !n.layer && !keeps.layers.has(n.name)),
    [report, keeps.layers])
  const nlPager = usePager(noLayer)
  const layerNames = (lr?.layers || []).map((l) => l.name)
  const [batchLayer, setBatchLayer] = useState('')
  const [confirmAssign, setConfirmAssign] = useState(false)
  const assignAll = () => {
    const v = batchLayer.trim()
    if (!v || !noLayer.length) return
    setConfirmAssign(true)
  }
  const doAssignAll = () => {
    setConfirmAssign(false)
    org.doAssignLayer(noLayer.map((n) => n.guid), batchLayer.trim())
    setBatchLayer('')
  }

  // Guided mode: freeze the current findings into a card list so the walk
  // does not reshuffle as accepted/assigned rows drop out of the live report.
  const [guided, setGuided] = useState(false)
  const [guideCards, setGuideCards] = useState<GuideCard[]>([])
  const startGuide = () => {
    const steps = buildLayerGuideSteps(noLayer, suggestionByGuid, layerMismatches)
    setGuideCards(steps.map((s): GuideCard => {
      if (s.kind === 'suggestion') {
        return {
          key: 'sug-' + s.guid,
          headline: <>Object “{s.name}” has no layer</>,
          body: <>The nearest parent container is on the layer “{s.layer}”.
            Should this object get the same layer?</>,
          yesLabel: `Yes, assign layer “${s.layer}”`,
          onYes: () => org.doAssignLayer([s.guid], s.layer!),
        }
      }
      if (s.kind === 'mismatch') {
        return {
          key: 'mix-' + s.guid,
          headline: <>Mixed-layer hierarchy</>,
          body: <>“{s.name}” is on layer “{s.childLayer}”, its parent
            “{s.parent}” on “{s.parentLayer}”. This is often intentional.
            Keep it as-is and remove it from the list?</>,
          yesLabel: 'Yes, keep as-is',
          onYes: () => org.keep('layers', s.name),
        }
      }
      return {
        key: 'nl-' + s.guid,
        headline: <>Object “{s.name}” has no layer</>,
        body: <>There is no layer suggestion for this object.
          Is it fine without a layer?</>,
        yesLabel: 'Yes, fine without a layer',
        onYes: () => org.keep('layers', s.name),
      }
    }))
    setGuided(true)
  }

  if (!report) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  const guideCount = noLayer.length + layerMismatches.length

  return (
    <div className="layers-tab">
      <div className="guide-toggle-bar">
        <Tip text="Guided mode: walks through every layer finding one by one — suggestions, objects without a layer and mixed hierarchies. Each card offers only Yes / No / Skip; “Yes” runs exactly the matching action.">
          <button className="sm" disabled={busy || guided || !guideCount}
            onClick={startGuide}>
            ▶ Guided mode{guideCount ? ` (${guideCount})` : ''}
          </button>
        </Tip>
      </div>

      {guided && (
        <GuideFlow cards={guideCards} onExit={() => setGuided(false)}
          labels={{
            no: 'No', skip: 'Skip', exit: 'Done',
            done: 'All layer findings worked through 🎉',
            empty: 'Nothing to decide right now.',
          }} />
      )}

      {/* ---- Side by side: layer overview (left) / no-layer worklist --- */}
      <div className="ov-cols2">
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
            {lr && lr.empty_layers > 0 && (
              <button className="sm" disabled={busy} onClick={org.doDeleteEmptyLayers}
                title="Delete every layer that nothing (objects, materials or tags) references (one undo step)">
                ✕ Delete {lr.empty_layers} empty
              </button>
            )}
          </div>
          {lr
            ? (
              <LayerTree
                layers={lr.layers} noLayer={lr.no_layer}
                nodes={report?.nodes || []} onFocus={org.doFocus}
                onDeleteLayer={org.doDeleteLayer}
              />
            )
            : <div className="fl-empty">Run an analysis to see the layer usage.</div>}
        </section>

        <Workbench
          title="No layer" count={noLayer.length} loading={previewing}
          empty="Every object is on a layer or accepted 🎉"
          onAcceptAll={() => org.keepMany('layers', noLayer.map((n) => n.name))}
          busy={busy} progress={org.progress}
        >
          <datalist id="nl-layers">
            {layerNames.map((l) => <option key={l} value={l} />)}
          </datalist>
          <div className="nl-batch">
            <input className="nl-input" list="nl-layers" placeholder="layer for ALL of these…"
              value={batchLayer} onChange={(e) => setBatchLayer(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') assignAll() }} />
            <button className="sm" disabled={busy || !batchLayer.trim() || !noLayer.length}
              onClick={assignAll}
              title="Assign every listed object to this layer (created if missing, undoable)">
              ✓ Assign all
            </button>
          </div>
          {confirmAssign && (
            <ConfirmModal title="Assign all"
              message={`You are about to assign ${noLayer.length} object${noLayer.length === 1 ? '' : 's'} to the layer “${batchLayer.trim()}” (created if missing, one undo step). Continue?`}
              confirmLabel={`✓ Assign ${noLayer.length}`}
              onConfirm={doAssignAll}
              onCancel={() => setConfirmAssign(false)} />
          )}
          <div className="rename-list">
            {nlPager.rows.map((n) => (
              <NoLayerRow key={n.guid} n={n} busy={busy}
                suggestion={suggestionByGuid.get(n.guid)}
                onAssign={(guid, layer) => org.doAssignLayer([guid], layer)}
                onKeep={(nm) => org.keep('layers', nm)}
                onFocus={(guid, nm) => org.doFocus(guid, nm)} />
            ))}
          </div>
          <Pager pager={nlPager} />
        </Workbench>
      </div>

      {/* ---- Layer tagging (scheme-based auto-assignment) --------------
          Parked for now: the tab's job is simply "give layerless objects a
          layer" via the worklist above. Flip SHOW_TAGGING to bring the
          scheme preview back. */}
      {SHOW_TAGGING && (
      <div className="workbench">
        <aside className={'wb-side' + (previewing ? ' side-loading' : '')}>
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
          hint="Click a row to select & frame the object in Cinema 4D · ✓ tags it · = keeps it layerless"
          applyLabel="Apply all" onApply={org.applyLayers}
          onAcceptAll={() => org.keepAll('layers')} busy={busy}
          progress={org.progress}
          note={layers?.applied != null ? `${layers.applied} applied (undoable).` : null}
        >
          <div className="rename-list">
            {pager.rows.map((d) => (
              <SuggestionRow key={d.guid} busy={busy}
                applyTitle="Apply — tag now (undoable)"
                onApply={() => org.applyLayerOne(d.guid, d.name)}
                onAcceptAsIs={() => org.keep('layers', d.name)}
                onFocus={() => org.doFocus(d.guid, d.name)}
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
      )}

      {layerMismatches.length > 0 && (
        <section className="card ly-mismatches">
          <div className="card-head">
            <Tip text="Object sits on a different layer than its parent. Informational only — often intentional; nothing here is ever changed automatically.">
              <h3>Mixed-layer hierarchies</h3>
            </Tip>
            <span className="hint-sm" style={{ margin: 0 }}>
              {layerMismatches.length} object{layerMismatches.length === 1 ? '' : 's'} on a different layer than their parent
            </span>
          </div>
          <p className="hint-sm">
            Informational only — a parent and its children on different layers is
            frequently deliberate. Nothing here is ever changed automatically;
            accept one to hide it from this list.
          </p>
          <div className="rename-list">
            {layerMismatches.map((m) => (
              <div className="rename-row" key={m.guid}>
                <span className="rn-old fl-clickable" title="Click to select & frame it in Cinema 4D"
                  onClick={() => org.doFocus(m.guid, m.name)}>{m.name}</span>
                <span className="rn-new dim" title={m.path}>
                  layer “{m.child_layer}” · parent “{m.parent}” on “{m.parent_layer}”
                </span>
                <span className="rn-actions">
                  <button className="rn-keep" disabled={busy} onClick={() => org.keep('layers', m.name)}
                    title="Accept as-is — this mix is intentional (restore below)">=</button>
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <AcceptedSection items={Array.from(keeps.layers)}
        onRestore={(nm) => org.unkeep('layers', nm)} />
    </div>
  )
}
