import React, { useEffect, useRef, useState } from 'react'
import Pager, { usePager } from '../components/Pager'
import type { SceneNode } from '../types'
import { CAT_ORDER, SORTS } from '../lib/constants'
import { catColor } from '../lib/colors'
import { humanNum } from '../lib/format'
import Tip from '../components/Tip'
import ActionButton from '../components/ActionButton'
import InfoButton from '../components/InfoButton'
import type { FocusFn } from '../components/Treemap'

// Display-only type abbreviations — the long C4D label blows up the Type
// column; the underlying type string (search, filter keys) stays untouched.
const TYPE_ABBREV: Record<string, string> = { 'Subdivision Surface': 'SDS' }
const typeLabel = (t: string) => TYPE_ABBREV[t] || t

// Searchable, faceted, sortable asset browser with batching and
// multi-select batch actions (assign to layer / move to group).
export default function AssetsTab({ nodes, onFocus, layerNames, busy, onAssignLayer, onMoveToGroup }: {
  nodes: SceneNode[]
  onFocus?: FocusFn
  layerNames?: string[]
  busy?: boolean
  onAssignLayer?: (guids: number[], layer: string) => void
  onMoveToGroup?: (guids: number[], group: string) => void
}) {
  const [query, setQuery] = useState('')
  const [cats, setCats] = useState<Set<string>>(() => new Set())   // active category facets
  const [types, setTypes] = useState<Set<string>>(() => new Set()) // active type facets
  const [showTypes, setShowTypes] = useState(false)
  const [onlyGeo, setOnlyGeo] = useState(true)
  const [noLayer, setNoLayer] = useState(false)
  const [sortKey, setSortKey] = useState('polygons')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [sel, setSel] = useState<Set<number>>(() => new Set())
  const [layerTarget, setLayerTarget] = useState('')
  const [groupTarget, setGroupTarget] = useState('')

  const toggleCat = (c: string) => setCats((s) => {
    const n = new Set(s)
    if (n.has(c)) n.delete(c); else n.add(c)
    return n
  })
  const toggleType = (t: string) => setTypes((s) => {
    const n = new Set(s)
    if (n.has(t)) n.delete(t); else n.add(t)
    return n
  })
  const toggleSel = (guid: number) => setSel((s) => {
    const n = new Set(s)
    if (n.has(guid)) n.delete(guid); else n.add(guid)
    return n
  })
  const setSort = (k: string) => {
    if (k === sortKey) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    else { setSortKey(k); setSortDir(k === 'name' || k === 'layer' ? 'asc' : 'desc') }
  }

  // Facet counting: after search + onlyGeo + noLayer, but BEFORE the category filter.
  const q = query.trim().toLowerCase()
  const preFiltered = React.useMemo(() => nodes.filter((n) =>
    (!q || n.name.toLowerCase().includes(q) || n.type.toLowerCase().includes(q) ||
      (n.layer || '').toLowerCase().includes(q)) &&
    (!onlyGeo || n.polygons > 0) &&
    (!noLayer || !n.layer)
  ), [nodes, q, onlyGeo, noLayer])

  const catCounts = React.useMemo(() => {
    const m: Record<string, number> = {}
    preFiltered.forEach((n) => { m[n.category] = (m[n.category] || 0) + 1 })
    return m
  }, [preFiltered])

  // Rows after search + geometry + category, used both for the type facet
  // counts and as the base for the type filter.
  const catFiltered = React.useMemo(
    () => cats.size ? preFiltered.filter((n) => cats.has(n.category)) : preFiltered,
    [preFiltered, cats])

  const typeCounts = React.useMemo(() => {
    const m: Record<string, number> = {}
    catFiltered.forEach((n) => { m[n.type] = (m[n.type] || 0) + 1 })
    return Object.entries(m).sort((a, b) => b[1] - a[1])
  }, [catFiltered])

  const filtered = React.useMemo(() => {
    const rows = types.size ? catFiltered.filter((n) => types.has(n.type)) : catFiltered
    const dir = sortDir === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      if (sortKey === 'name') return dir * a.name.localeCompare(b.name)
      if (sortKey === 'layer') return dir * (a.layer || '').localeCompare(b.layer || '')
      const ka = (a as unknown as Record<string, number>)[sortKey] || 0
      const kb = (b as unknown as Record<string, number>)[sortKey] || 0
      return dir * (ka - kb)
    })
  }, [catFiltered, types, sortKey, sortDir])

  // Drop selected guids that no longer exist (scene re-analyzed after apply).
  useEffect(() => setSel((s) => {
    if (!s.size) return s
    const alive = new Set(nodes.map((n) => n.guid))
    const n = new Set([...s].filter((g) => alive.has(g)))
    return n.size === s.size ? s : n
  }), [nodes])

  // Paged view of the filtered rows; any filter/sort change jumps back to page 1.
  const pager = usePager(filtered, 25,
    [q, onlyGeo, noLayer, sortKey, sortDir, [...cats].join(), [...types].join()].join('|'))
  const shown = pager.rows
  const allShownSel = shown.length > 0 && shown.every((n) => sel.has(n.guid))
  const someShownSel = shown.some((n) => sel.has(n.guid))
  const headRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (headRef.current) headRef.current.indeterminate = someShownSel && !allShownSel
  }, [someShownSel, allShownSel])

  const toggleAllShown = () => setSel((s) => {
    const n = new Set(s)
    if (allShownSel) shown.forEach((r) => n.delete(r.guid))
    else shown.forEach((r) => n.add(r.guid))
    return n
  })

  // Suggestions for the batch targets: existing layers / existing null groups.
  const groupNames = React.useMemo(() => {
    const seen = new Set<string>()
    nodes.forEach((n) => { if (n.category === 'null') seen.add(n.name) })
    return [...seen].sort((a, b) => a.localeCompare(b))
  }, [nodes])

  const selGuids = () => [...sel]
  const doLayer = () => {
    const t = layerTarget.trim()
    if (t && sel.size && onAssignLayer) { onAssignLayer(selGuids(), t); setSel(new Set()) }
  }
  const doGroup = () => {
    const t = groupTarget.trim()
    if (t && sel.size && onMoveToGroup) { onMoveToGroup(selGuids(), t); setSel(new Set()) }
  }

  const th = (k: string, label: string, cls?: string, tip?: string) => (
    <th className={(cls || '') + (sortKey === k ? ' sorted' : '')} onClick={() => setSort(k)}>
      {tip ? <Tip text={tip}><span>{label}</span></Tip> : label}
      {sortKey === k && <span className="caret">{sortDir === 'desc' ? '▾' : '▴'}</span>}
    </th>
  )

  return (
    <div className="workbench assets">
      <aside className="wb-side">
        <h3>Filters</h3>
        <p className="hint-sm">Search and narrow the object list on the right —
          nothing here changes the scene.</p>

        <input className="search" placeholder="Search name, type or layer…" value={query}
          onChange={(e) => setQuery(e.target.value)} />

        <Tip text="Show only objects with polygons — hides nulls, splines and empty containers.">
          <label className="check">
            <input type="checkbox" checked={onlyGeo} onChange={(e) => setOnlyGeo(e.target.checked)} />
            Only geometry
          </label>
        </Tip>
        <Tip text="Show only objects that are not assigned to any layer.">
          <label className="check">
            <input type="checkbox" checked={noLayer} onChange={(e) => setNoLayer(e.target.checked)} />
            No layer
          </label>
        </Tip>

        <label>Sort
          <span className="sortsel">
            <select value={sortKey} onChange={(e) => setSort(e.target.value)}>
              {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
            <button type="button" className="sortdir"
              title={sortDir === 'desc' ? 'Descending — click for ascending' : 'Ascending — click for descending'}
              onClick={() => setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))}>
              {sortDir === 'desc' ? '▾' : '▴'}
            </button>
          </span>
        </label>

        <div className="section-head sm">
          <span>Category</span>
          {cats.size > 0 && (
            <ActionButton title="Show every category again"
              onClick={() => setCats(new Set())}>Clear</ActionButton>
          )}
        </div>
        <div className="facets">
          {CAT_ORDER.filter((c) => catCounts[c]).map((c) => (
            <button key={c} className={'facet' + (cats.has(c) ? ' on' : '')} onClick={() => toggleCat(c)}
              style={cats.has(c) ? { borderColor: catColor(c), color: catColor(c) } : undefined}>
              <span className="facet-dot" style={{ background: catColor(c) }} />
              {c}<b>{catCounts[c]}</b>
            </button>
          ))}
        </div>

        {typeCounts.length > 1 && (<>
          <div className="section-head sm">
            <span>Type</span>
            {types.size > 0 && (
              <ActionButton title="Show every type again"
                onClick={() => setTypes(new Set())}>Clear</ActionButton>
            )}
          </div>
          <ActionButton className="facet-more"
            title={showTypes ? 'Hide the type list' : 'Narrow the list down to single object types'}
            onClick={() => setShowTypes((v) => !v)}>
            {showTypes ? 'Hide types' : 'Filter by type'}
            {types.size > 0 && <b>{types.size}</b>}
          </ActionButton>
          {showTypes && (
            <div className="facets type-facets">
              {typeCounts.map(([t, n]) => (
                <button key={t} className={'facet' + (types.has(t) ? ' on' : '')} onClick={() => toggleType(t)}
                  title={t}>
                  {typeLabel(t)}<b>{n}</b>
                </button>
              ))}
            </div>
          )}
        </>)}
      </aside>

      <div className="stacked" style={{ minWidth: 0 }}>
      {sel.size > 0 && (onAssignLayer || onMoveToGroup) && (
        <div className="asset-batch">
          <b>{sel.size} selected</b>
          {onAssignLayer && (
            <span className="batch-act">
              <input list="so-layer-names" placeholder="layer name…" value={layerTarget}
                onChange={(e) => setLayerTarget(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') doLayer() }} />
              <datalist id="so-layer-names">
                {(layerNames || []).map((l) => <option key={l} value={l} />)}
              </datalist>
              <button disabled={busy || !layerTarget.trim()} onClick={doLayer}
                title="Assign the selected objects to this C4D layer (created if missing, undoable)">
                Assign layer
              </button>
            </span>
          )}
          {onMoveToGroup && (
            <span className="batch-act">
              <input list="so-group-names" placeholder="group / null name…" value={groupTarget}
                onChange={(e) => setGroupTarget(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') doGroup() }} />
              <datalist id="so-group-names">
                {groupNames.map((g) => <option key={g} value={g} />)}
              </datalist>
              <button disabled={busy || !groupTarget.trim()} onClick={doGroup}
                title="Move the selected objects under this null (created at root if missing, undoable)">
                Move to group
              </button>
            </span>
          )}
          <ActionButton onClick={() => setSel(new Set())}>Clear selection</ActionButton>
        </div>
      )}

      {/* Same panel shape as the worklists (rename preview & co): head with
          title + count at the far right, the table scrolls inside. */}
      <div className={'wb-preview' + (!filtered.length ? ' wb-empty' : '')}>
        <div className="wb-preview-head">
          <h3>Objects</h3>
          <span className="head-count">
            {filtered.length} object{filtered.length === 1 ? '' : 's'}
            {filtered.length !== nodes.length && ` · ${nodes.length} total`}
          </span>
        </div>
        <div className="wb-scroll">
        <div className="asset-table-wrap flat">
        <table className="asset-table">
          <thead><tr>
            <th className="sel"><input ref={headRef} type="checkbox" checked={allShownSel}
              onChange={toggleAllShown} title="Select all shown rows" /></th>
            <th className="l"><Tip text="Object name. Click a row to select & frame the object in Cinema 4D."><span>Name</span></Tip></th>
            <th><Tip text="Object type in Cinema 4D (e.g. polygon object, null, light)."><span>Type</span></Tip></th>
            {th('layer', 'Layer', undefined, 'Layer the object sits on. “—” means: not assigned to any layer.')}
            {th('polygons', 'Polygons', 'r', 'Polygon count of the object. Click the column header to sort by it.')}
            {th('points', 'Points', 'r', 'Point count of the object. Click the column header to sort by it.')}
            {th('children', 'Children', 'r', 'Number of direct children in the hierarchy.')}
          </tr></thead>
          <tbody>
            {shown.map((n) => (
              <tr key={n.guid}
                className={'asset-row' + (n.visible === false ? ' hidden-obj' : '') + (sel.has(n.guid) ? ' selected' : '')}
                onClick={() => onFocus?.(n.guid, n.name)}
                title={n.visible === false ? 'Hidden in the Object Manager · Select & frame' : 'Select & frame in viewport'}>
                <td className="sel" onClick={(e) => e.stopPropagation()}>
                  <input type="checkbox" checked={sel.has(n.guid)} onChange={() => toggleSel(n.guid)} />
                </td>
                <td className="l">
                  <span className="cat-dot" style={{ background: catColor(n.category) }} />
                  {n.name}
                  {n.visible === false && <span className="hidden-tag">hidden</span>}
                </td>
                <td className="dim">{typeLabel(n.type)}</td>
                <td className="dim">{n.layer || <span className="no-layer">—</span>}</td>
                <td className="r">{humanNum(n.polygons)}</td>
                <td className="r">{humanNum(n.points)}</td>
                <td className="r dim">{n.children || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filtered.length && <div className="empty-note mid">No objects match.</div>}
        </div>

        <Pager pager={pager} />
        <InfoButton doc="assets" />
        </div>
      </div>
      </div>
    </div>
  )
}
