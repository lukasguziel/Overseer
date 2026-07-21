// The Textures area of the Materials tab: every map the scene references,
// faceted filters left, the decide-per-row table right. Extracted from
// MaterialsTab so each of the tab's two areas can be read in one piece.
import { useEffect, useMemo, useRef, useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import type { TextureEntry } from '../types'
import { plural, humanBytes } from '../lib/format'
import { RES_BUCKETS, resBucket, statusDot } from '../lib/colors'
import { rowButton } from '../lib/rowButton'
import Pager, { usePager } from '../components/Pager'
import ConfirmModal from '../components/ConfirmModal'
import ShrinkModal from '../components/ShrinkModal'
import CollectModal from '../components/CollectModal'
import ResizeNote from '../components/ResizeNote'
import ActionButton from '../components/ActionButton'
import FilterChips from '../components/FilterChips'
import Tip from '../components/Tip'
import SectionIntro from '../components/SectionIntro'
import { IconCheck, IconCollect, IconFolder, IconShrink } from '../components/icons'
import './materials.css'

// Resolution pill class — the coarse RES_BUCKETS of lib/colors, so the
// thresholds can never drift from the treemap's tiers.
const resTier = (e: TextureEntry): string => resBucket(Math.max(e.width, e.height))

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
// Texture table: fixed grid columns so file / path / res / pixels / size /
// material line up cleanly; long names and paths get ellipsis-truncated.
// Rows are clickable: they select the material in C4D and frame the first
// object carrying it.
function TexRow({ e, thumb, resized, busy, onFocus, onPick, onClear, onAccept, onResize, onRepath, onCollect }: {
  e: TextureEntry
  thumb?: string
  resized?: ResizeInfo
  busy?: boolean
  onFocus: (material: string) => void
  onPick?: (e: TextureEntry) => void
  onClear?: (e: TextureEntry) => void
  onAccept?: (e: TextureEntry) => void
  onResize?: (e: TextureEntry) => void
  onRepath?: (e: TextureEntry, mode: 'relative' | 'absolute') => void
  onCollect?: (e: TextureEntry) => void
}) {
  // Missing maps: pick / clear / accept (accepted ones are decided — badge only).
  const missingActions = e.missing && !e.accepted && (onPick || onClear || onAccept)
  // Present maps: shrink (needs real pixels on disk) and flip the path form.
  const canResize = !e.missing && e.exists && e.width > 0 && onResize
  // The path action exists for ONE case: an absolute path that could just as
  // well be project-relative (`relocatable` = the file lives under the project
  // folder). A path that is already relative has nothing to offer — and an
  // absolute path to a library elsewhere has no relative form at all, so the
  // button would promise what it cannot do. Both get no button.
  const canRepath = !e.missing && e.exists && e.absolute && e.relocatable && !!onRepath
  // The complement of canRepath: an absolute path with NO relative form —
  // the file must be copied into the project first (per-row Copy & relink).
  const canCollect = !e.missing && e.exists && e.absolute && !e.relocatable && !!onCollect
  const actionable = missingActions || canResize || canRepath || canCollect
  const pathTip = `${e.path}${e.resolved && e.resolved !== e.path ? `\n→ ${e.resolved}` : ''}`
  return (
    <>
    <div className={'dg-tr cols-tex dg-click' + (actionable ? ' dg-actionable' : '')
        + (resized ? ' tex-resized' : '')}
      title={`${pathTip}${e.width > 0 ? `\n${specText(e)}` : ''}\nClick to select material “${e.material}” & frame its object`}
      onClick={() => onFocus(e.material)}
      {...rowButton(() => onFocus(e.material))}>
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
          : <span className="fl-dot" style={{ background: statusDot(e.missing) }} />}
        <span className="dg-cut">{e.file}</span>
        {!e.used && <span className="pill unused">unused</span>}
        {resized && <span className="pill resized">resized</span>}
      </span>
      <span className="dim dg-cut">{e.material}</span>
      {/* The badge states WHAT THE PATH IS — never what it could become. The
          old "→ relative" on a relocatable path read as "this is relative"
          while the filter counted it (correctly) as absolute. The offer to
          rewrite it lives in the row's "→ rel" button, where it belongs. */}
      <span className="dg-cell-path dim">
        {e.missing
          ? (e.accepted
              ? <span className="pill" title="Accepted as missing — no longer counted as a problem">accepted</span>
              : <span className="pill missing">missing</span>)
          : e.absolute
            ? <span className={'pill' + (e.relocatable ? ' fixable' : '')}
                title={e.relocatable
                  ? `Absolute, but the file lives under the project folder — “→ rel” rewrites it to ${e.rel_target || 'a project-relative path'}`
                  : 'Absolute path to a file outside the project folder'}>absolute</span>
            : <span className="pill" title="Relative to the project folder">relative</span>}
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
              onClick={() => onAccept(e)}><IconCheck /></button>
          )}
          {canResize && (
            <button className="rn-keep tex-act" disabled={busy}
              title={`Shrink this map (${e.width}×${e.height}) — pick the size in the next step`}
              onClick={() => onResize!(e)}>
              <IconShrink />
            </button>
          )}
          {canCollect && (
            <button className="rn-keep tex-act" disabled={busy}
              title="Copy this file into the project and relink every material using it — destination and materials shown in the next step (relink undoable)"
              onClick={() => onCollect!(e)}>
              <IconCollect />
            </button>
          )}
          {canRepath && (
            <button className="rn-keep tex-chip" disabled={busy}
              title={`Rewrite this path relative to the project folder: ${e.rel_target || 'project-relative'} (undoable)`}
              onClick={() => onRepath!(e, 'relative')}>
              → rel
            </button>
          )}
          </>
        )}
      </span>
    </div>
    {resized && (() => {
      const [fw, fh] = resized.fromDims.split('×').map((n) => parseInt(n, 10) || 0)
      return <ResizeNote fromW={fw} fromH={fh} toW={e.width} toH={e.height}
        file={resized.fromFile} />
    })()}
    </>
  )
}

