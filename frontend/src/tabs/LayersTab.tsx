import React, { useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import type { SceneNode } from '../types'
import { catColor, layerSwatch, multiGradientColors, type GradientStop } from '../lib/colors'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedPanel from '../components/AcceptedPanel'
import AreaHistory from '../components/AreaHistory'
import LayerTree, { orderLayers } from '../components/LayerTree'
import { rowButton } from '../lib/rowButton'
import LayerGradient from '../components/LayerGradient'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import Pager, { usePager } from '../components/Pager'
import Tip from '../components/Tip'
import ActionButton from '../components/ActionButton'
import { IconCheck } from '../components/icons'
import { plural } from '../lib/format'

// One object without a layer: ✓ opens the inline layer picker (choose an
// existing layer or type a new name — it is created on assign), ✕ accepts
// "no layer" as fine for this object (score counts it as decided).
function NoLayerRow({ n, busy, suggestion, color, onAssign, onKeep, onFocus }: {
  n: SceneNode
  busy: boolean
  suggestion?: string
  color?: [number, number, number] | null
  onAssign: (guid: number, layer: string) => void
  onKeep: (name: string) => void
  onFocus: (guid: number, name: string) => void
}) {
  const [editing, setEditing] = useState(false)
  const [value, setValue] = useState('')
  const commit = () => {
    const v = value.trim()
    if (v) { onAssign(n.guid, v); setEditing(false) }
  }
  // Suggestions arrive after the rows are mounted, so seed the input when the
  // picker opens, not at mount.
  const startEditing = () => { setValue(suggestion || ''); setEditing(true) }
  return (
    <div className="rename-row">
      <span className="cat-dot" style={{ background: catColor(n.category) }} />
      <span className="rn-old fl-clickable" title="Click to select & frame it in Cinema 4D"
        onClick={() => onFocus(n.guid, n.name)}
        {...rowButton(() => onFocus(n.guid, n.name))}>{n.name}</span>
      <span className="rn-arrow">→</span>
      {/* The layer value IS the picker: click it and it becomes the input (with
          the layer list attached). No pencil button — an extra control to reach
          a field you can just click on is one control too many. */}
      {editing
        ? (
          <input className="nl-input" autoFocus list="nl-layers" placeholder="layer name…"
            value={value} onChange={(e) => setValue(e.target.value)}
            onBlur={() => setEditing(false)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commit()
              else if (e.key === 'Escape') setEditing(false)
            }} />
        )
        : (
          <button className={'rn-new nl-pick' + (suggestion ? '' : ' empty')} disabled={busy}
            title={suggestion
              ? `Suggested from the nearest parent with a layer. Click to pick a different layer.`
              : 'Click to pick a layer — an existing one or a new name'}
            onClick={startEditing}>
            {suggestion && (
              <span className="ly-swatch nl-swatch" style={{ background: layerSwatch(color) }} />
            )}
            {suggestion || 'pick a layer'}
            <span className="nl-caret">▾</span>
          </button>
        )}
      <span className="rn-actions">
        {editing
          ? (
            <>
              <button className="rn-ok" disabled={busy || !value.trim()} onMouseDown={commit}
                title="Assign to this layer (created if missing, undoable)"><IconCheck /></button>
              <button className="rn-no" title="Cancel" onMouseDown={() => setEditing(false)}>✕</button>
            </>
          )
          : (
            <>
              {suggestion && (
                <button className="rn-ok" disabled={busy} onClick={() => onAssign(n.guid, suggestion)}
                  title={`Assign the suggested layer “${suggestion}” (undoable)`}><IconCheck /></button>
              )}
              <button className="rn-keep" disabled={busy} onClick={() => onKeep(n.name)}
                title="Accept as-is — fine without a layer (restore below)"><IconCheck /></button>
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

  // Empty layers still awaiting a decision: not yet accepted-as-is. Accepting
  // one hides its delete prompt (it stays a normal row) and lists it in the
  // Accepted panel below, reusing the shared 'layers' keep section.
  const emptyOpen = React.useMemo(
    () => (lr?.layers || []).filter((l) => l.empty && !keeps.layers.has(l.name)).length,
    [lr, keeps.layers])

  // guid -> suggested (ancestor) layer, from the pure planner.
  const suggestionByGuid = React.useMemo(() => {
    const m = new Map<number, string>()
    for (const d of layerSuggestions?.diff || []) m.set(d.guid, d.layer)
    return m
  }, [layerSuggestions])

  // layer name -> its colour in C4D, so a suggested layer shows the same swatch
  // as its row in the overview above.
  const colorByLayer = React.useMemo(() => {
    const m = new Map<string, [number, number, number] | null>()
    for (const l of lr?.layers || []) m.set(l.name, l.color)
    return m
  }, [lr])

  // Objects without any layer, keeps filtered out — the first thing to work
  // through on this tab (they drive the coverage score).
  const noLayer = React.useMemo(
    () => (report?.nodes || []).filter((n) => !n.layer && !keeps.layers.has(n.name)),
    [report, keeps.layers])

  // The gradient colors ALL layers in overview order: top of the bar = first
  // row, bottom = last. While an edit session runs, the row swatches show the
  // gradient's colors instead of the current ones (`gradPreview`).
  const [gradStops, setGradStops] = useState<GradientStop[]>([
    { t: 0, color: '#38bdf8' }, { t: 1, color: '#f472b6' },
  ])
  const [gradEditing, setGradEditing] = useState(false)
  const orderedLayers = React.useMemo(() => orderLayers(lr?.layers || []), [lr])
  const gradColors = React.useMemo(
    () => multiGradientColors(orderedLayers.length, gradStops),
    [orderedLayers.length, gradStops])
  const gradPreview = React.useMemo(
    () => new Map(orderedLayers.map((l, i) => [l.name, gradColors[i]])),
    [orderedLayers, gradColors])
  const doApplyGradient = async () => {
    try {
      const colors = orderedLayers.map((l, i) => ({ name: l.name, color: gradColors[i] }))
      const r = await call('set_layer_colors', { colors })
      // Set the outcome AFTER the follow-up analysis resolves: doAnalyze is
      // run()-wrapped and resets the (unpinned) status to "Analysis …", so a
      // message set before it would be lost.
      await org.doAnalyze()
      org.setStatus(`Colored ${plural(r.applied, 'layer')} ✓ (undoable)`)
    } catch (e: any) { org.setStatus(`Color ✗ ${String(e.message || e)}`) }
  }
  const nlPager = usePager(noLayer)
  const layerNames = (lr?.layers || []).map((l) => l.name)
  const [batchLayer, setBatchLayer] = useState('')
  const [confirmAssign, setConfirmAssign] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const mmPager = usePager(layerMismatches)
  const doDeleteEmpty = () => {
    setConfirmDelete(false)
    org.doDeleteEmptyLayers(Array.from(keeps.layers))
  }
  // Rows that DO carry an ancestor suggestion — batch-assign exactly those.
  const suggested = React.useMemo(
    () => noLayer.filter((n) => suggestionByGuid.has(n.guid)),
    [noLayer, suggestionByGuid])
  const [confirmSuggest, setConfirmSuggest] = useState(false)
  const doAssignSuggested = async () => {
    setConfirmSuggest(false)
    try {
      const r = await call('apply_layer_suggestions', { guids: suggested.map((n) => n.guid) })
      // Outcome AFTER the analysis resolves — see doApplyGradient above.
      await org.doAnalyze()
      org.setStatus(`Assigned ${plural(r.applied, 'object')} to their suggested layer ✓ (undoable)`)
    } catch (e: any) { org.setStatus(`Assign ✗ ${String(e.message || e)}`) }
  }
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

  if (!report) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  return (
    <div className="layers-tab">
      {/* ---- Side by side: layer overview (left) / no-layer worklist --- */}
      <div className="ov-cols2">
        <section className="card ly-overview">
          <div className="card-head">
            <h3>Layer overview</h3>
            {lr && (
              <span className="head-count">
                {plural(lr.total_layers, 'layer')}
                {lr.empty_layers > 0 && <span className="hc-todo"> · {lr.empty_layers} empty</span>}
              </span>
            )}
            {emptyOpen > 0 && (
              <ActionButton tone="danger" disabled={busy}
                onClick={() => setConfirmDelete(true)}
                title="Delete every empty layer that nothing references and you have not accepted (one undo step)">
                Delete {emptyOpen} empty
              </ActionButton>
            )}
          </div>
          {confirmDelete && (
            <ConfirmModal danger title="Delete empty layers"
              message={`You are about to delete ${plural(emptyOpen, 'empty layer')} that nothing references and you have not accepted as-is (one undo step). Continue?`}
              confirmLabel={`✕ Delete ${emptyOpen}`}
              onConfirm={doDeleteEmpty}
              onCancel={() => setConfirmDelete(false)} />
          )}
          {lr
            ? (() => {
              const tree = (
                <LayerTree
                  layers={lr.layers} noLayer={lr.no_layer}
                  nodes={report?.nodes || []} onFocus={org.doFocus}
                  onDeleteLayer={org.doDeleteLayer}
                  onKeepLayer={(nm) => org.keep('layers', nm)}
                  keptEmpty={keeps.layers}
                  preview={gradEditing ? gradPreview : undefined}
                />
              )
              return orderedLayers.length > 1
                ? (
                  <LayerGradient stops={gradStops} onChange={setGradStops}
                    count={orderedLayers.length} busy={busy} onApply={doApplyGradient}
                    onEditingChange={setGradEditing}>
                    {tree}
                  </LayerGradient>
                )
                : tree
            })()
            : <div className="empty-note">Run an analysis to see the layer usage.</div>}
        </section>

        <Workbench
          title="No layer" count={noLayer.length} loading={previewing}
          empty="Every object is on a layer or accepted"
          onAcceptAll={() => org.keepMany('layers', noLayer.map((n) => n.name))}
          actions={suggested.length > 0 && (
            <ActionButton tone="go" disabled={busy}
              title="Assign every object with a suggested (ancestor) layer to exactly that layer (one undo step)"
              onClick={() => setConfirmSuggest(true)}>
              Assign {suggested.length} suggested
            </ActionButton>
          )}
          busy={busy} progress={org.progress}
        >
          {confirmSuggest && (
            <ConfirmModal title="Assign suggested layers"
              message={`You are about to assign ${plural(suggested.length, 'object')} to their suggested ancestor layer (one undo step). Objects without a suggestion stay untouched. Continue?`}
              confirmLabel={`✓ Assign ${suggested.length}`}
              onConfirm={doAssignSuggested}
              onCancel={() => setConfirmSuggest(false)} />
          )}
          <datalist id="nl-layers">
            {layerNames.map((l) => <option key={l} value={l} />)}
          </datalist>
          <div className="nl-batch">
            <input className="nl-input" list="nl-layers" placeholder="layer for ALL of these…"
              value={batchLayer} onChange={(e) => setBatchLayer(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') assignAll() }} />
            <ActionButton tone="go" disabled={busy || !batchLayer.trim() || !noLayer.length}
              onClick={assignAll}
              title="Assign every listed object to this layer (created if missing, undoable)">
              Assign all
            </ActionButton>
          </div>
          {confirmAssign && (
            <ConfirmModal title="Assign all"
              message={`You are about to assign ${plural(noLayer.length, 'object')} to the layer “${batchLayer.trim()}” (created if missing, one undo step). Continue?`}
              confirmLabel={`✓ Assign ${noLayer.length}`}
              onConfirm={doAssignAll}
              onCancel={() => setConfirmAssign(false)} />
          )}
          <div className="rename-list">
            {nlPager.rows.map((n) => (
              <NoLayerRow key={n.guid} n={n} busy={busy}
                suggestion={suggestionByGuid.get(n.guid)}
                color={colorByLayer.get(suggestionByGuid.get(n.guid) || '')}
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
          empty="Every light, camera and instance is already on its layer"
          hint="Click a row to select & frame the object in Cinema 4D · the green ✓ tags it · the grey one keeps it layerless"
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
            <span className="head-count">
              {plural(layerMismatches.length, 'object')} on a different layer than their parent
            </span>
          </div>
          <p className="hint-sm">
            Informational only — a parent and its children on different layers is
            frequently deliberate. Nothing here is ever changed automatically;
            accept one to hide it from this list.
          </p>
          <div className="rename-list">
            {mmPager.rows.map((m) => (
              <div className="rename-row" key={m.guid}>
                <span className="rn-old fl-clickable" title="Click to select & frame it in Cinema 4D"
                  onClick={() => org.doFocus(m.guid, m.name)}
                  {...rowButton(() => org.doFocus(m.guid, m.name))}>{m.name}</span>
                <span className="rn-new dim" title={m.path}>
                  layer “{m.child_layer}” · parent “{m.parent}” on “{m.parent_layer}”
                </span>
                <span className="rn-actions">
                  <button className="rn-keep" disabled={busy} onClick={() => org.keep('layers', m.name)}
                    title="Accept as-is — this mix is intentional (restore below)"><IconCheck /></button>
                </span>
              </div>
            ))}
          </div>
          <Pager pager={mmPager} />
        </section>
      )}

    <AcceptedPanel org={org} />
    <AreaHistory org={org} area="layers" kinds={['layers']} />
    </div>
  )
}
