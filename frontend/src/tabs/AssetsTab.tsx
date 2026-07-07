import React, { useEffect, useState } from 'react'
import type { SceneNode } from '../types'
import { CAT_ORDER, SORTS } from '../lib/constants'
import { catColor } from '../lib/colors'
import { humanNum } from '../lib/format'
import type { FocusFn } from '../components/Treemap'

// Searchable, faceted, sortable asset browser with batching.
export default function AssetsTab({ nodes, onFocus }: {
  nodes: SceneNode[]
  onFocus?: FocusFn
}) {
  const [query, setQuery] = useState('')
  const [cats, setCats] = useState<Set<string>>(() => new Set())   // active category facets
  const [onlyGeo, setOnlyGeo] = useState(true)
  const [sortKey, setSortKey] = useState('polygons')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [limit, setLimit] = useState(40)

  const toggleCat = (c: string) => setCats((s) => {
    const n = new Set(s)
    if (n.has(c)) n.delete(c); else n.add(c)
    return n
  })
  const setSort = (k: string) => {
    if (k === sortKey) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    else { setSortKey(k); setSortDir(k === 'name' ? 'asc' : 'desc') }
  }

  // Facet counting: after search + onlyGeo, but BEFORE the category filter.
  const q = query.trim().toLowerCase()
  const preFiltered = React.useMemo(() => nodes.filter((n) =>
    (!q || n.name.toLowerCase().includes(q) || n.type.toLowerCase().includes(q)) &&
    (!onlyGeo || n.polygons > 0)
  ), [nodes, q, onlyGeo])

  const catCounts = React.useMemo(() => {
    const m: Record<string, number> = {}
    preFiltered.forEach((n) => { m[n.category] = (m[n.category] || 0) + 1 })
    return m
  }, [preFiltered])

  const filtered = React.useMemo(() => {
    const rows = cats.size ? preFiltered.filter((n) => cats.has(n.category)) : preFiltered
    const dir = sortDir === 'asc' ? 1 : -1
    return [...rows].sort((a, b) => {
      if (sortKey === 'name') return dir * a.name.localeCompare(b.name)
      const ka = (a as unknown as Record<string, number>)[sortKey] || 0
      const kb = (b as unknown as Record<string, number>)[sortKey] || 0
      return dir * (ka - kb)
    })
  }, [preFiltered, cats, sortKey, sortDir])

  // Reset the batch when the filter/sort changes.
  useEffect(() => { setLimit(40) }, [q, onlyGeo, sortKey, sortDir, cats])

  const shown = filtered.slice(0, limit)
  const th = (k: string, label: string, cls?: string) => (
    <th className={(cls || '') + (sortKey === k ? ' sorted' : '')} onClick={() => setSort(k)}>
      {label}{sortKey === k && <span className="caret">{sortDir === 'desc' ? '▾' : '▴'}</span>}
    </th>
  )

  return (
    <div className="assets">
      <div className="asset-controls">
        <input className="search" placeholder="Search name or type…" value={query}
          onChange={(e) => setQuery(e.target.value)} />
        <label className="check inline">
          <input type="checkbox" checked={onlyGeo} onChange={(e) => setOnlyGeo(e.target.checked)} />
          only geometry
        </label>
        <label className="sortsel">Sort
          <select value={sortKey} onChange={(e) => setSort(e.target.value)}>
            {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
      </div>

      <div className="facets">
        {CAT_ORDER.filter((c) => catCounts[c]).map((c) => (
          <button key={c} className={'facet' + (cats.has(c) ? ' on' : '')} onClick={() => toggleCat(c)}
            style={cats.has(c) ? { borderColor: catColor(c), color: catColor(c) } : undefined}>
            <span className="facet-dot" style={{ background: catColor(c) }} />
            {c}<b>{catCounts[c]}</b>
          </button>
        ))}
        {cats.size > 0 && <button className="facet clear" onClick={() => setCats(new Set())}>clear</button>}
      </div>

      <div className="asset-count">
        showing {Math.min(limit, filtered.length)} of {filtered.length}
        {filtered.length !== nodes.length && <span className="dim"> · {nodes.length} total</span>}
      </div>

      <div className="asset-table-wrap">
        <table className="asset-table">
          <thead><tr>
            <th className="l">Name</th>
            <th>Type</th>
            {th('polygons', 'Polygons', 'r')}
            {th('points', 'Points', 'r')}
            {th('children', 'Children', 'r')}
          </tr></thead>
          <tbody>
            {shown.map((n) => (
              <tr key={n.guid} className="asset-row" onClick={() => onFocus?.(n.guid, n.name)}
                title="Select & frame in viewport">
                <td className="l">
                  <span className="cat-dot" style={{ background: catColor(n.category) }} />
                  {n.name}
                </td>
                <td className="dim">{n.type}</td>
                <td className="r">{humanNum(n.polygons)}</td>
                <td className="r">{humanNum(n.points)}</td>
                <td className="r dim">{n.children || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filtered.length && <div className="wb-empty">No objects match.</div>}
      </div>

      {limit < filtered.length && (
        <div className="asset-more">
          <button className="ghost" onClick={() => setLimit((l) => l + 60)}>
            Load more ({filtered.length - limit} left)
          </button>
        </div>
      )}
    </div>
  )
}
