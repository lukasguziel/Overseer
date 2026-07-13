import React, { useRef } from 'react'
import ActionButton from './ActionButton'
import { gradientColorAt, rgb01ToHex, type GradientStop } from '../lib/colors'
import './LayerGradient.css'

// Vertical multi-stop color gradient beside the layer list: the top of the
// bar is the first layer, the bottom the last, and every layer row next to it
// previews its resulting color live. Click the bar to add a stop in between
// (it appears in the color the bar already has there — dragging the picker
// then pulls the blend towards it), click a handle to change its color, drag
// it to move it along the bar, right-click to remove it. The two end handles
// stay put.
export default function LayerGradient({ stops, onChange, count, busy, onApply, children }: {
  stops: GradientStop[]
  onChange: (stops: GradientStop[]) => void
  count: number          // layers the gradient will color (drives the button)
  busy: boolean
  onApply: () => void
  children: React.ReactNode  // the layer list the bar sits next to
}) {
  const barRef = useRef<HTMLDivElement>(null)
  // Drag state for a middle handle. `moved` distinguishes a drag from a
  // click: only a plain click may open the native color picker.
  const dragRef = useRef<{ i: number; moved: boolean } | null>(null)

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
  const handleClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    // The click after a drag must not open the color picker.
    if (dragRef.current?.moved) e.preventDefault()
    dragRef.current = null
  }

  const blend = [...stops].sort((a, b) => a.t - b.t)
    .map((s) => `${s.color} ${(s.t * 100).toFixed(1)}%`).join(', ')

  return (
    <div className="lg-block">
      <div className="section-head sm">
        <span>Color gradient</span>
        <ActionButton tone="go" disabled={busy || !count}
          title="Assign each layer its color from the bar, top to bottom (one undo step)"
          onClick={onApply}>
          Color {count}
        </ActionButton>
      </div>
      <p className="hint-sm">
        Top of the bar is the first layer, bottom the last — each row shows the
        color it will get. Click the bar to add a color in between, click a
        handle to change it, right-click to remove it.
      </p>
      <div className="lg-vwrap">
        <div ref={barRef} className="lg-vbar" onClick={addStop}
          title="Click to add a color stop here"
          style={{ background: `linear-gradient(180deg, ${blend})` }}>
          {stops.map((s, i) => {
            const end = s.t === 0 || s.t === 1
            return (
              <input key={i} type="color"
                className={'lg-vhandle' + (end ? '' : ' mid')} value={s.color}
                style={{ top: `${s.t * 100}%` }}
                onClick={handleClick}
                onPointerDown={end ? undefined : dragStart(i)}
                onPointerMove={end ? undefined : dragMove}
                onChange={(e) => setColor(i, e.target.value)}
                onContextMenu={(e) => { e.preventDefault(); if (!end) removeStop(i) }}
                title={end
                  ? (s.t === 0 ? "The first layer's color" : "The last layer's color")
                  : 'Drag to move · click to change the color · right-click to remove'} />
            )
          })}
        </div>
        <div className="lg-content">{children}</div>
      </div>
    </div>
  )
}
