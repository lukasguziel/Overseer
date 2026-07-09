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
import ConfirmModal from '../components/ConfirmModal'

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
// Row status: only MISSING is a defect (err). Absolute vs relative is a
// pipeline preference — both render as healthy, the badge tells which.
const texDot = (e: TextureEntry): string =>
  e.missing ? 'var(--err)' : 'var(--apply)'

// One texture row. Missing rows carry their own decision buttons:
// … browse for a replacement file (opens C4D's native file dialog),
// ✕ clear THIS dead reference.
function TexRow({ e, thumb, onFocus, onPick, onClear }: {
  e: TextureEntry
  thumb?: string
  onFocus: (material: string) => void
  onPick?: (e: TextureEntry) => void
  onClear?: (e: TextureEntry) => void
}) {
  const actionable = e.missing && (onPick || onClear)
  return (
    <div className={'tex-tr tex-click' + (actionable ? ' tex-actionable' : '')}
      title={`${e.resolved || e.path}\nClick to select material “${e.material}” & frame its object`}
      onClick={() => onFocus(e.material)}>
      <span className="tex-cell-file">
        {thumb
          ? (
            <span className={'tex-thumb-wrap' + (e.exists ? ' openable' : '')}
              title={e.exists ? 'Open the image in your picture viewer' : undefined}
              onClick={(ev) => {
                if (!e.exists) return
                ev.stopPropagation()
                call('open_file', { path: e.resolved || e.path }).catch(() => {})
              }}>
              <img className="tex-thumb" src={thumb} alt="" draggable={false} />
              {e.exists && <span className="tex-thumb-eye">👁</span>}
            </span>
          )
          : <span className="fl-dot" style={{ background: texDot(e) }} />}
        <span className="tex-cut">{e.file}</span>
        {!e.used && <span className="tex-badge unused">unused</span>}
      </span>
      <span className="tex-cell-path dim">
        <span className="tex-cut">{e.path}</span>
        {e.missing
          ? <span className="tex-badge missing">missing</span>
          : e.relocatable
            ? <span className="tex-badge fixable">→ relative</span>
            : <span className="tex-badge">{e.absolute ? 'absolute' : 'relative'}</span>}
      </span>
      <span className="num">
        {e.res_tag ? <span className={'tex-badge tex-res ' + resTier(e)}>{e.res_tag}</span> : '—'}
      </span>
      <span className="num dim">{e.width > 0 ? `${e.width}×${e.height}` : '—'}</span>
      <span className="num">{e.bytes > 0 ? humanBytes(e.bytes) : '—'}</span>
      <span className="dim tex-cut">{e.material}</span>
      {actionable && (
        <span className="rn-actions" onClick={(ev) => ev.stopPropagation()}>
          {onPick && (
            <button className="rn-ok" title="Browse — pick the replacement file in Cinema 4D's file dialog (undoable)"
              onClick={() => onPick(e)}>…</button>
          )}
          {onClear && (
            <button className="rn-no" title="Clear this dead reference — the material stops pointing at the missing file (undoable)"
              onClick={() => onClear(e)}>✕</button>
          )}
        </span>
      )}
    </div>
  )
}

