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
import Tip from '../components/Tip'
import TabIntro from '../components/TabIntro'
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

// One texture row. Missing rows carry their own decision buttons:
// … browse for a replacement file (opens C4D's native file dialog),
// ✕ clear THIS dead reference.
function TexRow({ e, thumb, selected, resized, onToggle, onFocus, onPick, onClear, onAccept }: {
  e: TextureEntry
  thumb?: string
  selected: boolean
  resized?: ResizeInfo
  onToggle: () => void
  onFocus: (material: string) => void
  onPick?: (e: TextureEntry) => void
  onClear?: (e: TextureEntry) => void
  onAccept?: (e: TextureEntry) => void
}) {
  // Only unaccepted missing maps carry the decision buttons; accepted ones are
  // acknowledged and just show a badge (restore from the panel below).
  const actionable = e.missing && !e.accepted && (onPick || onClear || onAccept)
  const pathTip = `${e.path}${e.resolved && e.resolved !== e.path ? `\n→ ${e.resolved}` : ''}`
  return (
    <>
    <div className={'tex-tr tex-click' + (actionable ? ' tex-actionable' : '') + (selected ? ' tex-sel' : '')
        + (resized ? ' tex-resized' : '')}
      title={`${pathTip}${e.width > 0 ? `\n${specText(e)}` : ''}\nClick to select material “${e.material}” & frame its object`}
      onClick={() => onFocus(e.material)}>
      <input type="checkbox" className="tex-cb" checked={selected}
        title="Select this map for the batch actions on the left (Resize, Make absolute…)"
        onClick={(ev) => ev.stopPropagation()} onChange={onToggle} />
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
        {resized && <span className="tex-badge resized">resized</span>}
      </span>
      <span className="tex-cell-path dim">
        {e.missing
          ? (e.accepted
              ? <span className="tex-badge" title="Accepted as missing — no longer counted as a problem">accepted</span>
              : <span className="tex-badge missing">missing</span>)
          : e.relocatable
            ? <span className="tex-badge fixable">→ relative</span>
            : <span className="tex-badge">{e.absolute ? 'absolute' : 'relative'}</span>}
      </span>
      <span className="num">
        {e.res_tag ? <span className={'tex-badge tex-res ' + resTier(e)}>{e.res_tag}</span> : '—'}
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
      <span className="num" title={e.vram ? `~${humanBytes(e.vram)} VRAM (uncompressed, incl. mipmaps)` : undefined}>
        {e.bytes > 0 ? humanBytes(e.bytes) : '—'}
      </span>
      <span className="dim tex-cut">{e.material}</span>
      {actionable && (
        <span className="rn-actions" onClick={(ev) => ev.stopPropagation()}>
          {onPick && (
            <button className="rn-ok rn-icon" title="Browse — pick the replacement file in Cinema 4D's file dialog (undoable)"
              onClick={() => onPick(e)}><IconFolder /></button>
          )}
          {onClear && (
            <button className="rn-no" title="Clear this dead reference — the material stops pointing at the missing file (undoable)"
              onClick={() => onClear(e)}>✕</button>
          )}
          {onAccept && (
            <button className="rn-keep" title="Accept as-is — acknowledge the missing file; it stops counting as a problem (restore below)"
              onClick={() => onAccept(e)}>=</button>
          )}
        </span>
      )}
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

function TexTable({ rows, previews, selected, rowKey, resized, onToggle, allChecked, onToggleAll, onFocus, onPick, onClear, onAccept }: {
  rows: TextureEntry[]
  previews: Record<string, string>
  selected: Set<string>
  rowKey: (e: TextureEntry) => string
  resized: Record<string, ResizeInfo>
  onToggle: (e: TextureEntry) => void
  allChecked: boolean
  onToggleAll: () => void
  onFocus: (material: string) => void
  onPick?: (e: TextureEntry) => void
  onClear?: (e: TextureEntry) => void
  onAccept?: (e: TextureEntry) => void
}) {
  return (
    <div className="tex-table">
      <div className="tex-tr tex-thead">
        <input type="checkbox" className="tex-cb" checked={allChecked}
          title="Select / deselect every map in the current filter" onChange={onToggleAll} />
        <Tip text="File name of the texture. Click the thumbnail to open the image in your picture viewer."><span>File</span></Tip>
        <Tip text="Badge shows absolute / relative / missing — “→ relative” can be rewritten with one click. Hover a row for its full path."><span>Path</span></Tip>
        <Tip text="Resolution tier (e.g. 4K/8K) — heavy maps stand out instantly."><span className="num">Res</span></Tip>
        <Tip text="Actual pixel dimensions of the file."><span className="num">Pixels</span></Tip>
        <Tip text="File size on disk."><span className="num">Size</span></Tip>
        <Tip text="Material using this texture."><span>Material</span></Tip>
      </div>
      {rows.map((e, i) => (
        <TexRow key={e.path + '|' + e.material + '|' + i} e={e}
          thumb={previews[e.resolved || e.path]}
          selected={selected.has(rowKey(e))} resized={resized[e.path]} onToggle={() => onToggle(e)}
          onFocus={onFocus} onPick={onPick} onClear={onClear} onAccept={onAccept} />
      ))}
    </div>
  )
}

// Resolution filter chips: narrow all three texture sections to one tier.
// No "All" entry — an unset facet means all (chips toggle off on re-click).
const RES_TIERS: [string, string][] = [
  ['res-8k', '8K'], ['res-4k', '4K'], ['res-2k', '2K'], ['res-sm', '< 2K'],
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
  const [confirm, setConfirm] = useState(false)         // make textures relative
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
  // Batch resize + make-absolute (M4): percent choice and confirm gates.
  const [resizePercent, setResizePercent] = useState(50)
  const [resizeConfirm, setResizeConfirm] = useState(false)
  const [absConfirm, setAbsConfirm] = useState(false)
  // Row selection: check maps in the paths list to scope the batch actions
  // (Resize / Make absolute) to just those rows. Empty = act on the whole
  // filtered set, as before. Keyed by path+material so it survives paging.
  const rowKey = (e: TextureEntry) => e.path + '\n' + e.material
  const [selected, setSelected] = useState<Set<string>>(new Set())
  // Recently resized maps, keyed by the relinked copy's path — annotates that
  // row with a "resized" badge + a note showing what it replaced.
  const [resizedInfo, setResizedInfo] = useState<Record<string, ResizeInfo>>({})
  // Accepted-as-missing textures (persisted in config under the 'textures' keep
  // section); accepting one drops it out of the missing count + score.
  const texAccepted = tex?.accepted_all || []
  const setTexKeeps = (keys: string[]) => {
    call('set_keeps', { section: 'textures', keys })
      .then(() => org.doAnalyze())
      .catch(() => { /* next analyze reconciles */ })
  }
  const acceptTexture = (e: TextureEntry) => setTexKeeps([...texAccepted, e.path])
  const toggleRow = (e: TextureEntry) => setSelected((s) => {
    const next = new Set(s); const k = rowKey(e)
    next.has(k) ? next.delete(k) : next.add(k)
    return next
  })
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

  // Selection scoping: when the user has ticked rows, the path-array batch
  // actions (Resize / Make absolute) act on exactly those maps. With nothing
  // ticked they fall back to the whole filtered set (the previous behavior).
  const filteredTex = allTex.filter((e) => !e.accepted && byRes(e) && byPath(e) && bySpec(e))
  const selActive = selected.size > 0
  const selEntries = allTex.filter((e) => selected.has(rowKey(e)))
  const selScope = selActive ? selEntries : filteredTex
  // How many of the CURRENT filter are ticked — drives the header checkbox.
  const filteredSelCount = filteredTex.filter((e) => selected.has(rowKey(e))).length
  const allFilteredChecked = filteredTex.length > 0 && filteredSelCount === filteredTex.length
  const toggleAll = () => setSelected((s) => {
    const next = new Set(s)
    if (allFilteredChecked) filteredTex.forEach((e) => next.delete(rowKey(e)))
    else filteredTex.forEach((e) => next.add(rowKey(e)))
    return next
  })

  // Make-absolute counterpart to Fix paths: relative references that resolve
  // to an existing file. Batch resize operates on maps that exist on disk and
  // carry pixel data. Both honor the row selection when one is active.
  const makeAbsolute = selScope.filter((e) => !e.absolute && !e.missing)
  const resizeTargets = selScope.filter((e) => e.exists && e.width > 0)
  const totalVram = tex?.total_vram ?? 0
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
              applyLabel="Delete all"
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
                        <span className="tex-badge unused"
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
        ) : <div className="fl-empty">No material data.</div>}
      </section>

      {/* ---- Textures: ONE area — settings/filters left, paths right --- */}
      {tex ? (
        <>
        <TabIntro title="Textures"
          desc="Every map the scene references — real pixel size, disk size and resolution per texture. Spot oversized maps, fix absolute or missing paths, and shrink maps in place." />
        <div className="workbench">
          <aside className="wb-side">
            <h3>Filters</h3>
            <p className="hint-sm">
              Real pixel size, disk size and a resolution tag per map — spot the
              8K textures eating memory that could be 4K, and the paths that
              break when the project moves. Heaviest first.
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
            <div className="rule-group-head"><span>Path status</span></div>
            <div className="tex-filter tex-filter-col">
              {([['absolute', 'Absolute'],
                ['relative', 'Relative'],
                ['missing', 'Missing'],
              ] as [string, string][]).map(([key, label]) => {
                const n = nPath(key)
                const on = pathFilter === key
                const off = n === 0 && !on
                return (
                  <button key={key} disabled={off}
                    className={'tex-filter-btn' + (on ? ' on' : '')
                      + (key === 'missing' && n > 0 ? ' tf-warn' : '')}
                    title={off ? 'No matches with the current filters'
                      : on ? 'Click again to clear this filter'
                        : `Show only ${label.toLowerCase()} paths`}
                    onClick={() => setPathFilter(on ? '' : key)}>
                    {label} <em>{n}</em>
                  </button>
                )
              })}
            </div>

            <div className="rule-group-head"><span>Resolution</span></div>
            <div className="tex-filter tex-filter-col">
              {RES_TIERS.map(([key, label]) => {
                const n = nRes(key)
                const on = resFilter === key
                const off = n === 0 && !on
                return (
                  <button key={key} disabled={off}
                    className={'tex-filter-btn' + (on ? ' on' : '')}
                    title={off ? 'No matches with the current filters'
                      : on ? 'Click again to clear this filter'
                        : `Show only ${label} textures`}
                    onClick={() => setResFilter(on ? '' : key)}>
                    {label} <em>{n}</em>
                  </button>
                )
              })}
            </div>

            <div className="rule-group-head">
              <Tip text="Filter by the channel mode from the spec badge (e.g. “RGB 32b linear”). Maps without readable pixel data drop out while a filter is active.">
                <span>Channels</span>
              </Tip>
            </div>
            <div className="tex-filter tex-filter-col">
              {([['rgb', 'RGB'],
                ['rgba', 'RGBA'],
                ['grey', 'Greyscale'],
              ] as [string, string][]).map(([key, label]) => {
                const n = nMode(key)
                const on = modeFilter === key
                const off = n === 0 && !on
                return (
                  <button key={key} disabled={off}
                    className={'tex-filter-btn' + (on ? ' on' : '')}
                    title={off ? 'No matches with the current filters'
                      : on ? 'Click again to clear this filter'
                        : `Show only ${label} textures`}
                    onClick={() => setModeFilter(on ? '' : key)}>
                    {label} <em>{n}</em>
                  </button>
                )
              })}
            </div>
            {depths.length > 1 && (
              <div className="rule-group-head">
                <Tip text="Filter by bits per channel — 32-bit maps (EXR/HDR) are the memory hogs.">
                  <span>Bit depth</span>
                </Tip>
              </div>
            )}
            {depths.length > 1 && (
              <div className="tex-filter tex-filter-col">
                {depths.map((d) => {
                  const n = nDepth(d)
                  const on = depthFilter === d
                  const off = n === 0 && !on
                  return (
                    <button key={d} disabled={off}
                      className={'tex-filter-btn' + (on ? ' on' : '')}
                      title={off ? 'No matches with the current filters'
                        : on ? 'Click again to clear this filter'
                          : `Show only ${d}-bit textures`}
                      onClick={() => setDepthFilter(on ? 0 : d)}>
                      {d} bit <em>{n}</em>
                    </button>
                  )
                })}
              </div>
            )}
            {spaces.length > 1 && (
              <div className="rule-group-head">
                <Tip text="Filter by the colorspace tag where it is readable from the file (e.g. sRGB, linear).">
                  <span>Colorspace</span>
                </Tip>
              </div>
            )}
            {spaces.length > 1 && (
              <div className="tex-filter tex-filter-col">
                {spaces.map((s) => {
                  const n = nSpace(s)
                  const on = spaceFilter === s
                  const off = n === 0 && !on
                  return (
                    <button key={s} disabled={off}
                      className={'tex-filter-btn' + (on ? ' on' : '')}
                      title={off ? 'No matches with the current filters'
                        : on ? 'Click again to clear this filter'
                          : `Show only ${s} textures`}
                      onClick={() => setSpaceFilter(on ? '' : s)}>
                      {s} <em>{n}</em>
                    </button>
                  )
                })}
              </div>
            )}

            <div className="rule-group-head"><span>Paths</span></div>
            <button className="ghost sm" disabled={busy || !fixable}
              title={fixable
                ? `Rewrite ${fixable} absolute path(s) inside the project folder to relative (undoable)`
                : 'No absolute paths inside the project folder'}
              onClick={() => setConfirm(true)}>
              Fix paths ({fixable})
            </button>
            <p className="hint-sm" style={{ marginTop: 4 }}>
              Rewrite absolute paths that already point into the project to relative.
            </p>
            <button className="ghost sm" disabled={busy || !collectable}
              title={collectable
                ? `Copy ${collectable} texture(s) that live outside the project into “${collectDir || 'tex'}/” and relink relatively`
                : 'No existing textures outside the project folder'}
              onClick={() => setCollectConfirm(true)}>
              Copy &amp; relink ({collectable})
            </button>
            <label style={{ marginTop: 4 }}>
              <input className="nl-input" value={collectDir}
                onChange={(e) => setCollectDir(e.target.value)}
                title="Project subfolder out-of-project textures are copied into" />
            </label>
            <p className="hint-sm" style={{ marginTop: 4 }}>
              Copy out-of-project files into the folder above, then relink relatively.
            </p>
            <button className="ghost sm" disabled={busy || !makeAbsolute.length}
              title={makeAbsolute.length
                ? `Rewrite ${makeAbsolute.length} relative path(s) to their full absolute form (undoable)`
                : 'No relative texture paths to make absolute'}
              onClick={() => setAbsConfirm(true)}>
              Make absolute ({makeAbsolute.length})
            </button>
            <p className="hint-sm" style={{ marginTop: 4 }}>
              Rewrite relative paths to their full absolute form.
            </p>

            <div className="rule-group-head"><span>Shrink</span></div>
            <div className="tex-filter" style={{ marginBottom: 8 }}>
              {[25, 50, 75].map((p) => (
                <button key={p}
                  className={'tex-filter-btn' + (resizePercent === p ? ' on' : '')}
                  onClick={() => setResizePercent(p)}>{p}%</button>
              ))}
            </div>
            <button className="ghost sm" disabled={busy || !resizeTargets.length}
              title={resizeTargets.length
                ? `Resize ${resizeTargets.length} texture(s) to ${resizePercent}% (copies + relink, undoable)`
                : selActive ? 'No selected maps with pixel data' : 'No textures with pixel data in the current filter'}
              onClick={() => setResizeConfirm(true)}>
              Resize {resizeTargets.length} → {resizePercent}%
            </button>
            <p className="hint-sm" style={{ marginTop: 4 }}>
              Writes downsized <b>copies</b> next to the originals (suffix
              <code> _{resizePercent}</code>) and relinks the materials —
              applies to {selActive ? <b>the {selected.size} selected maps</b> : 'the currently filtered maps'}.
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
              {selActive && (
                <button className="wb-accept-all" title="Clear the selection"
                  onClick={() => setSelected(new Set())}>
                  {selected.size} selected · clear ✕
                </button>
              )}
              {missingCount > 0 && (
                <>
                  <button className="wb-accept-all" disabled={busy}
                    title="Pick a folder in Cinema 4D — it is searched recursively for the missing file names and every match is relinked (undoable)"
                    onClick={() => {
                      call('pick_folder', { title: 'Folder to search for the missing textures' })
                        .then((r) => { if (r.path) { setRelinkDir(r.path); setRelinkConfirm(true) } })
                        .catch(() => {})
                    }}>
                    <IconFolder /> Relink {missingCount} missing
                  </button>
                  <button className="wb-accept-all" disabled={busy}
                    title="Blank the dead path on every reference whose file is missing — the materials stay, the broken references go (undoable)"
                    onClick={() => setClearConfirm(true)}>
                    ✕ Clear {missingCount} missing
                  </button>
                  <button className="wb-accept-all"
                    title="Accept every missing map as-is — they stop counting as problems (restore below)"
                    onClick={() => {
                      const add = allTex.filter((e) => e.missing && !e.accepted).map((e) => e.path)
                      setTexKeeps([...texAccepted, ...add])
                    }}>
                    = Accept {missingCount} missing
                  </button>
                </>
              )}
            </div>
            <p className="hint-sm wb-hint">Click a row to select its material in Cinema 4D · missing rows: … pick the replacement file · ✕ clear the dead reference.</p>
            <div className="wb-scroll">
              {pathPager.total
                ? <>
                    <TexTable rows={pathPager.rows}
                      previews={texPreviews}
                      selected={selected} rowKey={rowKey} onToggle={toggleRow}
                      resized={resizedInfo}
                      allChecked={allFilteredChecked} onToggleAll={toggleAll}
                      onFocus={org.doFocusMaterial}
                      onPick={(e) => org.doPickTexturePath(e.path, e.material)}
                      onClear={(e) => org.doSetTexturePath(e.path, '', e.material)}
                      onAccept={acceptTexture} />
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
        <AcceptedSection items={texAccepted}
          onRestore={(p) => setTexKeeps(texAccepted.filter((a) => a !== p))}
          onRestoreAll={() => setTexKeeps([])}
          hint="Accepted-as-missing textures are remembered (config) and no longer count as problems — restore to treat them as missing again." />
        </>
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
      {absConfirm && (
        <ConfirmModal
          title="Make paths absolute"
          message={`Rewrite ${makeAbsolute.length} relative texture path${makeAbsolute.length === 1 ? '' : 's'} to their full absolute form (one undo step). Continue?`}
          confirmLabel={`✓ Make ${makeAbsolute.length} absolute`}
          onConfirm={() => { setAbsConfirm(false); org.doTextureRepath(makeAbsolute.map((e) => e.path), 'absolute') }}
          onCancel={() => setAbsConfirm(false)}
        />
      )}
      {resizeConfirm && (
        <ConfirmModal
          title={`Resize ${resizeTargets.length} texture${resizeTargets.length === 1 ? '' : 's'} to ${resizePercent}%`}
          message={`Write resized copies (suffix _${resizePercent}) of ${resizeTargets.length} texture${resizeTargets.length === 1 ? '' : 's'} next to the originals and relink the materials to them. The original files are never overwritten; the relink is one undo step. Formats without a resizer are skipped with a note. Continue?`}
          confirmLabel={`✓ Resize to ${resizePercent}%`}
          onConfirm={() => {
            setResizeConfirm(false)
            // Remember what each map is being resized from, keyed by the copy's
            // predicted path, so the relinked row shows the swap after re-analyze.
            const map: Record<string, ResizeInfo> = { ...resizedInfo }
            for (const e of resizeTargets) {
              map[resizeTargetPath(e.path, resizePercent)] =
                { fromFile: e.file, fromDims: `${e.width}×${e.height}`, percent: resizePercent }
            }
            setResizedInfo(map)
            setSelected(new Set())
            org.doTextureResize(resizeTargets.map((e) => e.path), resizePercent)
          }}
          onCancel={() => setResizeConfirm(false)}
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
