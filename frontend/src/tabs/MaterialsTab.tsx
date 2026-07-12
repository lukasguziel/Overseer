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
import FilterChips from '../components/FilterChips'
import Tip from '../components/Tip'
import SectionIntro from '../components/SectionIntro'
import { IconFolder } from '../components/icons'

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

// Compact per-texture analysis: channel mode, bit depth, alpha, colorspace,
// estimated VRAM. Shown as the row's hover title; the visible row carries the
// short badges (alpha / greyscale / colorspace).
function specText(e: TextureEntry): string {
  const parts: string[] = []
  const mode = e.greyscale ? 'greyscale' : (e.channels ?? 0) >= 4 ? 'RGBA' : 'RGB'
  parts.push(mode)
  if (e.channels) parts.push(`${e.channels} channels`)
  if (e.bit_depth) parts.push(`${e.bit_depth} bit`)
  parts.push(e.has_alpha ? 'with alpha' : 'no alpha')
  if (e.colorspace) parts.push(e.colorspace)
  if (e.vram) parts.push(`~${humanBytes(e.vram)} VRAM`)
  return parts.join(' · ')
}

// What a map was resized FROM — annotated onto the resized (relinked) row so
// the swap is visible right where it happened.
interface ResizeInfo { fromFile: string; fromDims: string; percent: number }

// Predict the relinked copy's path (stem_<percent>.ext) — mirrors the backend's
// textures.resize_target so we can match the resized row after the re-analyze.
function resizeTargetPath(path: string, percent: number): string {
  const dot = path.lastIndexOf('.')
  return dot < 0 ? `${path}_${percent}` : `${path.slice(0, dot)}_${percent}${path.slice(dot)}`
}