function TexTable({ rows, previews, onFocus, onPick, onClear }: {
  rows: TextureEntry[]
  previews: Record<string, string>
  onFocus: (material: string) => void
  onPick?: (e: TextureEntry) => void
  onClear?: (e: TextureEntry) => void
}) {
  return (
    <div className="tex-table">
      <div className="tex-tr tex-thead">
        <span>File</span><span>Path</span><span className="num">Res</span>
        <span className="num">Pixels</span><span className="num">Size</span><span>Material</span>
      </div>
      {rows.map((e, i) => (
        <TexRow key={e.path + '|' + e.material + '|' + i} e={e}
          thumb={previews[e.resolved || e.path]}
          onFocus={onFocus} onPick={onPick} onClear={onClear} />
      ))}
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
  const mat = report?.materials
  const tex = report?.textures

  // unused (deletable, used nowhere) and only_hidden (used exclusively by
  // hidden objects, protected) are independent lists since the identity fix
  // — both are always shown, regardless of the visibility toggle.
  const unusedPager = usePager(mat?.unused || [])
  // ONE paths list, narrowed by two filters in the settings panel:
  // resolution tier and path status (absolute / relative / missing).
  const [resFilter, setResFilter] = useState('')
  const [pathFilter, setPathFilter] = useState('')  // '' | 'absolute' | 'relative' | 'missing'
  // Copy & relink out-of-project textures: target subfolder + confirm state.
  const [collectDir, setCollectDir] = useState('tex')
  const [collectConfirm, setCollectConfirm] = useState(false)
  // Missing-texture actions: relink from a search folder / clear dead refs.
  const [relinkDir, setRelinkDir] = useState('')
  const [relinkConfirm, setRelinkConfirm] = useState(false)
  const [clearConfirm, setClearConfirm] = useState(false)
  const byRes = (e: TextureEntry) => !resFilter || resTier(e) === resFilter
  const byPath = (e: TextureEntry) =>
    !pathFilter
    || (pathFilter === 'missing' && e.missing)
    || (pathFilter === 'absolute' && e.absolute && !e.missing)
    || (pathFilter === 'relative' && !e.absolute && !e.missing)
  const allTex = tex ? [...tex.absolute, ...tex.relative] : []
  const pathPager = usePager(allTex.filter((e) => byRes(e) && byPath(e)).sort(bySize))

  // Mini image previews for the texture rows currently on screen (keyed by
  // resolved path; missing files simply keep their status dot).
  const [texPreviews, setTexPreviews] = useState<Record<string, string>>({})
  const visiblePaths = pathPager.rows
    .map((e) => e.resolved || e.path).filter(Boolean)
  const visibleKey = visiblePaths.join('\n')
  // Thumbnails are fetched in SMALL CHUNKS: each chunk is its own request,
  // so the C4D main thread is free between chunks (other API calls
  // interleave instead of queueing behind one 15s+ preview job) and the
  // images pop in progressively. The server caches rendered previews, so
  // revisiting the tab is instant.
  useEffect(() => {
    const paths = visibleKey ? visibleKey.split('\n') : []
    const missing = paths.filter((p) => !(p in texPreviews))
    if (!missing.length) return
    let alive = true
    ;(async () => {
      // 4 per request: big EXR/HDR maps take ~1s each to thumbnail, and each
      // request blocks the C4D main thread — keep the blocks short.
      for (let i = 0; i < missing.length && alive; i += 4) {
        try {
          const r = await call('texture_previews', { paths: missing.slice(i, i + 4), size: 40 })
          if (alive) setTexPreviews((prev) => ({ ...prev, ...(r.previews || {}) }))
        } catch { /* dots stay as fallback */ }
      }
    })()
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleKey])

  // Preview spheres for the unused list, fetched once per material set.
  const [previews, setPreviews] = useState<Record<string, string>>({})
  const wanted = [...(mat?.unused || []), ...(mat?.only_hidden || [])].join('\n')
  useEffect(() => {
    const names = wanted ? wanted.split('\n') : []
    if (!names.length) { setPreviews({}); return }
    let alive = true
    ;(async () => {
      for (let i = 0; i < names.length && alive; i += 8) {
        try {
          const r = await call('material_previews', { names: names.slice(i, i + 8), size: 48 })
          if (alive) setPreviews((prev) => ({ ...prev, ...(r.previews || {}) }))
        } catch { /* dots stay as fallback */ }
      }
    })()
    return () => { alive = false }
  }, [wanted])

  if (!report) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  const fixable = tex?.relocatable_count ?? 0
  // Absolute textures OUTSIDE the project: rewriting alone cannot fix them —
  // the file must be copied into the project first (Copy & relink).
  const collectable = allTex.filter((e) => e.absolute && !e.missing && !e.relocatable).length
  const missingCount = tex?.missing_count ?? 0
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
            {/* The headline number matches what the list below offers to
                delete; only-on-hidden materials are their own count. */}
            <div className="substats" style={{ marginBottom: 12 }}>
              <span><b>{mat.total}</b> total</span>
              <span className={deletable ? 'warn' : ''}><b>{deletable}</b> unused</span>
              {org.includeHidden && (mat.only_hidden?.length ?? 0) > 0 && (
                // Count from the LIST (names can repeat), not the name set.
                <span><b>{mat.only_hidden?.length}</b> only on hidden</span>
              )}
              {acceptedList.length > 0 && <span><b>{acceptedList.length}</b> accepted</span>}
              <span className={mat.missing_textures ? 'warn' : ''}><b>{mat.missing_textures || 0}</b> missing tex</span>
            </div>
            <Workbench
              title="Unused materials" count={deletable} loading={busy}
              empty="Every material is in use 🎉"
              hint="Click a row to select the material in Cinema 4D · ✓ deletes it · = keeps it"
              applyLabel="Delete all"
              onApply={() => org.doDeleteAllUnused(deletable)}
              onAcceptAll={() => org.keepAll('materials')}
              busy={busy} progress={org.progress}
            >
              <div className="rename-list">
                {unusedPager.rows.map((nm) => (
                  <SuggestionRow key={nm} busy={busy}
                    applyTitle="Apply — delete this material (undoable)"
                    onApply={() => org.doDeleteMaterial(nm)}
                    onAcceptAsIs={() => org.keep('materials', nm)}
                    onFocus={() => org.doFocusMaterial(nm)}
                  >
                    <MatThumb src={previews[nm]} fallback="var(--dim2)" />
                    <span className="rn-old" title={nm}>{nm}</span>
                    <span className="rn-arrow">→</span>
                    <span className="rn-new dim">delete</span>
                  </SuggestionRow>
                ))}
              </div>
              <Pager pager={unusedPager} />
            </Workbench>
            {/* Only-on-hidden materials belong to the ALL-OBJECTS view: with
                'Visible only' active, hidden usage is out of scope, so these
                rows disappear along with it. Rendered directly under the
                unused list (same card) as protected rows. */}
            {org.includeHidden && (mat.only_hidden?.length ?? 0) > 0 && (
              <div className="rename-list" style={{ marginTop: 10 }}>
                {(mat.only_hidden || []).map((nm, i) => (
                  <div className="fl-row static mat-row" key={nm + i}>
                    <MatThumb src={previews[nm]} fallback="var(--warn)" />
                    <span className="fl-name">{nm}</span>
                    <span className="tex-badge unused" title="Used only by objects that are hidden in the editor — kept safe from deletion">only on hidden</span>
                  </div>
                ))}
              </div>
            )}
            <AcceptedSection items={mat.accepted_all || []}
              onRestore={(nm) => org.unkeep('materials', nm)}
              hint="Accepted materials stay in the scene, are remembered (config) and no longer count as problems." />
          </>
        ) : <div className="fl-empty">No material data.</div>}
      </section>

      {/* ---- Textures: ONE area — settings/filters left, paths right --- */}
      {tex ? (
        <div className="workbench">
          <aside className="wb-side">
            <h3>Textures</h3>
            <p className="hint-sm">
              Real pixel size, disk size and a resolution tag per map — spot the
              8K textures eating memory that could be 4K, and the paths that
              break when the project moves. Heaviest first.
            </p>
            <div className="substats" style={{ marginBottom: 12 }}>
              <span><b>{tex.total}</b> maps</span>
              <span><b>{humanBytes(tex.total_bytes)}</b> on disk</span>
            </div>

            <div className="rule-group-head"><span>Path status</span></div>
            <div className="tex-filter tex-filter-col">
              {([['', 'All', allTex.length],
                ['absolute', 'Absolute', allTex.filter((e) => e.absolute && !e.missing).length],
                ['relative', 'Relative', allTex.filter((e) => !e.absolute && !e.missing).length],
                ['missing', 'Missing', allTex.filter((e) => e.missing).length],
              ] as [string, string, number][]).map(([key, label, n]) => (
                <button key={key || 'all'}
                  className={'tex-filter-btn' + (pathFilter === key ? ' on' : '')
                    + (key === 'missing' && n > 0 ? ' tf-warn' : '')}
                  title={key ? `Show only ${label.toLowerCase()} paths` : 'Show every texture path'}
                  onClick={() => setPathFilter(key)}>
                  {label} <em>{n}</em>
                </button>
              ))}
            </div>

            <div className="rule-group-head"><span>Resolution</span></div>
            <div className="tex-filter tex-filter-col">
              {RES_TIERS.map(([key, label]) => (
                <button key={key || 'all'}
                  className={'tex-filter-btn' + (resFilter === key ? ' on' : '')}
                  title={key ? `Show only ${label} textures` : 'Show all resolutions'}
                  onClick={() => setResFilter(key)}>
                  {label} <em>{key ? allTex.filter((e) => resTier(e) === key).length : allTex.length}</em>
                </button>
              ))}
            </div>

            <div className="rule-group-head"><span>Actions</span></div>
            <button className="ghost" disabled={busy || !fixable}
              title={fixable
                ? `Rewrite ${fixable} absolute path(s) that live under the project folder to relative (undoable)`
                : 'No absolute paths inside the project folder'}
              onClick={() => setConfirm(true)}>
              Fix paths ({fixable})
            </button>
            <label style={{ marginTop: 8 }}>Copy target folder
              <input className="nl-input" value={collectDir}
                onChange={(e) => setCollectDir(e.target.value)}
                title="Project subfolder out-of-project textures are copied into" />
            </label>
            <button className="ghost" disabled={busy || !collectable}
              title={collectable
                ? `Copy the ${collectable} texture file(s) that live OUTSIDE the project into “${collectDir || 'tex'}/” and relink the shaders relatively`
                : 'No existing textures outside the project folder'}
              onClick={() => setCollectConfirm(true)}>
              Copy &amp; relink ({collectable})
            </button>
            <p className="hint-sm">
              <b>Fix paths</b> rewrites absolute paths that already point inside
              the project. <b>Copy &amp; relink</b> first copies out-of-project
              files into the folder above, then relinks relatively.
            </p>

            {!tex.doc_path && (
              <p className="example warn">Project not saved — paths cannot be made relative yet.</p>
            )}
          </aside>

          <div className="wb-preview">
            <div className="wb-preview-head">
              <h3>Paths</h3>
              <span className="wb-count">
                {pathPager.total === 0 ? 'nothing to show'
                  : `${pathPager.total} map${pathPager.total === 1 ? '' : 's'}`}
              </span>
              {missingCount > 0 && (
                <>
                  <button className="wb-accept-all" disabled={busy}
                    title="Pick a folder in Cinema 4D — it is searched recursively for the missing file names and every match is relinked (undoable)"
                    onClick={() => {
                      call('pick_folder', { title: 'Folder to search for the missing textures' })
                        .then((r) => { if (r.path) { setRelinkDir(r.path); setRelinkConfirm(true) } })
                        .catch(() => {})
                    }}>
                    … Relink {missingCount} missing
                  </button>
                  <button className="wb-accept-all" disabled={busy}
                    title="Blank the dead path on every reference whose file is missing — the materials stay, the broken references go (undoable)"
                    onClick={() => setClearConfirm(true)}>
                    ✕ Clear {missingCount} missing
                  </button>
                </>
              )}
            </div>
            <p className="hint-sm wb-hint">Click a row to select its material in Cinema 4D · missing rows: … pick the replacement file · ✕ clear the dead reference.</p>
            <div className="wb-scroll">
              {pathPager.total
                ? <>
                    <TexTable rows={pathPager.rows}
                      previews={texPreviews} onFocus={org.doFocusMaterial}
                      onPick={(e) => org.doPickTexturePath(e.path, e.material)}
                      onClear={(e) => org.doSetTexturePath(e.path, '', e.material)} />
                    <Pager pager={pathPager} />
                  </>
                : <div className="wb-empty">
                    {pathFilter === 'missing' ? 'No missing textures 🎉'
                      : pathFilter === 'absolute' ? 'No absolute texture paths 🎉'
                        : 'No textures match the filters.'}
                  </div>}
            </div>
          </div>
        </div>
      ) : (
        <section className="card">
          <div className="card-head"><h3>Textures</h3></div>
          <div className="fl-empty">No texture data.</div>
          {report.textures_error && (
            <p className="example warn" style={{ marginTop: 8 }}>
              Texture scan failed: <code>{report.textures_error}</code>
            </p>
          )}
        </section>
      )}

      {confirm && (
        <ConfirmModal
          title="Fix paths"
          message={`Rewrite ${fixable} absolute texture path${fixable === 1 ? '' : 's'} that already live under the project folder to project-relative paths (one undo step). Continue?`}
          confirmLabel={`✓ Fix ${fixable} path${fixable === 1 ? '' : 's'}`}
          onConfirm={() => { setConfirm(false); org.doFixTexturesRelative() }}
          onCancel={() => setConfirm(false)}
        />
      )}
      {relinkConfirm && (
        <ConfirmModal
          title="Relink missing textures"
          message={`Search “${relinkDir.trim()}” (including subfolders) for the ${missingCount} missing file name${missingCount === 1 ? '' : 's'} and relink every match (project-relative when possible, one undo step). Files not found there are left as-is. Continue?`}
          confirmLabel={`✓ Relink ${missingCount}`}
          onConfirm={() => { setRelinkConfirm(false); org.doRelinkTextures(relinkDir.trim()) }}
          onCancel={() => setRelinkConfirm(false)}
        />
      )}
      {clearConfirm && (
        <ConfirmModal
          title="Clear missing references"
          message={`Blank the dead texture path on ${missingCount} reference${missingCount === 1 ? '' : 's'} whose file is missing. The materials stay — they just stop pointing at files that no longer exist (one undo step). Continue?`}
          confirmLabel={`✓ Clear ${missingCount} refs`}
          onConfirm={() => { setClearConfirm(false); org.doClearMissingTextures() }}
          onCancel={() => setClearConfirm(false)}
        />
      )}
      {collectConfirm && (
        <ConfirmModal
          title="Copy textures into the project"
          message={`Copy ${collectable} texture file${collectable === 1 ? '' : 's'} that live outside the project into “${(collectDir || 'tex').trim()}/” and relink the shaders with relative paths. The relink is one undo step; the copied files themselves stay on disk (originals are not touched). Continue?`}
          confirmLabel={`✓ Copy & relink ${collectable}`}
          onConfirm={() => { setCollectConfirm(false); org.doCollectTextures((collectDir || 'tex').trim()) }}
          onCancel={() => setCollectConfirm(false)}
        />
      )}
    </div>
  )
}
