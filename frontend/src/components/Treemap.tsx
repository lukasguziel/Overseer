import React from 'react'
import type { SceneNode } from '../types'
import { catColor } from '../lib/colors'
import { humanNum } from '../lib/format'

export type FocusFn = (guid: number, name?: string) => void

interface TreemapItem {
  value: number
  node: SceneNode
}
interface TreemapCell extends TreemapItem {
  x: number; y: number; w: number; h: number
}

// Binary-Split-Treemap: fuellt ein Rechteck rekursiv, gute Seitenverhaeltnisse.
function treemapBinary(items: TreemapItem[], x: number, y: number, w: number, h: number, out: TreemapCell[]): void {
  if (!items.length) return
  if (items.length === 1) { out.push({ ...items[0], x, y, w, h }); return }
  const total = items.reduce((s, d) => s + d.value, 0)
  let acc = 0
  let i = 0
  while (i < items.length - 1 && acc + items[i].value < total / 2) { acc += items[i].value; i++ }
  const a = items.slice(0, i + 1)
  const b = items.slice(i + 1)
  const frac = a.reduce((s, d) => s + d.value, 0) / total
  if (w >= h) {
    treemapBinary(a, x, y, w * frac, h, out)
    treemapBinary(b, x + w * frac, y, w * (1 - frac), h, out)
  } else {
    treemapBinary(a, x, y, w, h * frac, out)
    treemapBinary(b, x, y + h * frac, w, h * (1 - frac), out)
  }
}

// Poly-Treemap: Flaeche = Polygone, Farbe = Kategorie, Klick -> framen.
export default function Treemap({ nodes, onFocus, height = 300 }: {
  nodes: SceneNode[]; onFocus?: FocusFn; height?: number
}) {
  const cells = React.useMemo(() => {
    const items = nodes.filter((n) => n.polygons > 0)
      .sort((a, b) => b.polygons - a.polygons).slice(0, 60)
      .map((n) => ({ value: n.polygons, node: n }))
    const out: TreemapCell[] = []
    if (items.length) treemapBinary(items, 0, 0, 100, 100, out)
    return out
  }, [nodes])
  if (!cells.length) return <div className="wb-empty">No geometry to map.</div>
  return (
    <div className="treemap" style={{ height }}>
      {cells.map((c, i) => {
        const n = c.node
        const big = c.w > 13 && c.h > 11
        return (
          <button key={n.guid ?? i} className="tm-cell"
            style={{ left: c.x + '%', top: c.y + '%', width: c.w + '%', height: c.h + '%', background: catColor(n.category) }}
            onClick={() => onFocus?.(n.guid, n.name)} title={`${n.name} · ${humanNum(n.polygons)} polys`}>
            {big && <span className="tm-label"><span className="tm-name">{n.name}</span><span className="tm-val">{humanNum(n.polygons)}</span></span>}
          </button>
        )
      })}
    </div>
  )
}