// One texture row, with the decisions for THAT map on its right — the same
// gesture as accept/keep everywhere else in the app. A missing map can be
// re-picked, cleared or accepted; a map that is there can be shrunk, and its
// path flipped between relative and absolute. No batch button decides for you.
function TexRow({ e, thumb, resized, percent, busy, onFocus, onPick, onClear, onAccept, onResize, onRepath }: {
  e: TextureEntry
  thumb?: string
  resized?: ResizeInfo
  percent: number
  busy?: boolean
  onFocus: (material: string) => void
  onPick?: (e: TextureEntry) => void
  onClear?: (e: TextureEntry) => void
  onAccept?: (e: TextureEntry) => void
  onResize?: (e: TextureEntry) => void
  onRepath?: (e: TextureEntry, mode: 'relative' | 'absolute') => void
}) {
  // Missing maps: pick / clear / accept (accepted ones are decided — badge only).
  const missingActions = e.missing && !e.accepted && (onPick || onClear || onAccept)
  // Present maps: shrink (needs real pixels on disk) and flip the path form.
  const canResize = !e.missing && e.exists && e.width > 0 && onResize
  const canRepath = !e.missing && e.exists && onRepath
  const actionable = missingActions || canResize || canRepath
  const pathTip = `${e.path}${e.resolved && e.resolved !== e.path ? `\n→ ${e.resolved}` : ''}`
  return (
    <>
    <div className={'dg-tr cols-tex dg-click' + (actionable ? ' dg-actionable' : '')
        + (resized ? ' tex-resized' : '')}
      title={`${pathTip}${e.width > 0 ? `\n${specText(e)}` : ''}\nClick to select material “${e.material}” & frame its object`}
      onClick={() => onFocus(e.material)}>
      <span className="dg-cell-file">
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
        <span className="dg-cut">{e.file}</span>
        {!e.used && <span className="pill unused">unused</span>}
        {resized && <span className="pill resized">resized</span>}
      </span>
      <span className="dg-cell-path dim">
        {e.missing
          ? (e.accepted
              ? <span className="pill" title="Accepted as missing — no longer counted as a problem">accepted</span>
              : <span className="pill missing">missing</span>)
          : e.relocatable
            ? <span className="pill fixable">→ relative</span>
            : <span className="pill">{e.absolute ? 'absolute' : 'relative'}</span>}
      </span>
      <span className="num">
        {e.res_tag ? <span className={'pill tex-res ' + resTier(e)}>{e.res_tag}</span> : '—'}
      </span>
      <span className="num dim">
        {e.width > 0 ? `${e.width}×${e.height}` : '—'}
        {e.width > 0 && (
          <span className="tex-spec">
            {e.greyscale ? 'grey' : (e.channels ?? 0) >= 4 ? 'RGBA' : 'RGB'}
            {e.has_alpha ? ' +A' : ''}
            {e.bit_depth ? ` ${e.bit_depth}b` : ''}
            {e.colorspace ? ` ${e.colorspace}` : ''}
          </span>
        )}
      </span>
      <span className="num"
        title={e.vram
          ? `~${humanBytes(e.vram)} estimated GPU memory: width × height × channels × bit depth, +1/3 for mipmaps — independent of the compressed size on disk`
          : undefined}>
        {e.bytes > 0 ? humanBytes(e.bytes) : '—'}
        {(e.vram ?? 0) > 0 && (
          <span className="tex-spec tex-vram">~{humanBytes(e.vram!)} VRAM</span>
        )}
      </span>
      <span className="dim dg-cut">{e.material}</span>
      {/* The decision slot exists on every row (empty when there is nothing to
          decide) so the buttons stay in one column. */}
      <span className="rn-actions" onClick={(ev) => ev.stopPropagation()}>
        {actionable && (
          <>
          {missingActions && onPick && (
            <button className="rn-ok" title="Browse — pick the replacement file in Cinema 4D's file dialog (undoable)"
              onClick={() => onPick(e)}><IconFolder /></button>
          )}
          {missingActions && onClear && (
            <button className="rn-no" title="Clear this dead reference — the material stops pointing at the missing file (undoable)"
              onClick={() => onClear(e)}>✕</button>
          )}
          {missingActions && onAccept && (
            <button className="rn-keep" title="Accept as-is — acknowledge the missing file; it stops counting as a problem (restore below)"
              onClick={() => onAccept(e)}>=</button>
          )}
          {canRepath && (
            <button className="rn-keep tex-act" disabled={busy}
              title={e.absolute
                ? `Rewrite this one path relative to the project folder (undoable)`
                : `Rewrite this one path to its full absolute form (undoable)`}
              onClick={() => onRepath!(e, e.absolute ? 'relative' : 'absolute')}>
              {e.absolute ? '→ rel' : '→ abs'}
            </button>
          )}
          {canResize && (
            <button className="rn-ok tex-act" disabled={busy}
              title={`Write a copy of this map at ${percent}% (${e.width}×${e.height} → ${Math.max(1, Math.round(e.width * percent / 100))}×${Math.max(1, Math.round(e.height * percent / 100))}) and relink the material to it (undoable)`}
              onClick={() => onResize!(e)}>
              ↓ {percent}%
            </button>
          )}
          </>
        )}
      </span>
    </div>
    {resized && (
      <div className="tex-resized-note"
        title="This map was just resized — the material now links to this smaller copy. Undo in Cinema 4D to go back.">
        ↳ resized to {resized.percent}% · replaced <b>{resized.fromFile}</b> ({resized.fromDims}
        {' → '}{e.width > 0 ? `${e.width}×${e.height}` : 'smaller'})
      </div>
    )}
    </>
  )
}

function TexTable({ rows, previews, resized, percent, busy, onFocus, onPick, onClear, onAccept, onResize, onRepath }: {
  rows: TextureEntry[]
  previews: Record<string, string>
  resized: Record<string, ResizeInfo>
  percent: number
  busy?: boolean
  onFocus: (material: string) => void
  onPick?: (e: TextureEntry) => void
  onClear?: (e: TextureEntry) => void
  onAccept?: (e: TextureEntry) => void
  onResize?: (e: TextureEntry) => void
  onRepath?: (e: TextureEntry, mode: 'relative' | 'absolute') => void
}) {
  return (
    <div className="dg-table">
      <div className="dg-tr dg-thead cols-tex">
        <Tip text="File name of the texture. Click the thumbnail to open the image in your picture viewer."><span>File</span></Tip>
        <Tip text="Badge shows absolute / relative / missing. Decide per row on the right: flip the path form, shrink the map, or fix a missing reference. Hover a row for its full path."><span>Path</span></Tip>
        <Tip text="Resolution tier (e.g. 4K/8K) — heavy maps stand out instantly."><span className="num">Res</span></Tip>
        <Tip text="Actual pixel dimensions of the file."><span className="num">Pixels</span></Tip>
        <Tip text="File size on disk."><span className="num">Size</span></Tip>
        <Tip text="Material using this texture."><span>Material</span></Tip>
        <Tip text="What you can decide for this map: flip its path form, shrink it, or fix a missing reference."><span>Decide</span></Tip>
      </div>
      {rows.map((e, i) => (
        <TexRow key={e.path + '|' + e.material + '|' + i} e={e}
          thumb={previews[e.resolved || e.path]} percent={percent} busy={busy}
          resized={resized[e.path]}
          onFocus={onFocus} onPick={onPick} onClear={onClear} onAccept={onAccept}
          onResize={onResize} onRepath={onRepath} />
      ))}
    </div>
  )
}

