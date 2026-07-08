import React from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import { computeHygiene } from '../lib/hygiene'
import { catColor } from '../lib/colors'
import { humanNum, humanBytes } from '../lib/format'
import Tile, { type Delta } from '../components/Tile'
import Strip from '../components/Strip'
import Treemap from '../components/Treemap'
import Ring, { type Tone } from '../components/Ring'
import AssetTable from '../components/AssetTable'

export default function OverviewTab({ org }: { org: Organizer }) {
  const { report, detectInfo, compliance, busy, history } = org
  // ALL hooks BEFORE any early return -> otherwise a Rules-of-Hooks violation.
  const hyg = React.useMemo(
    () => computeHygiene(report?.nodes || [], report?.total_polys || 0),
    [report])

  if (!report || compliance == null) {
    return (
      <div className="empty-state">
        <p>No scene loaded yet.</p>
        <button onClick={org.doAnalyze} disabled={busy}>Analyze scene</button>
      </div>
    )
  }

  const toneOf = (pct: number): Tone => pct >= 80 ? 'good' : pct >= 50 ? 'mid' : 'low'
  const misplaced = report.misplaced?.length || 0
  const mat = report.materials
  const tex = report.textures

  // Materials score: share of materials that are NOT a problem (unused &
  // not accepted & not only-on-hidden). Accepting an unused material lifts it.
  const matTotal = mat?.total ?? 0
  const matProblem = mat?.deletable_count ?? (mat?.unused.length ?? 0)
  const matScore = matTotal ? Math.round((matTotal - matProblem) / matTotal * 100) : 100

  // Overall health = average of the sub-scores (naming + structure + materials).
  const subScores = [
    { key: 'naming', label: 'Naming', pct: hyg.namingScore, tab: 'naming' as const },
    { key: 'structure', label: 'Structure', pct: compliance, tab: 'structure' as const },
    { key: 'materials', label: 'Materials', pct: matScore, tab: 'materials' as const },
  ]
  const health = Math.round(subScores.reduce((s, x) => s + x.pct, 0) / subScores.length)
  const healthTone = toneOf(health)

  // Trends from the analysis history (this file only, chronological).
  const fh = (history || []).filter((h) => h.file === report.file).sort((a, b) => a.ts - b.ts)
  const seriesOf = (key: string, mul = 1): number[] =>
    fh.map((h) => (h[key] == null ? null : (h[key] as number) * mul))
      .filter((v): v is number => v != null)
  const deltaOf = (arr: number[]): Delta | null => {
    if (arr.length < 2) return null
    const p = arr[arr.length - 2]
    const c = arr[arr.length - 1]
    return { pct: p ? Math.round((c - p) / p * 100) : 0, dir: Math.sign(c - p) }
  }
  const sObj = seriesOf('objects')
  const sPoly = seriesOf('polys')
  const sSize = seriesOf('size')

  return (
    <div className="overview">
      <div className="tiles">
        <Tile value={humanNum(report.object_count)} label="Objects" spark={sObj} delta={deltaOf(sObj)} />
        <Tile value={humanNum(report.total_polys)} label="Polygons" spark={sPoly} delta={deltaOf(sPoly)} />
        <Tile value={humanBytes(report.file_size)} label="Project size" spark={sSize} delta={deltaOf(sSize)} />

        {/* Health tile = circular charts of the sub-scores (click to jump). */}
        <div className={'tile health-tile tile--' + healthTone}>
          <div className="health-rings">
            {subScores.map((s) => (
              <button className="hr" key={s.key} onClick={() => org.setTab(s.tab)} title={`Open ${s.label}`}>
                <Ring pct={s.pct} tone={toneOf(s.pct)} />
                <span>{s.label}</span>
              </button>
            ))}
          </div>
          <div className="tile-label">Health · <b>{health}%</b></div>
        </div>
      </div>

      <div className="substats">
        <span><b>{humanNum(report.total_points)}</b> points</span>
        <span><b>{report.max_depth}</b> max depth</span>
        <span><b>{Object.keys(report.types || {}).length}</b> distinct types</span>
        <span className={misplaced ? 'warn' : ''}><b>{misplaced}</b> misplaced</span>
      </div>

      {/* Composition strip: scene makeup at a glance */}
      <Strip data={report.categories} colorFn={(k) => catColor(k)} />

      {/* Hero: Poly-Treemap */}
      <section className="card">
        <div className="card-head">
          <h3>Geometry map — polygons by object</h3>
          <span className="dim" style={{ fontSize: 11 }}>click a tile to select &amp; frame</span>
        </div>
        <Treemap nodes={report.nodes || []} onFocus={org.doFocus} />
      </section>

      {/* Row 1: health + naming consistency */}
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head"><h3>Scene health</h3></div>
          <table className="mini"><tbody>
            <tr><td>Misplaced</td><td className={misplaced ? 'warn' : ''}>{misplaced}</td></tr>
            <tr><td>Default names</td><td className={hyg.defaults.length ? 'warn' : ''}>{hyg.defaults.length}</td></tr>
            <tr><td>Duplicate names</td><td className={hyg.dupTotal ? 'warn' : ''}>{hyg.dupTotal}</td></tr>
            <tr><td>Empty groups</td><td className={hyg.emptyGroups.length ? 'warn' : ''}>{hyg.emptyGroups.length}</td></tr>
          </tbody></table>
          <div className="ov-links">
            <button className="ghost sm" onClick={() => org.setTab('naming')}>Fix naming →</button>
            <button className="ghost sm" onClick={() => org.setTab('structure')}>Fix structure →</button>
          </div>
          {detectInfo && <p className="mini-note dim">detected: {detectInfo.style} / {String(detectInfo.language)} / pad {detectInfo.number_pad} · {Math.round(detectInfo.confidence * 100)}%</p>}
        </section>

        <section className="card">
          <div className="card-head"><h3>Naming consistency</h3></div>
          <div className="chipgroup-label">Casing</div>
          <Strip data={report.casing} />
          <div className="chipgroup-label" style={{ marginTop: 14 }}>Language</div>
          <Strip data={report.language} legendMax={3} />
        </section>
      </div>

      {/* Row 2: materials summary + polygon concentration (read-only) */}
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head">
            <h3>Materials &amp; textures</h3>
            <button className="ghost sm" onClick={() => org.setTab('materials')}>Manage →</button>
          </div>
          <table className="mini"><tbody>
            <tr><td>Materials</td><td>{mat?.total ?? 0}</td></tr>
            <tr><td>Unused materials</td><td className={mat?.unused.length ? 'warn' : ''}>{mat?.unused.length ?? 0}</td></tr>
            <tr><td>Missing textures</td><td className={mat?.missing_textures ? 'warn' : ''}>{mat?.missing_textures ?? 0}</td></tr>
            <tr><td>Textures on disk</td><td>{humanBytes(tex?.total_bytes ?? 0)}</td></tr>
            <tr><td>Absolute paths</td><td className={tex?.absolute_count ? 'warn' : ''}>{tex?.absolute_count ?? 0}</td></tr>
          </tbody></table>
        </section>

        <section className="card">
          <div className="card-head">
            <h3>Polygon concentration</h3>
            <button className="ghost sm" onClick={() => org.setTab('assets')}>Browse all →</button>
          </div>
          <table className="mini"><tbody>
            <tr><td>Total polygons</td><td>{humanNum(report.total_polys)}</td></tr>
            <tr><td>Top 10 objects</td><td>{hyg.top10pct}%</td></tr>
            <tr><td>Objects for 80%</td><td>{hyg.p80}</td></tr>
            <tr><td>Heavy outliers (&gt;5%)</td><td className={hyg.outliers.length ? 'warn' : ''}>{hyg.outliers.length}</td></tr>
          </tbody></table>
          {hyg.outliers.length > 0 && (
            <AssetTable rows={hyg.outliers.slice(0, 5)} onFocus={org.doFocus} />
          )}
        </section>
      </div>
    </div>
  )
}
