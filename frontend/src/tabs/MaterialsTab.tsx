import { useEffect, useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import type { TextureEntry } from '../types'
import { humanBytes } from '../lib/format'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedSection from '../components/AcceptedSection'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'

// Colour the resolution tag by tier so heavy 4K/8K maps jump out.
function resTier(e: TextureEntry): string {
  const px = Math.max(e.width, e.height)
  if (px >= 8192) return 'res-8k'
  if (px >= 4096) return 'res-4k'
  if (px >= 2048) return 'res-2k'
  return 'res-sm'
}

// Texture table: fixed grid columns so file / path / res / pixels / size /
// material line up cleanly; long names and paths get ellipsis-truncated.
// Rows are clickable: they select the material in C4D and frame the first
// object carrying it.
function TexTable({ rows, dot, previews, onFocus }: {
  rows: TextureEntry[]
  dot: string
  previews: Record<string, string>
  onFocus: (material: string) => void
}) {
  return (
    <div className="tex-table">
      <div className="tex-tr tex-thead">
        <span>File</span><span>Path</span><span className="num">Res</span>
        <span className="num">Pixels</span><span className="num">Size</span><span>Material</span>
      </div>
      {rows.map((e, i) => {
        const thumb = previews[e.resolved || e.path]
        return (
          <button className="tex-tr tex-click" key={i}
            title={`${e.resolved || e.path}\nClick to select material “${e.material}” & frame its object`}
            onClick={() => onFocus(e.material)}>
            <span className="tex-cell-file">
              {thumb
                ? <img className="tex-thumb" src={thumb} alt="" draggable={false} />
                : <span className="fl-dot" style={{ background: dot }} />}
              <span className="tex-cut">{e.file}</span>
              {!e.used && <span className="tex-badge unused">unused</span>}
            </span>
            <span className="tex-cell-path dim">
              <span className="tex-cut">{e.path}</span>
              {e.relocatable && <span className="tex-badge fixable">→ relative</span>}
            </span>
            <span className="num">
              {e.res_tag ? <span className={'tex-badge tex-res ' + resTier(e)}>{e.res_tag}</span> : '—'}
            </span>
            <span className="num dim">{e.width > 0 ? `${e.width}×${e.height}` : '—'}</span>
            <span className="num">{e.bytes > 0 ? humanBytes(e.bytes) : '—'}</span>
            <span className="dim tex-cut">{e.material}</span>
          </button>
        )
      })}
    </div>
  )
}

// Resolution filter chips: narrow all three texture sections to one tier.
const RES_TIERS: [string, string][] = [
  ['', 'all'], ['res-8k', '8K'], ['res-4k', '4K'], ['res-2k', '2K'], ['res-sm', '< 2K'],
]

const bySize = (a: TextureEntry, b: TextureEntry) => b.bytes - a.bytes

// Material preview sphere (as in the C4D material manager); falls back to the
// plain status dot until the thumbnail arrives (or if C4D can't render one).
function MatThumb({ src, fallback }: { src?: string; fallback: string }) {
  return src
    ? <img className="mat-thumb" src={src} alt="" draggable={false} />
    : <span className="fl-dot" style={{ background: fallback }} />
}

export default function MaterialsTab({ org }: { org: Organizer }) {
  const { report, busy } = org
  const [confirm, setConfirm] = useState(false)         // make textures relative
  const [bulkConfirm, setBulkConfirm] = useState(false) // delete unused materials
  const mat = report?.materials
  const tex = report?.textures

  const onHidden = new Set(mat?.only_hidden || [])
  // Hooks before the early return (Rules of Hooks).
  const unusedPager = usePager(
    (mat?.unused || []).filter((nm) => !onHidden.has(nm)))
  // Three clean sections: missing first (a missing map is neither usable as
  // absolute nor relative), the rest split by path style, heaviest first.
  // An active resolution filter narrows all three.
  const [resFilter, setResFilter] = useState('')
  const byRes = (e: TextureEntry) => !resFilter || resTier(e) === resFilter
  const allTex = tex ? [...tex.absolute, ...tex.relative] : []
  const missPager = usePager(allTex.filter((e) => e.missing && byRes(e)).sort(bySize))
  const absPager = usePager(tex ? tex.absolute.filter((e) => !e.missing && byRes(e)).sort(bySize) : [])
  const relPager = usePager(tex ? tex.relative.filter((e) => !e.missing && byRes(e)).sort(bySize) : [])

  // Mini image previews for the texture rows currently on screen (keyed by
  // resolved path; missing files simply keep their status dot).
  const [texPreviews, setTexPreviews] = useState<Record<string, string>>({})
  const visiblePaths = [...missPager.rows, ...absPager.rows, ...relPager.rows]
    .map((e) => e.resolved || e.path).filter(Boolean)
  const visibleKey = visiblePaths.join('\n')
  useEffect(() => {
    const paths = visibleKey ? visibleKey.split('\n') : []
    const missing = paths.filter((p) => !(p in texPreviews))
    if (!missing.length) return
    let alive = true
    call('texture_previews', { paths: missing, size: 40 })
      .then((r) => { if (alive) setTexPreviews((prev) => ({ ...prev, ...(r.previews || {}) })) })
      .catch(() => { /* dots stay as fallback */ })
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleKey])

  // Preview spheres for the unused list, fetched once per material set.
  const [previews, setPreviews] = useState<Record<string, string>>({})
  const wanted = (mat?.unused || []).join('\n')
  useEffect(() => {
    const names = wanted ? wanted.split('\n') : []
    if (!names.length) { setPreviews({}); return }
    let alive = true
    call('material_previews', { names, size: 48 })
      .then((r) => { if (alive) setPreviews(r.previews || {}) })
      .catch(() => { /* dots stay as fallback */ })
    return () => { alive = false }
  }, [wanted])

  if (!report) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  const fixable = tex?.relocatable_count ?? 0
  const deletable = mat?.deletable_count ?? (mat?.unused.length ?? 0)
  const acceptedList = mat?.accepted || []

  return (
    <div className="stacked">
      {/* ---- Materials overview (shading definitions) ---------------- */}
      <section className="card">
        <div className="card-head">
          <h3>Materials</h3>
        </div>
        {mat ? (
          <>
            <div className="substats" style={{ marginBottom: 12 }}>
              <span><b>{mat.total}</b> total</span>
              <span className={mat.unused.length ? 'warn' : ''}><b>{mat.unused.length}</b> unused</span>
              {acceptedList.length > 0 && <span><b>{acceptedList.length}</b> accepted</span>}
              {onHidden.size > 0 && <span><b>{onHidden.size}</b> on hidden</span>}
              <span className={mat.missing_textures ? 'warn' : ''}><b>{mat.missing_textures || 0}</b> missing tex</span>
            </div>
            <Workbench
              title="Unused materials" count={deletable} loading={busy}
              empty="Every material is in use 🎉"
              applyLabel={bulkConfirm ? `Really delete ${deletable}?` : 'Delete all'}
              onApply={() => {
                if (bulkConfirm) { org.doDeleteAllUnused(deletable); setBulkConfirm(false) }
                else setBulkConfirm(true)
              }}
              onAcceptAll={() => org.keepAll('materials')}
              busy={busy} progress={org.progress}
              note={bulkConfirm ? 'Click again to delete all unused materials (undoable).' : null}
            >
              <div className="rename-list">
                {unusedPager.rows.map((nm) => (
                  <SuggestionRow key={nm} busy={busy}
                    applyTitle="Apply — delete this material (undoable)"
                    onApply={() => org.doDeleteMaterial(nm)}
                    onAcceptAsIs={() => org.keep('materials', nm)}
                  >
                    <MatThumb src={previews[nm]} fallback="var(--dim2)" />
                    <span className="rn-old" title={nm}>{nm}</span>
                    <span className="rn-arrow">→</span>
                    <span className="rn-new dim">delete</span>
                  </SuggestionRow>
                ))}
                {mat.unused.filter((nm) => onHidden.has(nm)).map((nm) => (
                  <div className="fl-row static mat-row" key={nm}>
                    <MatThumb src={previews[nm]} fallback="var(--warn)" />
                    <span className="fl-name">{nm}</span>
                    <span className="tex-badge unused" title="Used only by hidden objects — kept safe from deletion">on hidden</span>
                  </div>
                ))}
              </div>
              <Pager pager={unusedPager} />
            </Workbench>
            <AcceptedSection items={mat.accepted_all || []}
              onRestore={(nm) => org.unkeep('materials', nm)}
              hint="Accepted materials stay in the scene, are remembered (config) and no longer count as problems." />
          </>
        ) : <div className="fl-empty">No material data.</div>}
      </section>

      {/* ---- Textures (image files on disk) -------------------------- */}
      <section className="card">
        <div className="card-head">
          <h3>Textures</h3>
          {fixable > 0 && (
            confirm ? (
              <span className="mat-confirm">
                make {fixable} relative?
                <button className="mat-yes" title="Confirm — rewrite absolute paths to relative"
                  onClick={() => { org.doFixTexturesRelative(); setConfirm(false) }}>✓</button>
                <button className="mat-no" title="Cancel" onClick={() => setConfirm(false)}>✕</button>
              </span>
            ) : (
              <button className="trash-btn fix-btn" disabled={busy}
                title={`Rewrite ${fixable} absolute path(s) that live under the project folder to relative (undoable)`}
                onClick={() => setConfirm(true)}>
                Fix paths<span className="trash-count">{fixable}</span>
              </button>
            )
          )}
        </div>
        {tex ? (
          <>
            <p className="hint-sm">
              Real pixel size, disk size and a resolution tag per map — spot the 8K
              textures eating memory that could be 4K, and the <b>absolute</b> paths
              that break when the project moves. Sorted by file size (heaviest first).
            </p>
            <div className="substats" style={{ marginBottom: 4 }}>
              <span><b>{tex.total}</b> textures</span>
              <span><b>{humanBytes(tex.total_bytes)}</b> on disk</span>
              <span className={tex.absolute_count ? 'warn' : ''}><b>{tex.absolute_count}</b> absolute</span>
              <span><b>{tex.relative_count}</b> relative</span>
              <span className={tex.missing_count ? 'warn' : ''}><b>{tex.missing_count}</b> missing</span>
            </div>
            <div className="tex-filter">
              <span className="tex-filter-label">Resolution</span>
              {RES_TIERS.map(([key, label]) => (
                <button key={key || 'all'}
                  className={'tex-filter-btn' + (resFilter === key ? ' on' : '')}
                  title={key ? `Show only ${label} textures in the lists below` : 'Show all resolutions'}
                  onClick={() => setResFilter(key)}>
                  {label} {key ? <em>{allTex.filter((e) => resTier(e) === key).length}</em> : <em>{allTex.length}</em>}
                </button>
              ))}
            </div>
            {tex.doc_path
              ? <p className="example" style={{ marginTop: 8 }}>Project: <code>{tex.doc_path}</code></p>
              : <p className="example warn" style={{ marginTop: 8 }}>Project not saved — paths cannot be made relative yet.</p>}
          </>
        ) : (
          <>
            <div className="fl-empty">No texture data.</div>
            {report.textures_error && (
              <p className="example warn" style={{ marginTop: 8 }}>
                Texture scan failed: <code>{report.textures_error}</code>
              </p>
            )}
          </>
        )}
      </section>

      {tex && (
        <>
          {missPager.total > 0 && (
            <section className="card">
              <div className="card-head">
                <h3>Missing textures</h3>
                <span className="card-hint">{missPager.total}</span>
              </div>
              <TexTable rows={missPager.rows} dot="var(--err)"
                previews={texPreviews} onFocus={org.doFocusMaterial} />
              <Pager pager={missPager} />
            </section>
          )}

          <section className="card">
            <div className="card-head">
              <h3>Absolute paths</h3>
              <span className="card-hint">{absPager.total}</span>
            </div>
            {absPager.total
              ? <>
                  <TexTable rows={absPager.rows} dot="var(--warn)"
                    previews={texPreviews} onFocus={org.doFocusMaterial} />
                  <Pager pager={absPager} />
                </>
              : <div className="fl-empty">No absolute texture paths 🎉</div>}
          </section>

          <section className="card">
            <div className="card-head">
              <h3>Relative paths</h3>
              <span className="card-hint">{relPager.total}</span>
            </div>
            {relPager.total
              ? <>
                  <TexTable rows={relPager.rows} dot="var(--apply)"
                    previews={texPreviews} onFocus={org.doFocusMaterial} />
                  <Pager pager={relPager} />
                </>
              : <div className="fl-empty">No relative texture paths.</div>}
          </section>
        </>
      )}
    </div>
  )
}