function TexTable({ rows, previews, resized, busy, onFocus, onPick, onClear, onAccept, onResize, onRepath, onCollect }: {
  rows: TextureEntry[]
  previews: Record<string, string>
  resized: Record<string, ResizeInfo>
  busy?: boolean
  onFocus: (material: string) => void
  onPick?: (e: TextureEntry) => void
  onClear?: (e: TextureEntry) => void
  onAccept?: (e: TextureEntry) => void
  onResize?: (e: TextureEntry) => void
  onRepath?: (e: TextureEntry, mode: 'relative' | 'absolute') => void
  onCollect?: (e: TextureEntry) => void
}) {
  return (
    <div className="dg-table">
      <div className="dg-tr dg-thead cols-tex">
        <Tip text="File name of the texture. Click the thumbnail to open the image in your picture viewer."><span>File</span></Tip>
        <Tip text="Material using this texture."><span>Material</span></Tip>
        <Tip text="Badge shows absolute / relative / missing. Decide per row on the right: flip the path form, shrink the map, or fix a missing reference. Hover a row for its full path."><span>Path</span></Tip>
        <Tip text="Resolution tier (e.g. 4K/8K) — heavy maps stand out instantly."><span className="num">Res</span></Tip>
        <Tip text="Actual pixel dimensions of the file."><span className="num">Pixels</span></Tip>
        <Tip text="File size on disk."><span className="num">Size</span></Tip>
        <Tip text="What you can do with this map: shrink it, make its path relative, copy it into the project, or fix a missing reference."><span>Actions</span></Tip>
      </div>
      {rows.map((e, i) => (
        <TexRow key={e.path + '|' + e.material + '|' + i} e={e}
          thumb={previews[e.resolved || e.path]} busy={busy}
          resized={resized[e.path]}
          onFocus={onFocus} onPick={onPick} onClear={onClear} onAccept={onAccept}
          onResize={onResize} onRepath={onRepath} onCollect={onCollect} />
      ))}
    </div>
  )
}

// Facet vocabularies for the filter chips (order = display order).
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
const pathStateOf = (e: TextureEntry): string =>
  e.missing ? 'missing' : e.absolute ? 'absolute' : 'relative'

