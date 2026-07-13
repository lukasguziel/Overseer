import React, { useRef, useState } from 'react'
import ActionButton from './ActionButton'
import { gradientColorAt, rgb01ToHex, type GradientStop } from '../lib/colors'
import { IconPencil } from './icons'
import './LayerGradient.css'

// Vertical multi-stop color gradient beside the layer list: the top of the
// bar is the first layer, the bottom the last. "Edit gradient" opens an edit
// session — while it runs, every layer row shows the color it WOULD get (not
// its current one), so the result is judged live. Click the bar to add a stop
// in between (it appears in the color the bar already has there), drag its
// handle to move it, use the pencil to recolor and the ✕ to remove — the
// handle itself is a pure drag grip, so a click can't nudge it accidentally.
// Cancel restores the gradient exactly as it was; "Set gradient" applies.
export default function LayerGradient({ stops, onChange, count, busy, onApply, onEditingChange, children }: {
  stops: GradientStop[]
  onChange: (stops: GradientStop[]) => void
  count: number          // layers the gradient will color (drives the button)
  busy: boolean
  onApply: () => void
  onEditingChange?: (editing: boolean) => void  // parent swaps row swatches to the live preview
  children: React.ReactNode  // the layer list the bar sits next to
}) {
  const barRef = useRef<HTMLDivElement>(null)
  const inputRefs = useRef<(HTMLInputElement | null)[]>([])
  // Drag state for a middle handle. `moved` distinguishes a drag from a
  // click, so the picker never opens at the end of a drag.
  const dragRef = useRef<{ i: number; moved: boolean } | null>(null)
  const [editing, setEditing] = useState(false)
  // Snapshot at edit start — Cancel restores exactly this gradient.
  const savedRef = useRef<GradientStop[]>(stops)

  const setEdit = (on: boolean) => { setEditing(on); onEditingChange?.(on) }
  const startEdit = () => { savedRef.current = stops; setEdit(true) }
  const cancelEdit = () => { onChange(savedRef.current); setEdit(false) }
  const applyEdit = () => { onApply(); setEdit(false) }

  const addStop = (e: React.MouseEvent) => {
    const bar = barRef.current
    if (!bar) return
    const r = bar.getBoundingClientRect()
    const t = Math.min(1, Math.max(0, (e.clientY - r.top) / r.height))
    const color = rgb01ToHex(gradientColorAt(stops, t))
    onChange([...stops, { t, color }].sort((a, b) => a.t - b.t))
  }
  const setColor = (i: number, color: string) =>
    onChange(stops.map((s, j) => (j === i ? { ...s, color } : s)))
  const removeStop = (i: number) => onChange(stops.filter((_, j) => j !== i))

  // Middle stops never reach exactly 0/1 — those positions ARE the ends.
  const dragStart = (i: number) => (e: React.PointerEvent) => {
    dragRef.current = { i, moved: false }
    ;(e.target as HTMLElement).setPointerCapture(e.pointerId)
  }
  const dragMove = (e: React.PointerEvent) => {
    const d = dragRef.current
    const bar = barRef.current
    if (!d || !bar) return
    const r = bar.getBoundingClientRect()
    const t = Math.min(0.98, Math.max(0.02, (e.clientY - r.top) / r.height))
    if (!d.moved && Math.abs(t - stops[d.i].t) * r.height < 3) return
    d.moved = true
    onChange(stops.map((s, j) => (j === d.i ? { ...s, t } : s)))
  }

  const blend = [...stops].sort((a, b) => a.t - b.t)
    .map((s) => `${s.color} ${(s.t * 100).toFixed(1)}%`).join(', ')

  return (
    <div className="lg-block">
      <div className="section-head sm">
        <span>Color gradient</span>
        {editing
          ? (
            <>
              <ActionButton disabled={busy} onClick={cancelEdit}
                title="Discard the edits — the gradient goes back to how it was">
                Cancel
              </ActionButton>
              <ActionButton tone="go" disabled={busy || !count} onClick={applyEdit}
                title="Assign each layer its color from the bar, top to bottom (one undo step)">
                Set gradient
              </ActionButton>
            </>
          )
          : (
            <ActionButton disabled={busy || !count} onClick={startEdit}
              title="Edit the gradient — add, move and recolor stops; the rows preview the result live">
              Edit gradient
            </ActionButton>
          )}
      </div>
      {editing && (
        <p className="hint-sm">
          Top of the bar is the first layer, bottom the last — each row shows
          the color it will get. Click the bar to add a color in between, drag
          a handle to move it, recolor it with the pencil, remove it with ✕.
        </p>
      )}
      <div className={'lg-vwrap' + (editing ? ' editing' : '')}>
        <div ref={barRef} className={'lg-vbar' + (editing ? ' editing' : '')}
          onClick={editing ? addStop : undefined}
          title={editing ? 'Click to add a color stop here' : undefined}
          style={{ background: `linear-gradient(180deg, ${blend})` }}>
          {editing && stops.map((s, i) => {
            const end = s.t === 0 || s.t === 1
            if (end) {
              return (
                <input key={i} type="color" className="lg-vhandle" value={s.color}
                  ref={(el) => { inputRefs.current[i] = el }}
                  style={{ top: `${s.t * 100}%` }}
                  onClick={(e) => e.stopPropagation()}
                  onChange={(e) => setColor(i, e.target.value)}
                  title={s.t === 0 ? "The first layer's color" : "The last layer's color"} />
              )
            }
            return (
              <div key={i} className="lg-stopwrap" style={{ top: `${s.t * 100}%` }}
                onClick={(e) => e.stopPropagation()}>
                <button className="rn-no lg-mini" disabled={busy}
                  title="Remove this stop" onClick={() => removeStop(i)}>✕</button>
                <button className="rn-keep lg-mini" disabled={busy}
                  title="Change this stop's color"
                  onClick={() => inputRefs.current[i]?.click()}><IconPencil /></button>
                <input type="color" className="lg-vhandle mid" value={s.color}
                  ref={(el) => { inputRefs.current[i] = el }}
                  onPointerDown={dragStart(i)}
                  onPointerMove={dragMove}
                  onClick={(e) => {
                    // The grip only drags: a real click must not open the
                    // picker (that is the pencil's job — a programmatic
                    // pencil click is not "trusted" and passes through).
                    e.stopPropagation()
                    if (e.nativeEvent.isTrusted) e.preventDefault()
                    dragRef.current = null
                  }}
                  onChange={(e) => setColor(i, e.target.value)}
                  onContextMenu={(e) => { e.preventDefault(); removeStop(i) }}
                  title="Drag to move this stop" />
              </div>
            )
          })}
        </div>
        <div className="lg-content">{children}</div>
      </div>
    </div>
  )
}
