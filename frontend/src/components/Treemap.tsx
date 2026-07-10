import React from 'react'
import type { SceneNode } from '../types'
import { catColor } from '../lib/colors'
import { humanNum } from '../lib/format'

export type FocusFn = (guid: number, name?: string) => void

export interface TreemapDatum {
  key: string | number
  value: number
  label: string
  detail: string
  color: string
  title?: string
  onClick?: () => void
}

interface TreemapItem {
  value: number
  datum: TreemapDatum
}
interface TreemapCell extends TreemapItem {
  x: number; y: number; w: number; h: number
}

// Binary-split treemap: fills a rectangle recursively, good aspect ratios.
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

// Generic weighted treemap: area = value, driven by the caller's data. In
// `dense` mode (large overlay with many tiles) labels appear on much smaller
// tiles and the font shrinks, so file names still show — truncated with an
// ellipsis — where a normal card would drop them.
export function TreemapChart({ data, height = 300, empty = 'Nothing to map.', dense = false }: {
  data: TreemapDatum[]; height?: number | string; empty?: string; dense?: boolean
}) {
  const cells = React.useMemo(() => {
    const items = data.filter((d) => d.value > 0)
      .sort((a, b) => b.value - a.value)
      .map((d) => ({ value: d.value, datum: d }))
    const out: TreemapCell[] = []
    if (items.length) treemapBinary(items, 0, 0, 100, 100, out)
    return out
  }, [data])
  if (!cells.length) return <div className="wb-empty">{empty}</div>
  const minW = dense ? 3.5 : 13
  const minH = dense ? 4.5 : 11
  return (
    <div className={dense ? 'treemap treemap--dense' : 'treemap'} style={{ height }}>
      {cells.map((c, i) => {
        const d = c.datum
        const big = c.w > minW && c.h > minH
        return (
          <button key={d.key ?? i} className="tm-cell"
            style={{ left: c.x + '%', top: c.y + '%', width: c.w + '%', height: c.h + '%', background: d.color }}
            onClick={d.onClick} title={d.title ?? `${d.label} · ${d.detail}`}>
            {big && <span className="tm-label"><span className="tm-name">{d.label}</span><span className="tm-val">{d.detail}</span></span>}
          </button>
        )
      })}
    </div>
  )
}

// Poly treemap: area = polygons, color = category, click -> frame object.
export default function Treemap({ nodes, onFocus, height = 300, count = 60, dense = false }: {
  nodes: SceneNode[]; onFocus?: FocusFn; height?: number | string; count?: number; dense?: boolean
}) {
  const data: TreemapDatum[] = React.useMemo(
    () => nodes.filter((n) => n.polygons > 0)
      .sort((a, b) => b.polygons - a.polygons).slice(0, count)
      .map((n) => ({
        key: n.guid,
        value: n.polygons,
        label: n.name,
        detail: humanNum(n.polygons),
        color: catColor(n.category),
        title: `${n.name} · ${humanNum(n.polygons)} polys`,
        onClick: () => onFocus?.(n.guid, n.name),
      })),
    [nodes, onFocus, count])
  return <TreemapChart data={data} height={height} dense={dense} empty="No geometry to map." />
}
