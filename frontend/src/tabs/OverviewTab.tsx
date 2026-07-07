import React, { useState } from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import { computeHygiene } from '../lib/hygiene'
import { catColor } from '../lib/colors'
import { humanNum, humanBytes } from '../lib/format'
import Tile, { type Delta } from '../components/Tile'
import Strip from '../components/Strip'
import Treemap from '../components/Treemap'
import Ring, { type Tone } from '../components/Ring'
import Cleanup, { type CleanupBucket } from '../components/Cleanup'
import AssetTable from '../components/AssetTable'
import UnusedMaterials from '../components/UnusedMaterials'
import { IconTrash } from '../components/icons'

export default function OverviewTab({ org }: { org: Organizer }) {
  const { report, detectInfo, compliance, busy, history } = org
  // ALL hooks BEFORE any early return -> otherwise a Rules-of-Hooks violation.
  const [bulkConfirm, setBulkConfirm] = useState(false)
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

  const tone: Tone = compliance >= 80 ? 'good' : compliance >= 50 ? 'mid' : 'low'
  const misplaced = report.misplaced?.length || 0
  const nameTone: Tone = hyg.namingScore >= 80 ? 'good' : hyg.namingScore >= 50 ? 'mid' : 'low'
  const buckets: CleanupBucket[] = [
    { key: 'default', label: 'Default names', items: hyg.defaults.map((n) => ({ guid: n.guid, name: n.name, meta: n.type })) },
    { key: 'dupes', label: 'Duplicate names', items: hyg.dupes.map((d) => ({ guid: d.guid, name: d.name, meta: '×' + d.count })) },
    { key: 'empty', label: 'Empty groups', items: hyg.emptyGroups.map((n) => ({ guid: n.guid, name: n.name })) },
    { key: 'root', label: 'Root clutter', items: hyg.rootClutter.map((n) => ({ guid: n.guid, name: n.name, meta: n.type })) },
  ]
  const mat = report.materials

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
  const sComp = seriesOf('compliance', 100)

  return (
    <div className="overview">
      <div className="ov-topbar">
        <button className="ghost sm" onClick={org.doAnalyze} disabled={busy}>↻ Refresh analysis</button>
      </div>

      <div className="tiles">
        <Tile value={humanNum(report.object_count)} label="Objects" spark={sObj} delta={deltaOf(sObj)} />
        <Tile value={humanNum(report.total_polys)} label="Polygons" spark={sPoly} delta={deltaOf(sPoly)} />
        <Tile value={humanBytes(report.file_size)} label="Project size" spark={sSize} delta={deltaOf(sSize)} />
        <Tile value={compliance + '%'} label="Structured" tone={tone} spark={sComp} delta={deltaOf(sComp)} />
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
          <div className="card-head">
            <h3>Scene health</h3>
            <button className="ghost sm" onClick={org.doDetect} disabled={busy}>Detect format</button>
          </div>
          <div className="rings">
            <div className="ring-item"><Ring pct={hyg.namingScore} tone={nameTone} /><span>Naming</span></div>
            <div className="ring-item"><Ring pct={compliance} tone={tone} /><span>Structure</span></div>
          </div>
          <table className="mini"><tbody>
            <tr><td>Misplaced</td><td className={misplaced ? 'warn' : ''}>{misplaced}</td></tr>
            <tr><td>Default names</td><td className={hyg.defaults.length ? 'warn' : ''}>{hyg.defaults.length}</td></tr>
            <tr><td>Duplicate names</td><td className={hyg.dupTotal ? 'warn' : ''}>{hyg.dupTotal}</td></tr>
            <tr><td>Empty groups</td><td className={hyg.emptyGroups.length ? 'warn' : ''}>{hyg.emptyGroups.length}</td></tr>
          </tbody></table>
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

      {/* Row 2: cleanup + materials */}
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head"><h3>Cleanup</h3></div>
          <Cleanup buckets={buckets} onFocus={org.doFocus} />
        </section>

        <section className="card">
          <div className="card-head">
            <h3>Materials</h3>
            {mat && mat.unused.length > 0 && (
              bulkConfirm ? (
                <span className="mat-confirm">
                  delete {mat.unused.length}?
                  <button className="mat-yes" title="Confirm delete all unused"
                    onClick={() => { org.doDeleteAllUnused(mat.unused.length); setBulkConfirm(false) }}>✓</button>
                  <button className="mat-no" title="Cancel" onClick={() => setBulkConfirm(false)}>✕</button>
                </span>
              ) : (
                <button className="trash-btn" disabled={busy}
                  title={`Delete all ${mat.unused.length} unused materials (undoable)`}
                  onClick={() => setBulkConfirm(true)}>
                  <IconTrash /><span className="trash-count">{mat.unused.length}</span>
                </button>
              )
            )}
          </div>
          {mat ? (
            <>
              <div className="substats" style={{ marginBottom: 12 }}>
                <span><b>{mat.total}</b> total</span>
                <span className={mat.unused.length ? 'warn' : ''}><b>{mat.unused.length}</b> unused</span>
                <span className={mat.missing_textures ? 'warn' : ''}><b>{mat.missing_textures || 0}</b> missing tex</span>
              </div>
              <div className="chipgroup-label">Unused materials</div>
              <UnusedMaterials names={mat.unused || []} onDelete={org.doDeleteMaterial} />
              {mat.missing.length > 0 && (
                <>
                  <div className="chipgroup-label" style={{ marginTop: 12 }}>Missing textures</div>
                  <div className="focuslist">
                    {mat.missing.slice(0, 10).map((t, i) => (
                      <div className="fl-row static" key={i}>
                        <span className="fl-dot" style={{ background: 'var(--err)' }} />
                        <span className="fl-name">{t.material}</span>
                        <span className="fl-meta dim">{t.file}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          ) : <div className="fl-empty">No material data.</div>}
        </section>
      </div>

      {/* Row 3: heaviest assets + concentration */}
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head">
            <h3>Heaviest assets</h3>
            <button className="ghost sm" onClick={() => org.setTab('assets')}>Browse all →</button>
          </div>
          <AssetTable rows={(report.largest || []).slice(0, 8)} onFocus={org.doFocus}
            empty="No geometry found in the scene." />
        </section>

        <section className="card">
          <div className="card-head"><h3>Polygon concentration</h3></div>
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
