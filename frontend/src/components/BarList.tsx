import { humanNum } from '../lib/format'

export interface BarRow {
  label: string
  value: number
  color?: string
  sub?: string
  onClick?: () => void
}

// Horizontal bar list.
export default function BarList({ rows, format = humanNum, empty }: {
  rows: BarRow[]; format?: (n: number) => string; empty?: string
}) {
  const max = Math.max(1, ...rows.map((r) => r.value))
  if (!rows.length) return <div className="wb-empty">{empty || 'No data.'}</div>
  return (
    <div className="barlist">
      {rows.map((r, i) => {
        const clickable = typeof r.onClick === 'function'
        return (
          <div className={'bar-row' + (clickable ? ' clickable' : '')} key={i}
            onClick={clickable ? r.onClick : undefined}
            title={clickable ? 'Select & frame in viewport' : r.label}>
            <div className="bar-label">{r.label}{r.sub && <span className="bar-sub">{r.sub}</span>}</div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: (r.value / max * 100) + '%', background: r.color || 'var(--accent)' }} />
            </div>
            <div className="bar-value">{format(r.value)}</div>
          </div>
        )
      })}
    </div>
  )
}
