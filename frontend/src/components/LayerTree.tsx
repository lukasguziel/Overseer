import { useState } from 'react'
import { catColor } from '../lib/colors'
import { humanNum } from '../lib/format'
import { IconTrash } from './icons'
import type { FocusFn } from './Treemap'
import type { LayerInfo, SceneNode } from '../types'

// The "no layer" bucket is modelled as a synthetic layer so the tree renders
// it with the same row/expand machinery as the real ones.
const NO_LAYER = '\0no-layer'

function swatch(color: LayerInfo['color']): string {
  if (!color) return 'var(--dim2)'
  const [r, g, b] = color
  return `rgb(${Math.round(r * 255)}, ${Math.round(g * 255)}, ${Math.round(b * 255)})`
}

// Small state badge — only rendered for the noteworthy (non-default) flags,
// because those are the ones that bite a 3D artist at render time.
function Flags({ l }: { l: LayerInfo }) {
  return (
    <>
      {!l.render && <span className="ly-flag warn" title="Render flag OFF — will NOT appear in the final render">no render</span>}
      {!l.view && <span className="ly-flag dim" title="Hidden in the editor viewport">hidden</span>}
      {l.locked && <span className="ly-flag dim" title="Layer is locked">locked</span>}
      {l.solo && <span className="ly-flag" title="Solo — only this layer is shown">solo</span>}
      {l.empty && <span className="ly-flag dim" title="Layer exists but nothing (objects, materials or tags) references it">empty</span>}
    </>
  )
}

export default function LayerTree({ layers, noLayer, nodes, onFocus, onDeleteLayer, onKeepLayer, keptEmpty }: {
  layers: LayerInfo[]
  noLayer: number
  nodes: SceneNode[]
  onFocus?: FocusFn
  onDeleteLayer?: (name: string) => void
  onKeepLayer?: (name: string) => void
  keptEmpty?: Set<string>
}) {
  const [open, setOpen] = useState<Set<string>>(() => new Set())
  const toggle = (name: string) =>
    setOpen((s) => {
      const n = new Set(s)
      n.has(name) ? n.delete(name) : n.add(name)
      return n
    })

  // Objects grouped by their assigned layer name (null -> NO_LAYER bucket).
  const byLayer = new Map<string, SceneNode[]>()
  for (const n of nodes) {
    const key = n.layer || NO_LAYER
    const arr = byLayer.get(key)
    if (arr) arr.push(n)
    else byLayer.set(key, [n])
  }

  // Non-empty layers first, then empty layers, then the synthetic "No layer"
  // bucket last — so the things that need attention sit together at the bottom.
  const rows: LayerInfo[] = [
    ...layers.filter((l) => !l.empty),
    ...layers.filter((l) => l.empty),
  ]
  if (noLayer > 0) {
    rows.push({
      name: NO_LAYER, color: null, solo: false, view: true, render: true,
      locked: false, objects: noLayer, materials: 0, tags: 0, polys: 0,
      empty: false,
    })
  }

  if (!rows.length) return <div className="fl-empty">This scene uses no layers.</div>

  return (
    <div className="layertree">
      {rows.map((l) => {
        const isNo = l.name === NO_LAYER
        const objs = byLayer.get(l.name) || []
        const expandable = objs.length > 0
        const isOpen = open.has(l.name)
        const emptyActions = !isNo && l.empty && !keptEmpty?.has(l.name) && (onDeleteLayer || onKeepLayer)
        return (
          <div key={l.name} className={`ly-group${isNo ? ' orphan' : ''}${!isNo && l.empty ? ' ly-empty' : ''}`}>
            <div className="ly-row">
              <button className="ly-head" disabled={!expandable}
                onClick={() => expandable && toggle(l.name)}
                title={expandable ? 'Show objects on this layer' : undefined}>
                <span className={`ly-caret${isOpen ? ' open' : ''}`}>
                  {expandable ? '▸' : ''}
                </span>
                <span className="ly-swatch" style={{ background: isNo ? 'transparent' : swatch(l.color) }} />
                <span className="ly-name">{isNo ? 'No layer' : l.name}</span>
                <Flags l={l} />
                <span className="ly-count">{l.objects} obj</span>
                {(l.objects_all ?? l.objects) > l.objects && (
                  <span className="ly-flag dim"
                    title="Objects hidden in the Object Manager also sit on this layer — that is why it does not count as empty under “Visible only”">
                    +{(l.objects_all ?? 0) - l.objects} hidden
                  </span>
                )}
                {l.materials > 0 && <span className="ly-count">{l.materials} mat</span>}
                {l.tags > 0 && <span className="ly-count">{l.tags} tag</span>}
                {l.polys > 0 && <span className="ly-polys">{humanNum(l.polys)} polys</span>}
              </button>
              {emptyActions && (
                <span className="rn-actions ly-actions">
                  {onDeleteLayer && (
                    <button className="rn-ok" title="Delete this empty layer (undoable)"
                      onClick={() => onDeleteLayer(l.name)}><IconTrash /></button>
                  )}
                  {onKeepLayer && (
                    <button className="rn-keep" title="Accept as-is — keep this empty layer (restore below)"
                      onClick={() => onKeepLayer(l.name)}>=</button>
                  )}
                </span>
              )}
            </div>
            {isOpen && (
              <div className="ly-objs">
                {objs.slice(0, 300).map((n, i) => (
                  <button key={n.guid ?? i} className="fl-row"
                    onClick={() => onFocus?.(n.guid, n.name)}
                    title="Select & frame in viewport">
                    <span className="fl-dot" style={{ background: catColor(n.category || 'other') }} />
                    <span className="fl-name">{n.name}</span>
                    <span className="fl-meta">{n.type}</span>
                  </button>
                ))}
                {objs.length > 300 && <div className="fl-more">+{objs.length - 300} more</div>}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