// Facet vocabularies for the filter chips (order = display order).
const RES_FILTERS: [string, string][] = [
  ['res-8k', '8K'], ['res-4k', '4K'], ['res-2k', '2K'], ['res-sm', '< 2K'],
]
const PATH_STATES: [string, string][] = [
  ['absolute', 'Absolute'], ['relative', 'Relative'], ['missing', 'Missing'],
]
const MODES: [string, string][] = [
  ['rgb', 'RGB'], ['rgba', 'RGBA'], ['grey', 'Greyscale'],
]

// Missing maps first (they need a decision), then heaviest first.
const bySize = (a: TextureEntry, b: TextureEntry) =>
  Number(b.missing) - Number(a.missing) || b.bytes - a.bytes

// Spec filter keys, mirroring the per-row spec badge (e.g. "RGB 32b linear"):
// channel mode, bit depth and colorspace. null = no pixel data (unknown) —
// such rows only show while the respective filter is off.
const modeOf = (e: TextureEntry): string | null =>
  e.width > 0 ? (e.greyscale ? 'grey' : (e.channels ?? 0) >= 4 ? 'rgba' : 'rgb') : null
const depthOf = (e: TextureEntry): number | null =>
  e.width > 0 && e.bit_depth ? e.bit_depth : null
const spaceOf = (e: TextureEntry): string | null =>
  e.width > 0 && e.colorspace ? e.colorspace : null

// Material preview sphere (as in the C4D material manager); falls back to the
// plain status dot until the thumbnail arrives (or if C4D can't render one).
function MatThumb({ src, fallback }: { src?: string; fallback: string }) {
  return src
    ? <img className="mat-thumb" src={src} alt="" draggable={false} />
    : <span className="fl-dot" style={{ background: fallback }} />
}

