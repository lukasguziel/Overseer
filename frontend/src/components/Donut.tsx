import { catColor } from '../lib/colors'
import { humanNum } from '../lib/format'

// SVG-Donut mit Legende. data: {key: value}
export default function Donut({ data, colorFn = catColor, format = humanNum }: {
  data: Record<string, number> | undefined
  colorFn?: (key: string) => string
  format?: (n: number) => string
}) {
  const entries = Object.entries(data || {}).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])
  const total = entries.reduce((s, [, v]) => s + v, 0)
  if (!total) return <div className="wb-empty">No data.</div>
  const R = 52; const SW = 20; const C = 2 * Math.PI * R
  let off = 0
  return (
    <div className="donut">
      <svg viewBox="0 0 130 130" className="donut-svg">
        <g transform="translate(65,65) rotate(-90)">
          <circle r={R} fill="none" stroke="var(--panel2)" strokeWidth={SW} />
          {entries.map(([k, v]) => {
            const len = v / total * C
            const seg = <circle key={k} r={R} fill="none" stroke={colorFn(k)} strokeWidth={SW}
              strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-off} />
            off += len
            return seg
          })}
        </g>
        <text x="65" y="61" className="donut-total">{humanNum(total)}</text>
        <text x="65" y="78" className="donut-cap">total</text>
      </svg>
      <div className="legend">
        {entries.map(([k, v]) => (
          <div className="legend-row" key={k}>
            <span className="legend-dot" style={{ background: colorFn(k) }} />
            <span className="legend-key">{k}</span>
            <span className="legend-val">{format(v)} <span className="dim">· {Math.round(v / total * 100)}%</span></span>
          </div>
        ))}
      </div>
    </div>
  )
}
