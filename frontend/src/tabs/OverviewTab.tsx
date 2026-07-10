import React from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import { computeHygiene } from '../lib/hygiene'
import { catColor } from '../lib/colors'
import { humanNum, humanBytes } from '../lib/format'
import Tile, { type Delta } from '../components/Tile'
import Strip from '../components/Strip'
import Treemap from '../components/Treemap'
import Ring from '../components/Ring'
import { scoreRating, scoreTone } from '../lib/score'
import Tip from '../components/Tip'
import AssetTable from '../components/AssetTable'
import EmptyState from '../components/EmptyState'
import { useAuditData } from '../hooks/useAudit'
import { TABS } from '../lib/constants'

// The guided flow, in the order that makes sense for a scene cleanup.
// Steps whose tab is parked ("soon") are hidden from the strip too.
const PARKED = new Set(TABS.filter(([, , soon]) => soon).map(([id]) => id))
const SHOW_WORKFLOW = false
const FLOW = ([
  { tab: 'naming', label: 'Normalize names' },
  { tab: 'translate', label: 'Translate names' },
  { tab: 'structure', label: 'Group objects' },
  { tab: 'layers', label: 'Tag layers' },
  { tab: 'materials', label: 'Clean materials' },
] as const).filter((s) => !PARKED.has(s.tab))