export default function MaterialsTab({ org }: { org: Organizer }) {
  const { report, busy } = org
  const mat = report?.materials
  const tex = report?.textures

  // mat.unused is scope-aware (All objects additionally contains the
  // hidden-only materials); only_hidden just marks which rows get the badge.
  const unusedPager = usePager(mat?.unused || [], 10)
  const onHiddenSet = new Set(mat?.only_hidden || [])
  // ONE paths list, narrowed by two filters in the settings panel:
  // resolution tier and path status (absolute / relative / missing).
  const [resFilter, setResFilter] = useState('')
  const [pathFilter, setPathFilter] = useState('')  // '' | 'absolute' | 'relative' | 'missing'
  // Spec filters (channel mode / bit depth / colorspace) — the values shown
  // in the per-row spec badge, e.g. "RGB 32b linear".
  const [modeFilter, setModeFilter] = useState('')   // '' | 'rgb' | 'rgba' | 'grey'
  const [depthFilter, setDepthFilter] = useState(0)  // 0 = all, else bits/channel
  const [spaceFilter, setSpaceFilter] = useState('') // '' | colorspace tag
  // Copy & relink out-of-project textures: target subfolder + confirm state.
  const [collectDir, setCollectDir] = useState('tex')
  const [collectConfirm, setCollectConfirm] = useState(false)
  // Missing-texture actions: relink from a search folder / clear dead refs.
  const [relinkDir, setRelinkDir] = useState('')
  const [relinkConfirm, setRelinkConfirm] = useState(false)
  const [clearConfirm, setClearConfirm] = useState(false)
  // What the per-row "↓ %" button writes. A setting, not an action — the
  // decision to shrink is made on the row itself.
  const [resizePercent, setResizePercent] = useState(50)
  // Recently resized maps, keyed by the relinked copy's path — annotates that
  // row with a "resized" badge + a note showing what it replaced.
  const [resizedInfo, setResizedInfo] = useState<Record<string, ResizeInfo>>({})
  // Accepted-as-missing textures (persisted in config under the 'textures' keep
  // section); accepting one drops it out of the missing count + score.
  const texAccepted = tex?.accepted_all || []
  const setTexKeeps = (keys: string[]) => {
    call('set_keeps', { section: 'textures', keys })
      .then(() => org.doAnalyze())
      .catch((e) => org.setStatus(`Accept ✗ ${String(e.message || e)}`))
  }
  const acceptTexture = (e: TextureEntry) => setTexKeeps([...texAccepted, e.path])
  // Shrink ONE map. The copy's path is predictable, so the row it will become
  // after the re-analyze is annotated up front with what it replaced.
  const resizeOne = (e: TextureEntry) => {
    setResizedInfo((prev) => ({
      ...prev,
      [resizeTargetPath(e.path, resizePercent)]: {
        fromFile: e.file,
        fromDims: `${e.width}×${e.height}`,
        percent: resizePercent,
      },
    }))
    org.doTextureResize([e.path], resizePercent)
  }
  // Parameterized facet matchers — shared by the row filter AND the faceted
  // chip counts (each facet is counted with every OTHER facet applied).
  const mRes = (e: TextureEntry, k: string) => !k || resTier(e) === k
  const mPath = (e: TextureEntry, k: string) =>
    !k
    || (k === 'missing' && e.missing)
    || (k === 'absolute' && e.absolute && !e.missing)
    || (k === 'relative' && !e.absolute && !e.missing)
  const mMode = (e: TextureEntry, k: string) => !k || modeOf(e) === k
  const mDepth = (e: TextureEntry, k: number) => !k || depthOf(e) === k
  const mSpace = (e: TextureEntry, k: string) => !k || spaceOf(e) === k
  const byRes = (e: TextureEntry) => mRes(e, resFilter)
  const byPath = (e: TextureEntry) => mPath(e, pathFilter)
  const bySpec = (e: TextureEntry) =>
    mMode(e, modeFilter) && mDepth(e, depthFilter) && mSpace(e, spaceFilter)
  const allTex = tex ? [...tex.absolute, ...tex.relative] : []
  // Faceted counts: how many rows a chip WOULD show given the other active
  // filters — numbers shrink as filters stack, 0 chips gray out.
  const nRes = (k: string) => allTex.filter((e) =>
    mRes(e, k) && byPath(e) && bySpec(e)).length
  const nPath = (k: string) => allTex.filter((e) =>
    byRes(e) && mPath(e, k) && bySpec(e)).length
  const nMode = (k: string) => allTex.filter((e) =>
    byRes(e) && byPath(e) && mMode(e, k) && mDepth(e, depthFilter) && mSpace(e, spaceFilter)).length
  const nDepth = (k: number) => allTex.filter((e) =>
    byRes(e) && byPath(e) && mMode(e, modeFilter) && mDepth(e, k) && mSpace(e, spaceFilter)).length
  const nSpace = (k: string) => allTex.filter((e) =>
    byRes(e) && byPath(e) && mMode(e, modeFilter) && mDepth(e, depthFilter) && mSpace(e, k)).length
  // Distinct bit depths / colorspaces actually present, for the filter chips.
  const depths = [...new Set(allTex.map(depthOf).filter((d): d is number => d != null))].sort((a, b) => a - b)
  const spaces = [...new Set(allTex.map(spaceOf).filter((s): s is string => s != null))].sort()
  const pathPager = usePager(
    // Accepted-as-missing maps drop out of the paths list — they live in the
    // Accepted panel below, like every other area (naming, files, …).
    allTex.filter((e) => !e.accepted && byRes(e) && byPath(e) && bySpec(e)).sort(bySize),
    undefined, [resFilter, pathFilter, modeFilter, depthFilter, spaceFilter].join('|'))

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

  const totalVram = tex?.total_vram ?? 0
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
            {/* Visibility toggle = scope: 'Visible only' lists materials used
                NOWHERE; 'All objects' additionally lists the ones used only
                by hidden objects — same list, fully actionable, badge marks
                them. Materials any visible object uses never show up. */}
            <div className="substats" style={{ marginBottom: 12 }}>
              <span><b>{mat.total}</b> total</span>
              <span className={deletable ? 'warn' : ''}><b>{deletable}</b> unused</span>
              {(mat.only_hidden?.length ?? 0) > 0 && (
                <span><b>{mat.only_hidden?.length}</b> of them only on hidden</span>
              )}
              {acceptedList.length > 0 && <span><b>{acceptedList.length}</b> accepted</span>}
              <span className={mat.missing_textures ? 'warn' : ''}><b>{mat.missing_textures || 0}</b> missing tex</span>
            </div>
            <Workbench
              title="Unused materials" count={deletable} loading={busy}
              empty={
                <>
                  {org.includeHidden
                    ? 'Every material is in use 🎉'
                    : 'Every material is used by a visible object 🎉 (switch to All objects to include hidden usage)'}
                  {missingCount > 0 && (
                    <span className="wb-empty-more">
                      Check the missing texture paths below — {missingCount} still need{missingCount === 1 ? 's' : ''} attention
                      <span className="wb-empty-arrow">↓</span>
                    </span>
                  )}
                </>
              }
              hint="Click a row to select the material in Cinema 4D · ✓ deletes it · = keeps it"
              applyLabel="Delete all" applyTone="danger"
              onApply={() => org.doDeleteAllUnused(deletable)}
              onAcceptAll={() => org.keepAll('materials')}
              busy={busy} progress={org.progress}
            >
              <div className="rename-list">
                {unusedPager.rows.map((nm, i) => {
                  const onHidden = onHiddenSet.has(nm)
                  return (
                    // Names can legitimately repeat (duplicate materials) —
                    // the index keeps React keys unique, no ghost rows.
                    <SuggestionRow key={`${nm}|${i}`} busy={busy}
                      applyTitle={onHidden
                        ? 'Apply — delete this material. Careful: hidden objects still use it and will lose it (undoable)'
                        : 'Apply — delete this material (undoable)'}
                      onApply={() => org.doDeleteMaterial(nm)}
                      onAcceptAsIs={() => org.keep('materials', nm)}
                      onFocus={() => org.doFocusMaterial(nm)}
                    >
                      <MatThumb src={previews[nm]} fallback={onHidden ? 'var(--warn)' : 'var(--dim2)'} />
                      <span className="rn-old" title={nm}>{nm}</span>
                      {onHidden && (
                        <span className="pill unused"
                          title="Used only by objects that are hidden in the editor — deleting removes it from them too">
                          on hidden
                        </span>
                      )}
                      <span className="rn-arrow">→</span>
                      <span className="rn-new dim">delete</span>
                    </SuggestionRow>
                  )
                })}
              </div>
              <Pager pager={unusedPager} />
            </Workbench>
            <AcceptedSection items={mat.accepted_all || []}
              onRestore={(nm) => org.unkeep('materials', nm)}
              onRestoreAll={() => org.unkeepAll('materials')}
              hint="Accepted materials stay in the scene, are remembered (config) and no longer count as problems." />
          </>
        ) : <div className="empty-note">No material data.</div>}
      </section>

      {/* ---- Textures: ONE area — settings/filters left, paths right --- */}
      {tex ? (
        <>
        <SectionIntro title="Textures"
          desc="Every map the scene references — real pixel size, disk size and resolution per texture. Spot oversized maps, fix absolute or missing paths, and shrink maps in place." />
        <div className="workbench">
          {/* Left column: two stacked panels — narrowing the list (Filters)
              and acting on it (Actions) are separate jobs. */}
          <div className="wb-col">
          <aside className="wb-side">
            <h3>Filters</h3>
            <p className="hint-sm">
              Narrow the list — every action below applies to what is left
              (or to the rows you tick). Heaviest map first.
            </p>
            <div className="substats" style={{ marginBottom: 12 }}>
              <span><b>{tex.total}</b> maps</span>
              <span><b>{humanBytes(tex.total_bytes)}</b> on disk</span>
              {totalVram > 0 && (
                <Tip text="Estimated uncompressed memory of all maps combined (width × height × 4 bytes, incl. mipmaps ~1.33×) — what they cost in RAM/VRAM.">
                  <span><b>{humanBytes(totalVram)}</b> VRAM (est.)</span>
                </Tip>
              )}
            </div>

            {/* Facet chips: no "All" entry — an unset facet means all, and
                clicking the active chip toggles it back off. */}
            <div className="section-head sm"><span>Path status</span></div>
            <FilterChips value={pathFilter} empty="" onChange={setPathFilter}
              options={PATH_STATES.map(([key, label]) => ({
                key,
                label,
                count: nPath(key),
                title: `Show only ${label.toLowerCase()} paths`,
                cls: key === 'missing' && nPath(key) > 0 ? 'tf-warn' : undefined,
              }))} />

            <div className="section-head sm"><span>Resolution</span></div>
            <FilterChips value={resFilter} empty="" onChange={setResFilter}
              options={RES_FILTERS.map(([key, label]) => ({
                key, label, count: nRes(key), title: `Show only ${label} textures`,
              }))} />

            <div className="section-head sm">
              <Tip text="Filter by the channel mode from the spec badge (e.g. “RGB 32b linear”). Maps without readable pixel data drop out while a filter is active.">
                <span>Channels</span>
              </Tip>
            </div>
            <FilterChips value={modeFilter} empty="" onChange={setModeFilter}
              options={MODES.map(([key, label]) => ({
                key, label, count: nMode(key), title: `Show only ${label} textures`,
              }))} />

            {depths.length > 1 && (
              <>
                <div className="section-head sm">
                  <Tip text="Filter by bits per channel — 32-bit maps (EXR/HDR) are the memory hogs.">
                    <span>Bit depth</span>
                  </Tip>
                </div>
                <FilterChips value={depthFilter} empty={0} onChange={setDepthFilter}
                  options={depths.map((d) => ({
                    key: d, label: `${d} bit`, count: nDepth(d),
                    title: `Show only ${d}-bit textures`,
                  }))} />
              </>
            )}
            {spaces.length > 1 && (
              <>
                <div className="section-head sm">
                  <Tip text="Filter by the colorspace tag where it is readable from the file (e.g. sRGB, linear).">
                    <span>Colorspace</span>
                  </Tip>
                </div>
                <FilterChips value={spaceFilter} empty="" onChange={setSpaceFilter}
                  options={spaces.map((s) => ({
                    key: s, label: s, count: nSpace(s), title: `Show only ${s} textures`,
                  }))} />
              </>
            )}

          </aside>

          <aside className="wb-side">
            <h3>Actions</h3>
            <p className="hint-sm">
              Each block says what it does before you run it. Every action is a
              single undo step. Path actions cover the whole scene;
              <b> Shrink</b> follows your filter and selection.
            </p>

            {missingCount > 0 && (
              <>
                <div className="section-head sm"><span>Missing files</span></div>

                <div className="side-action">
                  <p className="side-action-title">Find the files again</p>
                  <p className="hint-sm">
                    Pick a folder — it is searched top to bottom for the missing
                    file names, and every match is relinked.
                  </p>
                  <button className="ghost sm" disabled={busy}
                    title="Pick a folder in Cinema 4D — it is searched recursively for the missing file names and every match is relinked (undoable)"
                    onClick={() => {
                      call('pick_folder', { title: 'Folder to search for the missing textures' })
                        .then((r) => { if (r.path) { setRelinkDir(r.path); setRelinkConfirm(true) } })
                        .catch(() => {})
                    }}>
                    Relink {missingCount} missing
                  </button>
                </div>

                <div className="side-action">
                  <p className="side-action-title">Drop the dead links</p>
                  <p className="hint-sm">
                    Blanks the path on every reference whose file is gone. The
                    materials stay — only the broken links go.
                  </p>
                  <button className="ghost sm" disabled={busy}
                    title="Blank the dead path on every reference whose file is missing — the materials stay, the broken references go (undoable)"
                    onClick={() => setClearConfirm(true)}>
                    Clear {missingCount} missing
                  </button>
                </div>

                <div className="side-action">
                  <p className="side-action-title">Live with them</p>
                  <p className="hint-sm">
                    Acknowledges the missing maps: nothing changes in the scene,
                    they just stop counting as problems.
                  </p>
                  <button className="ghost sm"
                    title="Accept every missing map as-is — they stop counting as problems (restore below)"
                    onClick={() => {
                      const add = allTex.filter((e) => e.missing && !e.accepted).map((e) => e.path)
                      setTexKeeps([...texAccepted, ...add])
                    }}>
                    Accept {missingCount} missing
                  </button>
                </div>
              </>
            )}

            <div className="section-head sm"><span>Shrink</span></div>

            <div className="side-action">
              <p className="side-action-title">Size of the shrunk copy</p>
              <p className="hint-sm">
                Sets what the <b>↓ %</b> button on each row writes: a downsized
                <b> copy</b> next to the original (suffix <code>_{resizePercent}</code>),
                with the material relinked to it. The original file is never
                touched.
              </p>
              <div className="chip-row">
                {[25, 50, 75].map((p) => (
                  <button key={p}
                    className={'chip-btn' + (resizePercent === p ? ' on' : '')}
                    title={`Row buttons will write copies at ${p}% of the original size`}
                    onClick={() => setResizePercent(p)}>{p}%</button>
                ))}
              </div>
            </div>

            <div className="section-head sm"><span>Paths</span></div>
            <p className="hint-sm">
              Relative or absolute is a pipeline choice, not a defect — neither
              counts against your score. Flip a single path with the
              <b> → rel</b> / <b>→ abs</b> button on its row.
            </p>

            <div className="side-action">
              <p className="side-action-title">Copy into the project</p>
              <p className="hint-sm">
                Maps that live outside the project folder are copied into the
                subfolder below and relinked relatively — the one action that
                needs a destination, so it stays here.
              </p>
              <label>
                <input className="nl-input" value={collectDir}
                  onChange={(e) => setCollectDir(e.target.value)}
                  title="Project subfolder out-of-project textures are copied into" />
              </label>
              <button className="ghost sm" disabled={busy || !collectable}
                title={collectable
                  ? `Copy ${collectable} texture(s) that live outside the project into “${collectDir || 'tex'}/” and relink relatively`
                  : 'No existing textures outside the project folder'}
                onClick={() => setCollectConfirm(true)}>
                Copy &amp; relink ({collectable})
              </button>
            </div>

            {!tex.doc_path && (
              <p className="hint-sm">Project not saved — paths cannot be made relative yet.</p>
            )}
          </aside>
          </div>

          <div className="wb-preview">
            <div className="wb-preview-head">
              <h3>Paths</h3>
              <span className="wb-count">
                {pathPager.total === 0 ? 'nothing to show'
                  : `${pathPager.total} map${pathPager.total === 1 ? '' : 's'}`}
              </span>
              {/* Batch actions on the missing maps live in the Actions panel. */}
            </div>
            <p className="hint-sm wb-hint">
              Click a row to select its material in Cinema 4D. Decide per map on
              the right: <b>→ rel</b>/<b>→ abs</b> flips its path form,
              <b> ↓ {resizePercent}%</b> writes a smaller copy and relinks it;
              missing maps offer … pick a replacement · ✕ clear · = accept.
            </p>
            <div className="wb-scroll">
              {pathPager.total
                ? <>
                    <TexTable rows={pathPager.rows}
                      previews={texPreviews}
                      resized={resizedInfo} percent={resizePercent} busy={busy}
                      onFocus={org.doFocusMaterial}
                      onPick={(e) => org.doPickTexturePath(e.path, e.material)}
                      onClear={(e) => org.doSetTexturePath(e.path, '', e.material)}
                      onAccept={acceptTexture}
                      onResize={resizeOne}
                      onRepath={(e, mode) => org.doTextureRepath([e.path], mode)} />
                    <Pager pager={pathPager} />
                  </>
                : <div className="empty-note mid">
                    {pathFilter === 'missing' ? 'No missing textures 🎉'
                      : pathFilter === 'absolute' ? 'No absolute texture paths 🎉'
                        : 'No textures match the filters.'}
                  </div>}
            </div>
          </div>
        </div>
        <AcceptedSection items={texAccepted}
          onRestore={(p) => setTexKeeps(texAccepted.filter((a) => a !== p))}
          onRestoreAll={() => setTexKeeps([])}
          hint="Accepted-as-missing textures are remembered (config) and no longer count as problems — restore to treat them as missing again." />
        </>
      ) : (
        <section className="card">
          <div className="card-head"><h3>Textures</h3></div>
          <div className="empty-note">No texture data.</div>
          {report.textures_error && (
            <p className="example warn" style={{ marginTop: 8 }}>
              Texture scan failed: <code>{report.textures_error}</code>
            </p>
          )}
        </section>
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
