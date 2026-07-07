import Sparkline from './Sparkline'

export interface Delta {
  pct: number
  dir: number
}

export default function Tile({ value, label, tone, spark, delta }: {
  value: string | number
  label: string
  tone?: string
  spark?: number[]
  delta?: Delta | null
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
    </div>
  )
}
