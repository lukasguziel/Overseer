import { useMemo, useState } from 'react'
import ActionButton from './ActionButton'
import { gradientColors, layerSwatch } from '../lib/colors'
import './LayerGradient.css'

// Spread a two-handle color gradient across the layers of the overview: the
// first layer gets the left color, the last the right, everything between
// sits on its evenly spaced stop. Ticking layers in the list narrows the
// target; with nothing ticked every layer is colored. The stops ON the bar
// are the actual per-layer colors that will be applied.
export default function LayerGradient({ names, selectedCount, busy, onApply }: {
  names: string[]        // target layers, in the order the overview lists them
  selectedCount: number  // ticked layers (0 = gradient goes to all)
  busy: boolean
  onApply: (colors: { name: string; color: [number, number, number] }[]) => void
}) {
  const [from, setFrom] = useState('#38bdf8')
  const [to, setTo] = useState('#f472b6')
  const stops = useMemo(
    () => gradientColors(names.length, from, to),
    [names.length, from, to])

  return (
    <div className="lg-block">
      <div className="section-head sm"><span>Color gradient</span></div>
      <p className="hint-sm">
        Spreads a two-color gradient across{' '}
        {selectedCount > 0
          ? <>the <b>{selectedCount} ticked</b> layer{selectedCount === 1 ? '' : 's'}</>
          : <>all <b>{names.length}</b> layers</>}{' '}
        — each dot on the bar is one layer&apos;s new color. Tick layers below
        to color only those; untick everything to color all.
      </p>
      <div className="lg-row">
        <input className="lg-handle" type="color" value={from}
          onChange={(e) => setFrom(e.target.value)}
          title="Left end of the gradient — the first layer's color" />
        <div className="lg-bar" style={{ background: `linear-gradient(90deg, ${from}, ${to})` }}>
          {stops.map((c, i) => (
            <span key={names[i]} className="lg-stop"
              title={`${names[i]} → this color`}
              style={{
                left: `${stops.length <= 1 ? 0 : (i / (stops.length - 1)) * 100}%`,
                background: layerSwatch(c),
              }} />
          ))}
        </div>
        <input className="lg-handle" type="color" value={to}
          onChange={(e) => setTo(e.target.value)}
          title="Right end of the gradient — the last layer's color" />
        <ActionButton tone="go" disabled={busy || !names.length}
          title="Assign each listed layer its gradient color (one undo step)"
          onClick={() => onApply(names.map((nm, i) => ({ name: nm, color: stops[i] })))}>
          Color {names.length}
        </ActionButton>
      </div>
    </div>
  )
}