export default function TexturesSection({ org }: { org: Organizer }) {
  const { report, busy } = org
  const tex = report?.textures

  // ONE paths list, narrowed by the search box and the facet chips in the
  // settings panel (resolution tier, path status, spec).
  const [query, setQuery] = useState('')
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
  // Per-row Copy & relink: the ONE texture being collected + the materials
  // its relink will touch (null while the lookup request is in flight).
  const [collectOne, setCollectOne] = useState<TextureEntry | null>(null)
  const [collectOneMats, setCollectOneMats] = useState<string[] | null>(null)
  const openCollectOne = (e: TextureEntry) => {
    setCollectOne(e)
    setCollectOneMats(null)
    call('texture_owners', { path: e.path })
      .then((r) => setCollectOneMats(r.materials || []))
      .catch(() => setCollectOneMats([e.material]))
  }
  // Missing-texture actions: relink from a search folder / clear dead refs.
  const [relinkDir, setRelinkDir] = useState('')
  const [relinkConfirm, setRelinkConfirm] = useState(false)
  const [clearConfirm, setClearConfirm] = useState(false)
  // The map whose shrink dialog is open (null = none). The size is picked in
  // the dialog, so the row button carries an icon and no number.
  const [shrink, setShrink] = useState<TextureEntry | null>(null)
  // Recently resized maps, keyed by the relinked copy's path — annotates that
  // row with a "resized" badge + a note showing what it replaced.
  const [resizedInfo, setResizedInfo] = useState<Record<string, ResizeInfo>>({})
  // Accepted-as-missing textures (persisted in config under the 'textures' keep
  // section); accepting one drops it out of the missing count + score.
  const texAccepted = tex?.accepted_all || []
  const setTexKeeps = (keys: string[]) => {
    call('set_keeps', { section: 'textures', keys })
      .then(() => org.doAnalyze())
      .catch((e) => { org.setError(String(e.message || e)); org.setStatus('Accept ✗') })
  }
  const acceptTexture = (e: TextureEntry) => setTexKeeps([...texAccepted, e.path])
  // Shrink ONE map at the size chosen in the dialog. The copy's path is
  // predictable, so the row it will become after the re-analyze is annotated
  // up front with what it replaced.
  const resizeOne = (e: TextureEntry, percent: number) => {
    setResizedInfo((prev) => ({
      ...prev,
      [resizeTargetPath(e.path, percent)]: {
        fromFile: e.file,
        fromDims: `${e.width}×${e.height}`,
        percent,
      },
    }))
    org.doTextureResize([e.path], percent)
  }

  const allTex = useMemo(
    () => tex ? [...tex.absolute, ...tex.relative] : [], [tex])
  // THE list the chips describe. Accepted-as-missing maps are decided: they
  // live in the Accepted panel below, not in the worklist. The search narrows
  // this base too, so the chip counts always describe what a click would show.
  // Every faceted count must be taken over exactly THIS set — counting the
  // accepted ones is what produced a "missing 31" chip opening an empty list.
  const q = query.trim().toLowerCase()
  const listable = useMemo(() => allTex.filter((e) => !e.accepted
    && (!q || e.file.toLowerCase().includes(q)
      || e.material.toLowerCase().includes(q)
      || e.path.toLowerCase().includes(q))), [allTex, q])

  // Faceted counts in ONE pass: how many rows a chip WOULD show given the
  // other active filters — numbers shrink as filters stack, 0 chips gray out.
  // Each facet family is counted with every OTHER family's filter applied.
  const counts = useMemo(() => {
    const res: Record<string, number> = {}
    const path: Record<string, number> = {}
    const mode: Record<string, number> = {}
    const depth: Record<number, number> = {}
    const space: Record<string, number> = {}
    for (const e of listable) {
      const eRes = resTier(e)
      const eMode = modeOf(e)
      const eDepth = depthOf(e)
      const eSpace = spaceOf(e)
      const okRes = !resFilter || eRes === resFilter
      const okPath = !pathFilter || pathStateOf(e) === pathFilter
      const okMode = !modeFilter || eMode === modeFilter
      const okDepth = !depthFilter || eDepth === depthFilter
      const okSpace = !spaceFilter || eSpace === spaceFilter
      const okSpec = okMode && okDepth && okSpace
      if (okPath && okSpec) res[eRes] = (res[eRes] || 0) + 1
      if (okRes && okSpec) { const k = pathStateOf(e); path[k] = (path[k] || 0) + 1 }
      if (okRes && okPath && okDepth && okSpace && eMode) mode[eMode] = (mode[eMode] || 0) + 1
      if (okRes && okPath && okMode && okSpace && eDepth != null) depth[eDepth] = (depth[eDepth] || 0) + 1
      if (okRes && okPath && okMode && okDepth && eSpace != null) space[eSpace] = (space[eSpace] || 0) + 1
    }
    return { res, path, mode, depth, space }
  }, [listable, resFilter, pathFilter, modeFilter, depthFilter, spaceFilter])

  // Distinct bit depths / colorspaces actually present, for the filter chips.
  const depths = useMemo(() => [...new Set(listable.map(depthOf)
    .filter((d): d is number => d != null))].sort((a, b) => a - b), [listable])
  const spaces = useMemo(() => [...new Set(listable.map(spaceOf)
    .filter((s): s is string => s != null))].sort(), [listable])

  const filteredRows = useMemo(() => listable.filter((e) =>
    (!resFilter || resTier(e) === resFilter)
    && (!pathFilter || pathStateOf(e) === pathFilter)
    && (!modeFilter || modeOf(e) === modeFilter)
    && (!depthFilter || depthOf(e) === depthFilter)
    && (!spaceFilter || spaceOf(e) === spaceFilter)).sort(bySize),
  [listable, resFilter, pathFilter, modeFilter, depthFilter, spaceFilter])
  const pathPager = usePager(filteredRows, undefined,
    [q, resFilter, pathFilter, modeFilter, depthFilter, spaceFilter].join('|'))

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
  // One chunk chain at a time: a filter click changes the visible set faster
  // than thumbnails render, and an in-flight request cannot be cancelled —
  // without this gate, rapid clicking stacks preview jobs in the C4D
  // main-thread queue until Cinema visibly freezes.
  const texChain = useRef<Promise<void> | null>(null)
  useEffect(() => {
    const paths = visibleKey ? visibleKey.split('\n') : []
    const missing = paths.filter((p) => !(p in texPreviews))
    if (!missing.length) return
    let alive = true
    // Debounced: fetch only once the view has settled — clicking through
    // filters must cost nothing until the user stops on one.
    const t = setTimeout(async () => {
      await texChain.current  // let the previous chain drain fully
      if (!alive) return
      texChain.current = (async () => {
        // 4 per request: common formats are answered off the C4D main
        // thread (Pillow in the bridge), but EXR/HDR still block it ~1s
        // each — small blocks keep the embedded view responsive.
        for (let i = 0; i < missing.length && alive; i += 4) {
          try {
            const r = await call('texture_previews', { paths: missing.slice(i, i + 4), size: 40 })
            if (alive) setTexPreviews((prev) => ({ ...prev, ...(r.previews || {}) }))
          } catch { /* dots stay as fallback */ }
        }
      })()
      await texChain.current
    }, 350)
    return () => { alive = false; clearTimeout(t) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleKey])

  if (!tex) {
    return (
      <section className="card">
        <div className="card-head"><h3>Textures</h3></div>
        <div className="empty-note">No texture data.</div>
        {report?.textures_error && (
          <p className="example warn" style={{ marginTop: 8 }}>
            Texture scan failed: <code>{report.textures_error}</code>
          </p>
        )}
      </section>
    )
  }

  const totalVram = tex.total_vram ?? 0
  // Absolute textures OUTSIDE the project: rewriting alone cannot fix them —
  // the file must be copied into the project first (Copy & relink).
  const collectable = allTex.filter((e) => e.absolute && !e.missing && !e.relocatable).length
  const missingCount = tex.missing_count ?? 0

  return (
    <>
      <SectionIntro title="Textures" doc="mat-textures"
        desc="Every map the scene references — real pixel size, disk size and resolution per texture. Spot oversized maps, fix absolute or missing paths, and shrink maps in place." />
      <div className="workbench">
        <aside className="wb-side">
          <h3>Filters</h3>
          <p className="hint-sm">
            Narrow the list. Every map is then decided on its own row — the
            buttons on the right. Heaviest map first.
          </p>
          <input className="search" placeholder="Search file, material or path…"
            value={query} onChange={(e) => setQuery(e.target.value)} />
          {/* No map COUNT here: the list header already says how many rows
              it shows, and this number counted the accepted ones too — two
              different totals under the same word ("114 maps" vs "88 maps"). */}
          <div className="substats">
            <span><b>{humanBytes(tex.total_bytes)}</b> on disk</span>
            {totalVram > 0 && (
              <Tip text="Estimated uncompressed memory of all maps combined (width × height × 4 bytes, incl. mipmaps ~1.33×) — what they cost in RAM/VRAM.">
                <span><b>{humanBytes(totalVram)}</b> VRAM (est.)</span>
              </Tip>
            )}
          </div>

          <FilterChips label="Path status" value={pathFilter} empty="" onChange={setPathFilter}
            options={PATH_STATES.map(([key, label]) => ({
              key,
              label,
              count: counts.path[key] || 0,
              title: `Show only ${label.toLowerCase()} paths`,
              cls: key === 'missing' && (counts.path[key] || 0) > 0 ? 'tf-warn' : undefined,
            }))} />

          <FilterChips label="Resolution" value={resFilter} empty="" onChange={setResFilter}
            options={RES_BUCKETS.map(({ key, label }) => ({
              key, label, count: counts.res[key] || 0, title: `Show only ${label} textures`,
            }))} />

          <FilterChips label="Channels" value={modeFilter} empty="" onChange={setModeFilter}
            tip="Filter by the channel mode from the spec badge (e.g. “RGB 32b linear”). Maps without readable pixel data drop out while a filter is active."
            options={MODES.map(([key, label]) => ({
              key, label, count: counts.mode[key] || 0, title: `Show only ${label} textures`,
            }))} />

          {depths.length > 1 && (
            <FilterChips label="Bit depth" value={depthFilter} empty={0} onChange={setDepthFilter}
              tip="Filter by bits per channel — 32-bit maps (EXR/HDR) are the memory hogs."
              options={depths.map((d) => ({
                key: d, label: `${d} bit`, count: counts.depth[d] || 0,
                title: `Show only ${d}-bit textures`,
              }))} />
          )}
          {spaces.length > 1 && (
            <FilterChips label="Colorspace" value={spaceFilter} empty="" onChange={setSpaceFilter}
              tip="Filter by the colorspace tag where it is readable from the file (e.g. sRGB, linear)."
              options={spaces.map((s) => ({
                key: s, label: s, count: counts.space[s] || 0, title: `Show only ${s} textures`,
              }))} />
          )}
        </aside>

        <div className="wb-preview">
          <div className="wb-preview-head">
            <h3>Maps</h3>
            <span className="head-count">
              {pathPager.total === 0 ? 'nothing to show'
                : `${plural(pathPager.total, 'map')}`}
            </span>
            {/* The two actions that CANNOT be a row decision: they need a
                folder, not a map. Everything else is decided per row. */}
            <span className="wb-head-actions">
              {collectable > 0 && (
                <ActionButton tone="go" disabled={busy}
                  title={`Copy the ${collectable} texture(s) living outside the project into it and relink relatively`}
                  onClick={() => setCollectConfirm(true)}>
                  Copy &amp; relink {collectable}
                </ActionButton>
              )}
              {missingCount > 0 && (
                <ActionButton tone="go" disabled={busy}
                  title="Pick a folder in Cinema 4D — it is searched recursively for the missing file names and every match is relinked (undoable)"
                  onClick={() => {
                    call('pick_folder', { title: 'Folder to search for the missing textures' })
                      .then((r) => { if (r.path) { setRelinkDir(r.path); setRelinkConfirm(true) } })
                      .catch(() => {})
                  }}>
                  Relink {missingCount} missing
                </ActionButton>
              )}
              {missingCount > 0 && (
                <ActionButton tone="danger" disabled={busy}
                  title="Blank the dead path on every reference whose file is missing — the materials stay, the broken references go (undoable)"
                  onClick={() => setClearConfirm(true)}>
                  Clear {missingCount} missing
                </ActionButton>
              )}
              {missingCount > 0 && (
                <ActionButton disabled={busy}
                  title="Accept every missing map as-is — they stop counting as problems (restore below)"
                  onClick={() => {
                    const add = allTex.filter((e) => e.missing && !e.accepted).map((e) => e.path)
                    setTexKeeps([...texAccepted, ...add])
                  }}>
                  Accept {missingCount} missing
                </ActionButton>
              )}
            </span>
          </div>
          <p className="hint-sm wb-hint">
            Click a row to select its material in Cinema 4D. Decide per map on
            the right: the shrink icon writes a smaller copy (you pick the
            size), the folder-arrow icon copies an outside file into the
            project and relinks it, <b>→ rel</b> makes an in-project path
            relative; missing maps offer the folder icon to pick a
            replacement · ✕ clear · the grey ✓ accepts.
          </p>
          <div className="wb-scroll">
            {pathPager.total
              ? <>
                  <TexTable rows={pathPager.rows}
                    previews={texPreviews}
                    resized={resizedInfo} busy={busy}
                    onFocus={org.doFocusMaterial}
                    onPick={(e) => org.doPickTexturePath(e.path, e.material)}
                    onClear={(e) => org.doSetTexturePath(e.path, '', e.material)}
                    onAccept={acceptTexture}
                    onResize={(e) => setShrink(e)}
                    onRepath={(e, mode) => org.doTextureRepath([e.path], mode)}
                    onCollect={openCollectOne} />
                  <Pager pager={pathPager} />
                </>
              : <div className="empty-note mid">
                  {/* An empty list with accepted maps behind it is NOT "none
                      found" — say where they went, or the count and the list
                      look like they disagree. */}
                  {q ? 'No textures match the search.'
                    : pathFilter === 'missing'
                      ? (texAccepted.length > 0
                          ? `No missing textures left to decide — ${texAccepted.length} accepted as missing (restore them below).`
                          : 'No missing textures')
                      : pathFilter === 'absolute' ? 'No absolute texture paths'
                        : 'No textures match the filters.'}
                </div>}
          </div>
        </div>
      </div>

      {relinkConfirm && (
        <ConfirmModal
          title="Relink missing textures"
          message={`Search “${relinkDir.trim()}” (including subfolders) for the ${plural(missingCount, 'missing file name')} and relink every match (project-relative when possible, one undo step). Files not found there are left as-is. Continue?`}
          confirmLabel={`✓ Relink ${missingCount}`}
          onConfirm={() => { setRelinkConfirm(false); org.doRelinkTextures(relinkDir.trim()) }}
          onCancel={() => setRelinkConfirm(false)}
        />
      )}
      {clearConfirm && (
        <ConfirmModal danger
          title="Clear missing references"
          message={`Blank the dead texture path on ${plural(missingCount, 'reference')} whose file is missing. The materials stay — they just stop pointing at files that no longer exist (one undo step). Continue?`}
          confirmLabel={`✓ Clear ${missingCount} refs`}
          onConfirm={() => { setClearConfirm(false); org.doClearMissingTextures() }}
          onCancel={() => setClearConfirm(false)}
        />
      )}
      {shrink && (
        <ShrinkModal file={shrink.file} width={shrink.width} height={shrink.height} busy={busy}
          onConfirm={(percent) => { const e = shrink; setShrink(null); resizeOne(e, percent) }}
          onCancel={() => setShrink(null)} />
      )}
      {collectConfirm && (
        <CollectModal count={collectable} initialDir={collectDir} busy={busy}
          onConfirm={(dir) => { setCollectDir(dir); setCollectConfirm(false); org.doCollectTextures(dir) }}
          onCancel={() => setCollectConfirm(false)} />
      )}
      {collectOne && (
        <CollectModal count={1} file={collectOne.file} materials={collectOneMats}
          initialDir={collectDir} busy={busy}
          onConfirm={(dir) => {
            const e = collectOne
            setCollectDir(dir)
            setCollectOne(null)
            org.doCollectTextures(dir, [e.path])
          }}
          onCancel={() => setCollectOne(null)} />
      )}
    </>
  )
}