export default function OverviewTab({ org }: { org: Organizer }) {
  const { report, compliance, busy, history } = org
  // ALL hooks BEFORE any early return -> otherwise a Rules-of-Hooks violation.
  const hyg = React.useMemo(
    () => computeHygiene(report?.nodes || [], report?.total_polys || 0,
      { casing: org.casing, kept: org.keeps.naming }),
    [report, org.casing, org.keeps.naming])
  // External files size (Alembic/caches/…) from the shared files scan —
  // prefetched while the Overview is open.
  const filesScan = useAuditData<{ summary?: { total_bytes?: number } }>('files_scan')

  // Casing distribution for display: detection classes that are COMPATIBLE
  // with the chosen convention fold into it — a single-word ALL-CAPS name
  // cannot be anything but "UPPER", yet it fully matches UPPER_SNAKE.
  const COMPAT: Record<string, string[]> = {
    UPPER_SNAKE: ['UPPER'],
    lower_snake: ['lower'],
    PascalCase: ['Capitalized'],
    camelCase: ['lower'],
    kebab: ['lower'],
  }
  // Language distribution: prefer the translate plan's detection (the same
  // engine + numbers the Translate tab shows — preloaded on the Overview);
  // the offline dictionary heuristic is only the fallback before it loads.
  const displayLanguage = React.useMemo(() => {
    const det = org.translation?.detected
    if (det?.counts && det.total > 0) {
      return { data: det.counts as Record<string, number>, fromEngine: true }
    }
    return { data: report?.language || {}, fromEngine: false }
  }, [org.translation, report])

  // Texture budget: resolution mix + estimated UNCOMPRESSED memory (w*h*4
  // bytes — what actually lands in RAM/VRAM, disk size lies for JPGs) and
  // the heaviest maps.
  const texBudget = React.useMemo(() => {
    const entries = report?.textures ? [...report.textures.absolute, ...report.textures.relative] : []
    const withPx = entries.filter((e) => e.width > 0)
    const tiers: Record<string, number> = {}
    let clientMem = 0
    for (const e of withPx) {
      const t = Math.max(e.width, e.height) >= 8192 ? '8K'
        : Math.max(e.width, e.height) >= 4096 ? '4K'
          : Math.max(e.width, e.height) >= 2048 ? '2K' : '< 2K'
      tiers[t] = (tiers[t] || 0) + 1
      clientMem += e.width * e.height * 4
    }
    // Prefer the server aggregate (per physical file, counted once, incl. the
    // mip chain); the per-row client sum is the fallback before it arrives.
    const mem = report?.textures?.total_vram ?? clientMem
    const top = [...withPx].sort((a, b) => b.width * b.height - a.width * a.height).slice(0, 3)
    return { tiers, mem, top, count: withPx.length }
  }, [report])

  const displayCasing = React.useMemo(() => {
    const raw = report?.casing || {}
    const conv = org.casing
    const fold = new Set(COMPAT[conv] || [])
    const out: Record<string, number> = {}
    for (const [k, v] of Object.entries(raw)) {
      const key = k === conv || fold.has(k) ? conv || k : k
      out[key] = (out[key] || 0) + (v as number)
    }
    return out
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [report, org.casing])

  if (!report || compliance == null) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  const toneOf = scoreTone
  const mat = report.materials
  const tex = report.textures

  // Overall health = average of the per-area decision scores (same numbers
  // as the ring next to the navigation). Translate/Layers need their plan —
  // the hook preloads both while the Overview is open; until they arrive the
  // ring shows a placeholder. Structure is parked with its tab.
  const AREAS = [
    { key: 'naming', label: 'Naming', tab: 'naming' as const },
    { key: 'translate', label: 'Translate', tab: 'translate' as const },
    { key: 'layers', label: 'Layers', tab: 'layers' as const },
    { key: 'materials', label: 'Materials', tab: 'materials' as const },
    { key: 'tags', label: 'Tags', tab: 'tags' as const },
    { key: 'files', label: 'Files', tab: 'files' as const },
  ]
  const subScores = AREAS.map((a) => ({ ...a, pct: org.areaScore(a.tab) }))
  const known = subScores.filter((s): s is typeof s & { pct: number } => s.pct != null)
  const health = known.length
    ? Math.round(known.reduce((s, x) => s + x.pct, 0) / known.length)
    : 100
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
        <Tile value={humanNum(report.object_count)} label="Objects" spark={sObj} delta={deltaOf(sObj)}
          sub={[`${Object.keys(report.types || {}).length} distinct types`,
            `${report.max_depth} levels deep`]} />
        <Tile value={humanNum(report.total_polys)} label="Polygons" spark={sPoly} delta={deltaOf(sPoly)}
          sub={[`${humanNum(report.total_points)} points`,
            `${hyg.top10pct}% in the top 10 objects`]} />
        <Tile value={humanBytes(report.file_size)} label="Project size" spark={sSize} delta={deltaOf(sSize)}
          sub={(() => {
            const texB = tex?.total_bytes ?? 0
            const extB = filesScan?.summary?.total_bytes ?? 0
            const lines: string[] = []
            if (texB) lines.push(`+ ${humanBytes(texB)} textures on disk`)
            if (extB) lines.push(`+ ${humanBytes(extB)} external files (Alembic & caches)`)
            if (texB || extB) lines.push(`= ${humanBytes((report.file_size || 0) + texB + extB)} total footprint`)
            return lines.length ? lines : null
          })()} />

        {/* Health tile: big overall ring, sub-scores as a mini-ring list below. */}
        <div className={'tile health-tile tile--' + healthTone}>
          <div className="health-main">
            <Ring pct={health} tone={healthTone} />
            <Tip text="Gesamt-Gesundheit = Durchschnitt der Bereichs-Scores (Naming, Layers, Materials …), 0–100. Ab 80 gilt ein Bereich als gut, ab 95 als top. Ein Wert zählt erst, wenn sein Bereich einmal geladen wurde.">
              <div className="tile-label">Health · {scoreRating(health)}</div>
            </Tip>
          </div>
          <div className="health-subs">
            {subScores.map((s) => (
              <button className="hs" key={s.key} onClick={() => org.setTab(s.tab)} title={`Open ${s.label}`}>
                <Ring pct={s.pct ?? 0} tone={s.pct == null ? 'low' : toneOf(s.pct)} text={false} />
                <span className="hs-pct">{s.pct == null ? '…' : s.pct}</span>
                <span className="hs-label">{s.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Composition strip: scene makeup at a glance (the old substats line
          folded into the tiles above; misplaced lives with Structure). */}
      <Strip data={report.categories} colorFn={(k) => catColor(k)} />

      {/* Guided workflow: the cleanup steps in order, with live todo counts.
          ✓ = that area is clean, amber badge = open todos, no marker = not
          previewed yet (open the step to find out).
          Parked for now — flip SHOW_WORKFLOW to bring it back. */}
      {SHOW_WORKFLOW && <section className="card">
        <div className="card-head">
          <h3>Cleanup workflow</h3>
          <span className="card-hint">work the steps left to right — each one is previewed before anything changes</span>
        </div>
        <div className="flow">
          {FLOW.map((s, i) => {
            const count = org.planCount(s.tab)
            return (
              <button key={s.tab} className="flow-step" onClick={() => org.setTab(s.tab)}
                title={count == null ? `Open ${s.label} to preview` : count > 0 ? `${count} open todo${count === 1 ? '' : 's'}` : 'All clean'}>
                <span className="flow-num">{i + 1}</span>
                {s.label}
                {count != null && (count > 0
                  ? <span className="badge">{count}</span>
                  : <span className="done">✓</span>)}
              </button>
            )
          })}
        </div>
      </section>}

      {/* Hero: Poly-Treemap */}
      <section className="card">
        <div className="card-head">
          <h3>Geometry map — polygons by object</h3>
          <span className="card-hint">click a tile to select &amp; frame</span>
        </div>
        <Treemap nodes={report.nodes || []} onFocus={org.doFocus} />
      </section>

      {/* Row 1: naming consistency + materials summary (the scene-health
          number table is gone — the health tile + nav underlines cover it). */}
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head">
            <h3>Naming consistency</h3>
            {org.casing && <span className="card-hint">convention: {org.casing}</span>}
          </div>
          <div className="chipgroup-label">Casing</div>
          <Strip data={displayCasing} />
          <p className="mini-note dim">
            Detection classes compatible with your convention are merged —
            e.g. single-word ALL-CAPS names count as UPPER_SNAKE. “spaced” /
            “kebab” are names whose separators you chose to keep.
          </p>
          <div className="chipgroup-label" style={{ marginTop: 10 }}>Language</div>
          <Strip data={displayLanguage.data} legendMax={3} />
          <p className="mini-note dim">
            {displayLanguage.fromEngine
              ? `Detected by the ${org.translateEngine} translate engine — same numbers as the Translate tab.`
              : '“Unknown” = names without dictionary words (codes, product names).'}
          </p>
        </section>

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
            {/* Absolute vs relative is a taste question — shown, never warned. */}
            <tr><td>Absolute paths</td><td>{tex?.absolute_count ?? 0}</td></tr>
          </tbody></table>
        </section>
      </div>

      {/* Row 2: polygon concentration (read-only) */}
      <div className="ov-cols2">
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

        <section className="card">
          <div className="card-head">
            <Tip text="Geschätzter Speicherbedarf der Texturen: Breite × Höhe × 4 Byte pro Map, inkl. Mip-Maps (~1,33×) — was die Maps unkomprimiert in RAM/VRAM kosten, unabhängig von der JPG-Größe auf der Platte.">
              <h3>Texture budget</h3>
            </Tip>
            <button className="ghost sm" onClick={() => org.setTab('materials')}>Inspect →</button>
          </div>
          {texBudget.count > 0 ? (
            <>
              <table className="mini"><tbody>
                <tr><td>Maps with pixel data</td><td>{texBudget.count}</td></tr>
                <tr>
                  <td>Est. uncompressed memory</td>
                  <td title="width × height × 4 bytes per map incl. mipmaps (~1.33×) — what the maps cost in RAM/VRAM, regardless of JPG compression on disk">
                    {humanBytes(texBudget.mem)}
                  </td>
                </tr>
                <tr><td>Resolution mix</td><td>
                  {['8K', '4K', '2K', '< 2K'].filter((t) => texBudget.tiers[t])
                    .map((t) => `${texBudget.tiers[t]}× ${t}`).join(' · ') || '—'}
                </td></tr>
              </tbody></table>
              <div className="chipgroup-label" style={{ marginTop: 10 }}>Heaviest maps</div>
              <div className="rename-list">
                {texBudget.top.map((e, i) => (
                  <button key={i} className="fl-row fl-click tb-row"
                    title={`${e.path}\nClick to select material “${e.material}”`}
                    onClick={() => org.doFocusMaterial(e.material)}>
                    <span className="fl-name">{e.file}</span>
                    <span className="dim">{e.width}×{e.height}</span>
                    <span className="dim">{humanBytes(e.width * e.height * 4)}</span>
                  </button>
                ))}
              </div>
            </>
          ) : <div className="fl-empty">No texture pixel data (files missing or none referenced).</div>}
        </section>
      </div>
    </div>
  )
}
