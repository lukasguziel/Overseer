import Sparkline from './Sparkline'

export interface Delta {
  pct: number
  dir: number
}

export default function Tile({ value, label, tone, spark, delta, sub }: {
  value: string | number
  label: string
  tone?: string
  spark?: number[]
  delta?: Delta | null
  sub?: string | string[] | null // small secondary line(s) (e.g. texture/external sizes)
}) {
  return (
    <div className={'tile' + (tone ? ' tile--' + tone : '')}>
      <div className="tile-top">
        <div className="tile-value">{value}</div>
        {spark && spark.length > 1 && <Sparkline data={spark} />}
      </div>
      <div className="tile-label">
        {label}
        {delta && delta.pct !== 0 && (
          <span className={'tile-delta ' + (delta.dir > 0 ? 'up' : 'down')}>
            {delta.dir > 0 ? '▲' : '▼'} {Math.abs(delta.pct)}%
          </span>
        )}
      </div>
      {sub && (Array.isArray(sub) ? sub : [sub]).map((s, i) => (
        <div className="tile-sub" key={i}>{s}</div>
      ))}
    </div>
  )
}
