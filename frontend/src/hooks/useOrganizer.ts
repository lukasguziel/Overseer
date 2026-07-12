// Central app state: settings, report, live previews and all API actions.
// The tab components consume only this object — App.tsx stays thin.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { call } from '../api'
import type { TabId } from '../lib/constants'
import { dominantCasing } from '../lib/constants'
import { computeHygiene } from '../lib/hygiene'
import { prefetchAudit, refreshLoadedAudits, loadedAuditCount, useAuditData } from './useAudit'
import type {
  ChangeEntry, DetectInfo, HistoryEntry, LayerDiff, LayerMismatch,
  OrganizerSettings, PlanResult,
  Preset, ProgressInfo, RenameDiff, ReparentDiff, SceneReport, TranslateDiff,
} from '../types'

export interface RulesInfo {
  groups?: { name: string; priority: number }[]
}

// The five suggestion areas share one "accepted as-is" mechanism: keys the
// user accepted are persisted per section in config.json and filtered out of
// plans server-side.
export type KeepSection = 'naming' | 'translate' | 'layers' | 'structure' | 'materials'

const emptyKeeps = (): Record<KeepSection, Set<string>> => ({
  naming: new Set(), translate: new Set(), layers: new Set(),
  structure: new Set(), materials: new Set(),
})

// Score rounding: never below 0, and never a perfect 100 while todos remain.
const capped = (open: number, share: number): number =>
  open > 0 ? Math.min(99, Math.max(0, Math.round(share * 100))) : 100

export function useOrganizer() {
  const [tab, setTab] = useState<TabId>('overview')
  const [scope, setScope] = useState(false)        // false = whole scene, true = selection
  const [includeHidden, setIncludeHidden] = useState(false)  // false = exclude OM-hidden objects from all stats
  const [autoRefresh, setAutoRefresh] = useState(false)  // watch the scene and re-analyze on change
  // Live C4D object selection (polled) + a manual-mode flag that the selection
  // changed since the last (selection-scoped) analysis.
  const [sel, setSel] = useState<{ count: number; names: string[] }>({ count: 0, names: [] })
  const [selStale, setSelStale] = useState(false)

  // Auto-refresh is derived from the scope: selection scope follows the live
  // C4D selection automatically; whole-scene is manual (click the refresh
  // icon). There is no separate auto/manual toggle any more.
  const chooseScope = useCallback((v: boolean) => {
    setScope(v)
    setAutoRefresh(v)
  }, [])

  const [casing, setCasing] = useState('')   // '' = not chosen yet; auto-detected from the scene
  const [applyCasing, setApplyCasing] = useState(true)        // rule: normalize casing/separators
  const [keepSeparators, setKeepSeparators] = useState(true) // recase words but keep existing separators (e.g. hyphens)
  const [keepSpecials, setKeepSpecials] = useState(true)     // keep special chars like [ ] even in full normalization
  const [language, setLanguage] = useState('en')
  const [numberPad, setNumberPad] = useState(2)
  const [applyNumbering, setApplyNumbering] = useState(true)  // rule: pad/normalize numbers
  const [dedupe, setDedupe] = useState(true)                  // rule: renumber duplicate names to be unique
  const [safe, setSafe] = useState(true)
  const [tidy, setTidy] = useState(true)           // only collect loose objects
  const [translateTarget, setTranslateTarget] = useState('en')  // Translate tab: target language
  // 'google' = online (default — any language, real source detection);
  // 'offline' = bundled dictionaries (10 languages, local, no network)
  const [translateEngine, setTranslateEngine] = useState('google')

  // Active document name (from the cheap `dirty` poll). Drives per-project
  // settings hydration: switching projects reloads the stored settings.
  const [docName, setDocName] = useState<string | null>(null)
  // Gate the whole app render until the first boot preload is fully done —
  // analyze + settings hydration + naming/translate previews computed with the
  // HYDRATED settings. Keeps the wrong pre-hydration count off the screen.
  const [ready, setReady] = useState(false)

  const [busy, setBusy] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [status, setStatus] = useState('Ready.')
  const [error, setError] = useState('')
  const [progress, setProgress] = useState<ProgressInfo | null>(null)
  // Stepped "reload all areas" overlay: drives a client-side progress bar while
  // every area (report + all plans + loaded audits) is refreshed in sequence.
  const [reloadProgress, setReloadProgress] = useState<
    { step: number; total: number; label: string } | null>(null)

  // Progress feed: poll /api/progress permanently (answered by the bridge's
  // server thread, so it works WHILE the C4D main thread is busy). Fast
  // cadence while an operation or preview runs, slow heartbeat otherwise —
  // the heartbeat is what catches BACKGROUND work (debounced re-analyses,
  // batch actions) so the UI can always say what is loading.
  useEffect(() => {
    let stop = false
    const tick = async () => {
      try {
        const p = await call<ProgressInfo>('progress')
        if (!stop) setProgress(p.active ? p : null)
      } catch { /* server busy/gone - keep last state */ }
    }
    tick()
    const t = setInterval(tick, busy || previewing ? 250 : 1000)
    return () => { stop = true; clearInterval(t) }
  }, [busy, previewing])

  // Bumped on every completed analysis (manual, auto-refresh, post-apply).
  // Feeds the live-preview deps so the active tab's plan reloads whenever the
  // scene changed — not only when a setting toggles.
  const [sceneVersion, setSceneVersion] = useState(0)

  // Per-tab snapshot of the preview deps at the time its plan was last loaded
  // (by usePreview, the boot seed or reloadEverything). While the snapshot
  // still matches, entering the tab skips the redundant re-plan.
  const previewDone = useRef<Partial<Record<TabId, unknown[]>>>({})

  const [report, setReport] = useState<SceneReport | null>(null)
  const [detectInfo, setDetectInfo] = useState<DetectInfo | null>(null)
  const [naming, setNaming] = useState<PlanResult<RenameDiff> | null>(null)
  const [structure, setStructure] = useState<PlanResult<ReparentDiff> | null>(null)
  const [layers, setLayers] = useState<PlanResult<LayerDiff> | null>(null)
  const [translation, setTranslation] = useState<PlanResult<TranslateDiff> | null>(null)
  const [layerSuggestions, setLayerSuggestions] = useState<PlanResult<LayerDiff> | null>(null)
  const [layerMismatches, setLayerMismatches] = useState<LayerMismatch[]>([])
  const [keeps, setKeeps] = useState<Record<KeepSection, Set<string>>>(emptyKeeps)
  const [rules, setRules] = useState<RulesInfo | null>(null)
  const [exported, setExported] = useState('')
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [changes, setChanges] = useState<ChangeEntry[]>([])
  const [presets, setPresets] = useState<Preset[]>([])
  const [activePreset, setActivePreset] = useState<string | null>(null)

  const settings = useCallback((): OrganizerSettings => ({
    casing,
    apply_casing: applyCasing,
    keep_separators: keepSeparators,
    keep_specials: keepSpecials,
    language: language === 'none' ? null : language,
    number_pad: numberPad,
    apply_numbering: applyNumbering,
    dedupe,
    selection: scope,
    safe,
    tidy,
  }), [casing, applyCasing, keepSeparators, keepSpecials, language, numberPad, applyNumbering, dedupe, scope, safe, tidy])

  async function run<T>(label: string, fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true); setError(''); setStatus(label + ' …')
    try {
      const r = await fn()
      setStatus(label + ' ✓')
      return r
    } catch (e: any) {
      setError(String(e.message || e)); setStatus(label + ' ✗')
      return undefined
    } finally {
      setBusy(false)
    }
  }

  // Change token of the scene as of the last analysis, so the auto-refresh
  // watcher knows when the scene has moved on (survives re-renders via a ref).
  const lastDirty = useRef<{ dirty: number; name: string; sel: number } | null>(null)

  const doAnalyze = useCallback(() => run('Analysis', async () => {
    // Selection scope + the eye toggle narrow every stat in the report
    // (Overview, Assets, compliance, …) — the server re-aggregates the tree.
    const r = await call('analyze', { settings: { selection: scope, include_hidden: includeHidden } })
    setReport(r.report)
    // Set docName straight from the report so per-project settings hydrate
    // NOW (during boot), not one watcher tick later — otherwise the previews
    // would first render with default settings and visibly correct themselves.
    if (r.report?.doc_name != null) setDocName(r.report.doc_name)
    lastDirty.current = { dirty: r.report?.dirty ?? 0, name: r.report?.doc_name ?? '', sel: r.report?.sel ?? 0 }
    setSelStale(false)  // this analysis is in sync with the current selection
    setSceneVersion((v) => v + 1)  // let the active tab's live preview reload
    call('history').then((h) => setHistory(h.history || [])).catch(() => {})
  }), [scope, includeHidden])

  // Background re-analysis after optimistic per-row actions: refreshes the
  // report + previews WITHOUT the global busy lock, debounced so a burst of
  // row clicks causes one refresh. sceneVersion bump re-plans the open tab.
  // Scope/visibility are read through refs AT FIRE TIME — a pending timer
  // created before a toggle flip must not overwrite the fresh report with
  // the OLD perspective (that made stale on-hidden rows reappear).
  const scopeRef = useRef(scope)
  scopeRef.current = scope
  const includeHiddenRef = useRef(includeHidden)
  includeHiddenRef.current = includeHidden
  const refreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const refreshSoon = useCallback((delay = 700) => {
    if (refreshTimer.current) clearTimeout(refreshTimer.current)
    refreshTimer.current = setTimeout(async () => {
      refreshTimer.current = null
      try {
        const r = await call('analyze', {
          settings: { selection: scopeRef.current, include_hidden: includeHiddenRef.current } })
        setReport(r.report)
        lastDirty.current = { dirty: r.report?.dirty ?? 0, name: r.report?.doc_name ?? '', sel: r.report?.sel ?? 0 }
        setSceneVersion((v) => v + 1)
      } catch { /* the next manual analyze catches up */ }
    }, delay)
  }, [])

  // Optimistically remove rows from a section's plan (per-row apply/accept):
  // the row disappears instantly, the server re-plan follows via refreshSoon.
  const dropRows = useCallback((section: KeepSection, pred: (d: any) => boolean) => {
    const update = (p: any) => {
      if (!p) return p
      const diff = (p.diff || []).filter((d: any) => !pred(d))
      const removed = (p.diff || []).length - diff.length
      return removed ? { ...p, diff, count: Math.max(0, (p.count || 0) - removed) } : p
    }
    if (section === 'naming') setNaming(update)
    else if (section === 'translate') setTranslation(update)
    else if (section === 'layers') setLayers(update)
    else if (section === 'structure') setStructure(update)
  }, [])

  const doDetect = () => run('Detect', async () => {
    const r = await call('detect')
    const d: DetectInfo = r.detect
    setCasing(d.style); setLanguage(d.language || 'en'); setNumberPad(d.number_pad)
    setDetectInfo(d)
    setStatus(`Detected: ${d.style} / ${d.language} / pad ${d.number_pad} (${Math.round(d.confidence * 100)}%)`)
  })

  const doExportJson = () => run('Export JSON', async () => {
    const r = await call('export')
    setReport(r.report)
    setExported(r.export_path ? `JSON → ${r.export_path}` : '(not written)')
  })
  const doExportCsv = () => run('Export CSV', async () => {
    const r = await call('export_csv')
    setReport(r.report)
    setExported(r.csv_path ? `CSV (${r.csv_rows} rows) → ${r.csv_path}` : '(not written)')
  })

  const doFocus = useCallback((guid: number, name?: string) => {
    setStatus(`Focusing ${name || ''}…`)
    call('focus', { guid })
      .then((r) => setStatus(r.ok ? `Focused ${name || ''} ✓` : 'Object not found'))
      .catch((e) => { setError(String(e.message || e)); setStatus('Focus ✗') })
  }, [])

  // Select a material in the C4D material manager and frame the first object
  // that carries it (used by the texture tables).
  const doFocusMaterial = useCallback((name: string) => {
    setStatus(`Focusing material “${name}”…`)
    call('focus_material', { name })
      .then((r) => setStatus(r.object
        ? `Selected “${name}” · framed “${r.object}” ✓`
        : r.ok ? `Selected “${name}” (assigned to no object)` : 'Material not found'))
      .catch((e) => { setError(String(e.message || e)); setStatus('Focus ✗') })
  }, [])

  const doDeleteMaterial = useCallback((name: string) => {
    setStatus(`Deleting ${name}…`)
    call('delete_material', { name, include_hidden: includeHidden })
      .then((r) => {
        setStatus(r.deleted ? `Deleted material “${name}” ✓ (undoable)` : `“${name}” is in use — kept`)
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Delete ✗') })
  }, [doAnalyze, includeHidden])

  const doDeleteAllUnused = useCallback((count: number) => {
    setStatus(`Deleting ${count} unused material${count === 1 ? '' : 's'}…`)
    call('delete_unused_materials', { include_hidden: includeHidden })
      .then((r) => {
        setStatus(`Deleted ${r.deleted} unused material${r.deleted === 1 ? '' : 's'} ✓ (undoable)`)
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Delete ✗') })
  }, [doAnalyze, includeHidden])

  const doFixTexturesRelative = useCallback((materials?: string[]) => {
    setStatus('Making texture paths relative…')
    call('fix_textures_relative', materials ? { materials } : {})
      .then((r) => {
        if (r.error) { setStatus(r.error); return }
        setStatus(r.fixed
          ? `Rewrote ${r.fixed} texture path${r.fixed === 1 ? '' : 's'} to relative ✓ (undoable)`
          : 'No relocatable absolute textures to fix.')
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Fix ✗') })
  }, [doAnalyze])

  // Copy out-of-project textures into <project>/<subdir> and relink the
  // shaders relatively. The copy itself is a file operation (not undoable),
  // the relink is one undo step — the confirm dialog says so.
  const doCollectTextures = useCallback((subdir: string) => {
    setStatus(`Copying textures into “${subdir}”…`)
    call('collect_textures', { subdir })
      .then((r) => {
        if (r.error) { setStatus(r.error); return }
        setStatus(r.relinked
          ? `Copied ${r.copied} file${r.copied === 1 ? '' : 's'} → ${subdir}/ · relinked ${r.relinked} shader${r.relinked === 1 ? '' : 's'} ✓ (relink undoable)`
          : 'No out-of-project textures to collect.')
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Collect ✗') })
  }, [doAnalyze])

  // Relink missing textures by searching a folder recursively for the file
  // names; matches are rewritten (project-relative when possible).
  const doRelinkTextures = useCallback((folder: string) => {
    setStatus(`Searching “${folder}” for missing textures…`)
    call('relink_textures', { folder })
      .then((r) => {
        if (r.error) { setStatus(r.error); return }
        setStatus(`Relinked ${r.relinked} texture${r.relinked === 1 ? '' : 's'} ✓ (undoable)`
          + (r.not_found ? ` · ${r.not_found} not found there` : '')
          + (r.skipped ? ` · ${r.skipped} skipped` : ''))
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Relink ✗') })
  }, [doAnalyze])

  // Per-row texture reference edit: rewrite (or blank) ONE reference,
  // identified by its current raw path + owning material.
  const doSetTexturePath = useCallback((path: string, newPath: string, material?: string) => {
    setStatus(newPath ? 'Rewriting texture reference…' : 'Clearing texture reference…')
    call('set_texture_path', { path, new_path: newPath, material })
      .then((r) => {
        if (r.error) { setStatus(r.error); return }
        setStatus(newPath
          ? `Reference → “${newPath}” ✓ (undoable)`
          : `Reference cleared ✓ (undoable)`)
        refreshSoon(300)
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Edit ✗') })
  }, [refreshSoon])

  // Pick a replacement file for ONE reference via C4D's native file dialog
  // (the request waits while the dialog is open inside Cinema 4D).
  const doPickTexturePath = useCallback((path: string, material?: string) => {
    setStatus('Pick the file in the Cinema 4D window…')
    call('pick_texture_path', { path, material })
      .then((r) => {
        if (r.error) { setStatus(r.error); return }
        if (r.cancelled) { setStatus('File picker cancelled.'); return }
        setStatus(`Reference → “${r.picked}” ✓ (undoable)`)
        refreshSoon(300)
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Pick ✗') })
  }, [refreshSoon])

  // Batch-resize textures to a percentage: writes resized COPIES next to the
  // originals (suffix _25/_50/_75) and relinks the shaders (undoable, journaled).
  const doTextureResize = useCallback((paths: string[], percent: number) => {
    setStatus(`Resizing ${paths.length} texture${paths.length === 1 ? '' : 's'} to ${percent}%…`)
    call('texture_resize', { paths, percent })
      .then((r) => {
        if (r.error) { setStatus(r.error); return }
        setStatus(`Resized ${r.resized} texture${r.resized === 1 ? '' : 's'} to ${percent}% ✓ (undoable)`
          + (r.skipped ? ` · ${r.skipped} skipped` : ''))
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Resize ✗') })
  }, [doAnalyze])

  // Convert texture paths between relative and absolute form (undoable, journaled).
  const doTextureRepath = useCallback((paths: string[], mode: 'relative' | 'absolute') => {
    setStatus(`Making ${paths.length} path${paths.length === 1 ? '' : 's'} ${mode}…`)
    call('texture_repath', { paths, mode })
      .then((r) => {
        if (r.error) { setStatus(r.error); return }
        setStatus(r.changed
          ? `Rewrote ${r.changed} path${r.changed === 1 ? '' : 's'} to ${mode} ✓ (undoable)`
          : `No paths to make ${mode}.`)
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Repath ✗') })
  }, [doAnalyze])

  // Clear dead references: blank the path on shaders whose file is missing.
  const doClearMissingTextures = useCallback(() => {
    setStatus('Clearing missing texture references…')
    call('clear_missing_textures')
      .then((r) => {
        setStatus(`Cleared ${r.cleared} missing reference${r.cleared === 1 ? '' : 's'} ✓ (undoable)`
          + (r.skipped ? ` · ${r.skipped} skipped (parameter not writable)` : ''))
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Clear ✗') })
  }, [doAnalyze])

  // Asset browser batch actions: explicit guids + explicit target, no plan.
  // Layer assignment is OPTIMISTIC: the report's nodes get the new layer
  // immediately (the no-layer worklist row disappears in the same frame),
  // the server call runs in the background and a debounced re-analysis
  // reconciles counts — no global busy lock, no blocking overlay.
  const doAssignLayer = useCallback((guids: number[], layer: string) => {
    const gs = new Set(guids)
    setReport((r) => r
      ? { ...r, nodes: (r.nodes || []).map((n) => gs.has(n.guid) ? { ...n, layer } : n) }
      : r)
    setStatus(`Assigning layer “${layer}”…`)
    call('assign_layer', { guids, layer })
      .then((r) => {
        setStatus(`${r.applied} object${r.applied === 1 ? '' : 's'} → layer “${layer}” ✓ (undoable)`)
        refreshSoon()
      })
      .catch((e) => {
        // Roll back by re-analyzing — the optimistic state was wrong.
        setError(String(e.message || e)); setStatus('Assign layer ✗')
        doAnalyze()
      })
  }, [refreshSoon, doAnalyze])

  const doMoveToGroup = (guids: number[], group: string) => run('Move to group', async () => {
    const r = await call('move_to_group', { guids, group })
    setStatus(`${r.applied} object${r.applied === 1 ? '' : 's'} → group “${group}” ✓ (undoable)`)
    doAnalyze()
  })

  const doDeleteEmptyLayers = (keep?: string[]) => run('Delete empty layers', async () => {
    const r = await call('delete_empty_layers', keep && keep.length ? { keep } : {})
    setStatus(`${r.deleted} empty layer${r.deleted === 1 ? '' : 's'} deleted ✓ (undoable)`)
    doAnalyze()
  })

  const doDeleteLayer = (name: string) => run('Delete layer', async () => {
    const r = await call('delete_layer', { name })
    setStatus(r.deleted
      ? `Layer “${name}” deleted ✓ (undoable)`
      : `“${name}” is not empty (hidden objects count too) — not deleted`)
    doAnalyze()
  })

  // Remember the server-filtered keep list a plan reported for a section.
  const noteKept = useCallback((section: KeepSection, kept?: string[]) => {
    if (kept) setKeeps((k) => ({ ...k, [section]: new Set(kept) }))
  }, [])

  const reloadNaming = useCallback(async () => {
    const r = await call('plan_naming', { settings: settings() })
    setNaming(r)
    noteKept('naming', r.kept)
  }, [settings, noteKept])

  const reloadStructure = useCallback(async () => {
    const r = await call('plan_structure', { settings: settings() })
    setStructure(r)
    noteKept('structure', r.kept)
  }, [settings, noteKept])

  const reloadLayers = useCallback(async () => {
    const r = await call('plan_layers', { settings: settings() })
    setLayers(r)
    noteKept('layers', r.kept)
  }, [settings, noteKept])

  // Layers tab extras: ancestor-layer suggestions for the no-layer worklist
  // and the informational parent/child layer-mismatch findings.
  const reloadLayerExtras = useCallback(async () => {
    const [s, m] = await Promise.all([
      call('plan_layer_suggestions', { settings: settings() }),
      call('layer_mismatches', { settings: settings() }),
    ])
    setLayerSuggestions(s)
    setLayerMismatches(m.findings || [])
  }, [settings])

  const reloadTranslate = useCallback(async () => {
    const p = await call('plan_translate', {
      settings: settings(), target: translateTarget, engine: translateEngine })
    setTranslation(p)
    noteKept('translate', p.kept)
  }, [settings, translateTarget, translateEngine, noteKept])

  // The preview dep snapshots (shared between the usePreview effects below and
  // the eager loaders, so preloaded plans count as "already previewed").
  // Recomputed every render; the elements are state values / stable callbacks.
  const namingDeps = [casing, applyCasing, keepSeparators, keepSpecials, language,
    numberPad, applyNumbering, dedupe, scope, settings, reloadNaming, sceneVersion]
  const translateDeps = [scope, settings, translateTarget, translateEngine,
    reloadTranslate, sceneVersion]
  const structureDeps = [safe, tidy, scope, settings, rules, reloadStructure, sceneVersion]
  const layersDeps = [scope, settings, keeps.layers, reloadLayerExtras, sceneVersion]
  const namingDepsRef = useRef(namingDeps)
  namingDepsRef.current = namingDeps
  const translateDepsRef = useRef(translateDeps)
  translateDepsRef.current = translateDeps
  const structureDepsRef = useRef(structureDeps)
  structureDepsRef.current = structureDeps
  const layersDepsRef = useRef(layersDeps)
  layersDepsRef.current = layersDeps

  // Reload EVERY area in sequence behind a stepped progress overlay: the
  // report (Overview/Assets/Materials/Layers stats), the naming/translate/
  // structure/layer plans, and every audit scan the user has already opened.
  // Used on selection changes under selection scope so all tabs AND nav badges
  // stay current without visiting each one. The analyze here is quiet (no
  // global busy lock) — the stepped overlay is the only spinner.
  const reloadEverything = useCallback(async () => {
    const steps: [string, () => Promise<unknown>][] = [
      ['Analyzing scene', async () => {
        const r = await call('analyze', {
          settings: { selection: scopeRef.current, include_hidden: includeHiddenRef.current } })
        setReport(r.report)
        if (r.report?.doc_name != null) setDocName(r.report.doc_name)
        lastDirty.current = { dirty: r.report?.dirty ?? 0, name: r.report?.doc_name ?? '', sel: r.report?.sel ?? 0 }
        setSelStale(false)
        setSceneVersion((v) => v + 1)
      }],
      ['Naming', () => reloadNaming()],
      ['Translate', () => reloadTranslate()],
      ['Structure', () => reloadStructure()],
      ['Layers', () => reloadLayerExtras()],
    ]
    if (loadedAuditCount() > 0) {
      steps.push(['Tags, files, generators & sims', () => refreshLoadedAudits()])
    }
    const total = steps.length
    for (let i = 0; i < total; i++) {
      setReloadProgress({ step: i, total, label: steps[i][0] })
      try { await steps[i][1]() } catch { /* keep going — later steps still refresh */ }
    }
    // Everything is fresh now — entering a tab must not re-plan again.
    previewDone.current = {
      naming: namingDepsRef.current, translate: translateDepsRef.current,
      structure: structureDepsRef.current, layers: layersDepsRef.current,
    }
    setReloadProgress(null)
  }, [reloadNaming, reloadTranslate, reloadStructure, reloadLayerExtras])

  const reloadEverythingRef = useRef(reloadEverything)
  reloadEverythingRef.current = reloadEverything

  // Toggling the All-objects / Visible-only filter or the Selection /
  // Whole-scene scope changes what EVERY stat counts (report, all plans, open
  // audits), so both must trigger a full reload — nothing else has them in its
  // deps. Deterministic instead of a skip-first heuristic: the report records
  // the perspective it was computed with (`include_hidden`, `scoped`);
  // whenever either disagrees with the current toggles, reload. Self-healing —
  // a transition can never be silently lost — and loop-free: after the reload
  // both sides agree again. The ref guards re-entry while a reload is already
  // in flight (the report stays stale until it lands). Selection scope with an
  // empty C4D selection errors server-side and leaves the report as-is; the
  // effect only refires on the next real change, so it cannot spin.
  const perspectiveReloading = useRef(false)
  useEffect(() => {
    if (!ready || perspectiveReloading.current || !report) return
    const hiddenMismatch = report.include_hidden != null
      && Boolean(report.include_hidden) !== includeHidden
    const scopeMismatch = report.scoped != null
      && Boolean(report.scoped) !== scope
    if (!hiddenMismatch && !scopeMismatch) return
    perspectiveReloading.current = true
    Promise.resolve(reloadEverythingRef.current())
      .finally(() => { perspectiveReloading.current = false })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [includeHidden, scope, ready, report])

  const applyNaming = () => run('Apply naming', async () => {
    const r = await call('apply_naming', { settings: settings() })
    setNaming(r); doAnalyze()
  })
  // Per-row apply: optimistic — the row disappears instantly, the API call
  // and the report refresh run in the background (no global busy lock).
  const applyNamingOne = (guid: number, name?: string) => {
    dropRows('naming', (d) => d.guid === guid)
    setStatus(`Renaming “${name || ''}”…`)
    call('apply_naming', { settings: settings(), guids: [guid] })
      .then((r) => { setStatus(r.applied ? `Renamed “${name || ''}” ✓ (undoable)` : 'Nothing renamed'); refreshSoon() })
      .catch((e) => { setError(String(e.message || e)); setStatus('Rename ✗'); reloadNaming().catch(() => {}) })
  }
  // Batch apply for the guided mode: N rows at once, same optimistic pattern
  // as the One-variants (rows vanish instantly, background call + debounced
  // refresh — no global busy lock).
  const applyNamingMany = useCallback((guids: number[], label: string) => {
    const gs = new Set(guids)
    dropRows('naming', (d) => gs.has(d.guid))
    setStatus(`Renaming ${label}…`)
    call('apply_naming', { settings: settings(), guids })
      .then((r) => { setStatus(`${r.applied} renamed ✓ (undoable)`); refreshSoon() })
      .catch((e) => { setError(String(e.message || e)); setStatus('Rename ✗'); reloadNaming().catch(() => {}) })
  }, [dropRows, settings, refreshSoon, reloadNaming])

  const applyTranslateMany = useCallback((guids: number[], label: string) => {
    const gs = new Set(guids)
    dropRows('translate', (d) => gs.has(d.guid))
    setStatus(`Translating ${label}…`)
    call('apply_translate', {
      settings: settings(), target: translateTarget, engine: translateEngine, guids })
      .then((r) => { setStatus(`${r.applied} translated ✓ (undoable)`); refreshSoon() })
      .catch((e) => { setError(String(e.message || e)); setStatus('Translate ✗'); reloadTranslate().catch(() => {}) })
  }, [dropRows, settings, translateTarget, translateEngine, refreshSoon, reloadTranslate])

  const applyStructure = () => run('Apply structure', async () => {
    const r = await call('apply_structure', { settings: settings() })
    setStructure(r); doAnalyze()
  })
  // Move a single object into its group immediately (per-row ✓).
  const applyStructureOne = (guid: number, name?: string) => {
    dropRows('structure', (d) => d.guid === guid)
    setStatus(`Moving “${name || ''}”…`)
    call('apply_structure', { settings: settings(), guids: [guid] })
      .then((r) => { setStatus(r.applied ? `Moved “${name || ''}” ✓ (undoable)` : 'Nothing moved'); refreshSoon() })
      .catch((e) => { setError(String(e.message || e)); setStatus('Move ✗'); reloadStructure().catch(() => {}) })
  }

  const applyLayers = () => run('Apply layers', async () => {
    const r = await call('apply_layers', { settings: settings() })
    setStatus(`${r.applied} objects tagged ✓ (undoable)`)
    doAnalyze()
    await reloadLayers()  // tagged rows drop out of the preview
  })

  // Tag a single object immediately (per-row ✓, optimistic).
  const applyLayerOne = (guid: number, name?: string) => {
    dropRows('layers', (d) => d.guid === guid)
    setStatus(`Tagging “${name || ''}”…`)
    call('apply_layers', { settings: settings(), guids: [guid] })
      .then((r) => { setStatus(r.applied ? `Tagged “${name || ''}” ✓ (undoable)` : 'Nothing tagged'); refreshSoon() })
      .catch((e) => { setError(String(e.message || e)); setStatus('Tag ✗'); reloadLayers().catch(() => {}) })
  }

  const applyTranslate = () => run('Apply translations', async () => {
    const r = await call('apply_translate', {
      settings: settings(), target: translateTarget, engine: translateEngine })
    setStatus(`Translated ${r.applied} names ✓ (undoable)`)
    doAnalyze()
    await reloadTranslate()  // the just-renamed ones drop out
  })

  // Translate a single entry immediately (per-row button, optimistic).
  const applyTranslateOne = (guid: number, name?: string) => {
    dropRows('translate', (d) => d.guid === guid)
    setStatus(`Translating “${name || ''}”…`)
    call('apply_translate', {
      settings: settings(), target: translateTarget, engine: translateEngine, guids: [guid] })
      .then((r) => { setStatus(r.applied ? `Translated “${name || ''}” ✓ (undoable)` : 'Nothing translated'); refreshSoon() })
      .catch((e) => { setError(String(e.message || e)); setStatus('Translate ✗'); reloadTranslate().catch(() => {}) })
  }

  // Accept-as-is: persist the section's keep list, then re-plan so counts,
  // rows and the Accepted section stay in sync everywhere.
  const syncKeeps = useCallback(async (section: KeepSection, next: Set<string>) => {
    setKeeps((k) => ({ ...k, [section]: next }))
    await call('set_keeps', { section, keys: Array.from(next) })
    if (section === 'materials') { doAnalyze(); return }
    if (section === 'naming') await reloadNaming()
    else if (section === 'translate') await reloadTranslate()
    else if (section === 'layers') await reloadLayers()
    else await reloadStructure()
  }, [doAnalyze, reloadNaming, reloadTranslate, reloadLayers, reloadStructure])

  // Accept-as-is is optimistic: the rows vanish instantly (the server plan
  // filters them identically on the next reload), only the config write goes
  // over the wire. On error the section is re-planned from the server.
  const keep = useCallback((section: KeepSection, key: string) => {
    const next = new Set(keeps[section]); next.add(key)
    setKeeps((k) => ({ ...k, [section]: next }))
    if (section === 'naming' || section === 'translate') {
      dropRows(section, (d) => d.old === key)
    } else if (section === 'layers' || section === 'structure') {
      dropRows(section, (d) => d.name === key)
    }
    setStatus(`Accepted “${key}” as-is ✓`)
    call('set_keeps', { section, keys: Array.from(next) })
      .then(() => { if (section === 'materials') refreshSoon(200) })
      .catch((e) => {
        setError(String(e.message || e)); setStatus('Accept ✗')
        syncKeeps(section, keeps[section]).catch(() => {})
      })
  }, [keeps, dropRows, refreshSoon, syncKeeps])

  const unkeep = useCallback((section: KeepSection, key: string) => {
    const next = new Set(keeps[section]); next.delete(key)
    syncKeeps(section, next).catch((e) => setError(String(e.message || e)))
  }, [keeps, syncKeeps])

  // Restore EVERY accepted-as-is item of a section in one go (the "restore all"
  // button on the Accepted panel): clears the whole keep list and re-plans.
  const unkeepAll = useCallback((section: KeepSection) => {
    syncKeeps(section, new Set()).catch((e) => setError(String(e.message || e)))
  }, [syncKeeps])

  // Accept a whole batch of keys as-is (✕-all buttons, no-layer worklist):
  // one config write, the matching rows vanish, the score jumps.
  const keepMany = useCallback((section: KeepSection, keys: string[]) => {
    if (!keys.length) return
    const keySet = new Set(keys)
    const next = new Set(keeps[section])
    keys.forEach((k) => next.add(k))
    setKeeps((k) => ({ ...k, [section]: next }))
    dropRows(section, (d) => keySet.has(
      section === 'naming' || section === 'translate' ? d.old : d.name))
    setStatus(`Accepted ${keys.length} item${keys.length === 1 ? '' : 's'} as-is ✓`)
    call('set_keeps', { section, keys: Array.from(next) })
      .then(() => { if (section === 'materials') refreshSoon(200) })
      .catch((e) => {
        setError(String(e.message || e)); setStatus('Accept ✗')
        syncKeeps(section, keeps[section]).catch(() => {})
      })
  }, [keeps, dropRows, refreshSoon, syncKeeps])

  // Accept EVERYTHING in a section's current plan as-is.
  const keepAll = useCallback((section: KeepSection) => {
    let keys: string[] = []
    if (section === 'materials') {
      // unused and only_hidden are separate lists — accept the deletable ones.
      keys = report?.materials?.unused || []
    } else {
      const plan = section === 'naming' ? naming
        : section === 'translate' ? translation
          : section === 'layers' ? layers : structure
      keys = (plan?.diff || []).map((d: any) =>
        section === 'naming' || section === 'translate' ? d.old : d.name)
    }
    keepMany(section, keys)
  }, [naming, translation, layers, structure, report, keepMany])

  // --- Per-project settings persistence ------------------------------------
  // Every clickable setting is stored automatically in a per-project JSON
  // (configs/<slug>.json in the plugin's writable data dir) and restored when
  // the same project is reopened. `scope` is deliberately NOT persisted — the
  // selection scope is a session-specific choice, not a project preference.
  const currentUi = useCallback(() => ({
    casing, applyCasing, keepSeparators, keepSpecials, language, numberPad,
    applyNumbering, dedupe, safe, tidy, translateTarget,
    translateEngine, includeHidden,
  }), [casing, applyCasing, keepSeparators, keepSpecials, language, numberPad,
    applyNumbering, dedupe, safe, tidy, translateTarget, translateEngine, includeHidden])

  const applyStoredUi = useCallback((ui: any) => {
    if (typeof ui.casing === 'string') setCasing(ui.casing)
    if (typeof ui.applyCasing === 'boolean') setApplyCasing(ui.applyCasing)
    if (typeof ui.keepSeparators === 'boolean') setKeepSeparators(ui.keepSeparators)
    if (typeof ui.keepSpecials === 'boolean') setKeepSpecials(ui.keepSpecials)
    if (typeof ui.language === 'string') setLanguage(ui.language)
    if (typeof ui.numberPad === 'number') setNumberPad(ui.numberPad)
    if (typeof ui.applyNumbering === 'boolean') setApplyNumbering(ui.applyNumbering)
    if (typeof ui.dedupe === 'boolean') setDedupe(ui.dedupe)
    if (typeof ui.safe === 'boolean') setSafe(ui.safe)
    if (typeof ui.tidy === 'boolean') setTidy(ui.tidy)
    if (typeof ui.translateTarget === 'string') setTranslateTarget(ui.translateTarget)
    if (typeof ui.translateEngine === 'string') setTranslateEngine(ui.translateEngine)
    if (typeof ui.includeHidden === 'boolean') setIncludeHidden(ui.includeHidden)
  }, [])

  const applyPreset = (id: string) => run('Apply preset', async () => {
    const r = await call('apply_preset', { id })
    setActivePreset(r.applied || id)
    setRules(null)  // Let the Rules tab reload
    // The preset is the global config; reflect the current UI into the
    // project file so reopening the project keeps this choice.
    call('ui_settings_set', { ui: currentUi() }).catch(() => {})
    setStatus(`Preset “${r.applied || id}” applied (${r.groups} groups) — open Rules to see it.`)
  })

  // Hydrate stored settings on startup and whenever the active document
  // changes. `hydrated` gates the auto-save below so mount-time defaults never
  // clobber the stored file before the initial load has finished.
  const hydrated = useRef(false)
  // Flips to true once the stored settings for the current document have been
  // applied (or confirmed absent). The badge-seeding effect below keys off it
  // so the naming/translate previews are (re)planned with the HYDRATED
  // settings — not the mount-time defaults, which produce a wrong badge count.
  const [uiHydrated, setUiHydrated] = useState(false)
  useEffect(() => {
    if (docName === null) return
    hydrated.current = false
    setUiHydrated(false)
    let cancel = false
    call('ui_settings_get')
      .then((r) => {
        if (cancel) return
        if (r.found && r.ui) applyStoredUi(r.ui)
      })
      .catch(() => {})
      .finally(() => { if (!cancel) { hydrated.current = true; setUiHydrated(true) } })
    return () => { cancel = true }
  }, [docName, applyStoredUi])

  // Debounced auto-save: persist the current settings ~800ms after any change,
  // but only once the initial hydration for this document has completed.
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!hydrated.current) return
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = setTimeout(() => {
      call('ui_settings_set', { ui: currentUi() }).catch(() => {})
    }, 800)
    return () => { if (saveTimer.current) clearTimeout(saveTimer.current) }
  }, [currentUi])

  // Boot sequence on first load: just analyze. Analyze sets docName, which
  // fires per-project settings hydration; the seed effect below then loads the
  // previews with the HYDRATED settings and lifts the `ready` gate. The whole
  // chain runs behind the blocking preloader, so the app only appears once
  // every nav badge already holds its correct count.
  const booted = useRef(false)
  useEffect(() => {
    if (booted.current) return
    booted.current = true
    doAnalyze()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Seed the naming/translate badge previews once per-project settings have
  // hydrated (uiHydrated flips true after docName -> ui_settings_get). Refs
  // give us the latest reload closures without re-running on every setting
  // change. The FIRST seed is blocking and lifts the `ready` gate; later seeds
  // (document switches) refresh the badges silently in the background.
  const reloadNamingRef = useRef(reloadNaming)
  reloadNamingRef.current = reloadNaming
  const reloadTranslateRef = useRef(reloadTranslate)
  reloadTranslateRef.current = reloadTranslate
  const seededOnce = useRef(false)
  useEffect(() => {
    if (!uiHydrated || !booted.current) return
    const initial = !seededOnce.current
    seededOnce.current = true
    const seed = async () => {
      try {
        await reloadNamingRef.current()
        await reloadTranslateRef.current()
        // Mark both plans as previewed so opening the tab right after boot
        // does not re-plan the identical state.
        previewDone.current.naming = namingDepsRef.current
        previewDone.current.translate = translateDepsRef.current
      } catch { /* transient — the tab's own preview will catch up */ }
    }
    ;(async () => {
      if (initial) {
        await run('Loading previews', seed)
        setReady(true)
      } else {
        await seed()
      }
    })()
  }, [uiHydrated])

  // Scene watcher (always polling the cheap `dirty`+selection token, ~1 s):
  //  - keeps the live C4D selection display up to date;
  //  - AUTO mode: re-analyzes when the scene changed (add/edit/reparent, doc
  //    switch) OR, under selection scope, when the C4D selection changed;
  //  - MANUAL mode: under selection scope, flags that the selection moved on
  //    so the UI can nudge the user to refresh.
  const refreshing = useRef(false)
  useEffect(() => {
    let stop = false
    const tick = async () => {
      if (stop || busy || refreshing.current) return
      try {
        const d = await call('dirty')
        if (stop) return
        setSel({ count: d.sel_count ?? 0, names: d.sel_names ?? [] })
        setDocName(d.name ?? null)  // triggers per-project settings hydration on switch
        const last = lastDirty.current
        if (!last) return
        const docChanged = d.name !== last.name
        const sceneChanged = d.dirty !== last.dirty || docChanged
        const selChanged = d.sel !== last.sel
        // A DOCUMENT switch always reloads everything, even in manual mode —
        // the server now answers for a different scene, so every displayed
        // number (report, plans, audits, health) is stale, not merely old.
        if (docChanged || (autoRefresh && (sceneChanged || (scope && selChanged)))) {
          refreshing.current = true
          Promise.resolve(reloadEverythingRef.current())
            .finally(() => { refreshing.current = false })
        } else if (!autoRefresh && scope && selChanged) {
          setSelStale(true)
        }
      } catch { /* main thread busy/gone — try again next tick */ }
    }
    const t = setInterval(tick, 1000)
    return () => { stop = true; clearInterval(t) }
  }, [autoRefresh, scope, busy, doAnalyze])

  // Load analysis history + presets as soon as the Misc tab becomes active.
  useEffect(() => {
    if (tab !== 'misc') return
    call('history').then((r) => setHistory(r.history || [])).catch(() => {})
    call('presets').then((r) => { setPresets(r.presets || []); setActivePreset(r.active || null) }).catch(() => {})
  }, [tab, report])

  // Generic live-preview effect: recompute plan_<op> debounced
  // as soon as the tab is active and settings change.
  //
  // Freshness guard: entering a tab does NOT re-plan when nothing changed
  // since the plan was last loaded (boot preload, reloadEverything or a
  // previous visit) — `previewDone` records the dep snapshot per tab, and the
  // effect skips while it still matches. Any real change (settings identity,
  // scope, sceneVersion bump from an analysis) breaks the match and reloads.
  function usePreview(activeTab: TabId, delay: number, load: () => Promise<void>, deps: unknown[]) {
    /* eslint-disable react-hooks/rules-of-hooks -- fixed call order, wrappers only */
    useEffect(() => {
      if (tab !== activeTab) return
      const done = previewDone.current[activeTab]
      if (done && done.length === deps.length && done.every((v, i) => Object.is(v, deps[i]))) return
      let cancel = false
      setPreviewing(true)
      const t = setTimeout(async () => {
        try {
          await load()
          if (!cancel) {
            setError('')
            previewDone.current[activeTab] = deps
          }
        } catch (e: any) {
          if (!cancel) setError(String(e.message || e))
        } finally {
          if (!cancel) setPreviewing(false)
        }
      }, delay)
      return () => { cancel = true; clearTimeout(t) }
      // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tab, ...deps])
    /* eslint-enable react-hooks/rules-of-hooks */
  }

  usePreview('naming', 250, async () => {
    await reloadNaming()
  }, namingDeps)

  usePreview('structure', 250, async () => {
    const [, rl] = await Promise.all([
      reloadStructure(),
      rules ? Promise.resolve(null) : call('rules'),
    ])
    if (rl) setRules(rl)
  }, structureDeps)

  usePreview('translate', 250, async () => {
    await reloadTranslate()
  }, translateDeps)

  // NOTE: the scheme-based layer-tagging preview is parked (LayersTab
  // SHOW_TAGGING) — the tab works off the report's no-layer list only, so
  // no plan_layers preview is fetched any more. It does fetch the ancestor
  // suggestions + mismatch findings, though.
  usePreview('layers', 250, async () => {
    await reloadLayerExtras()
  }, layersDeps)

  // Materials keeps live in the analyze report (accepted_all), not a plan.
  useEffect(() => {
    noteKept('materials', report?.materials?.accepted_all)
  }, [report, noteKept])

  // Uniform todo count per area for the tab-header badges: live plan count
  // once the tab was previewed, report-derived fallback before that.
  const planCount = useCallback((t: TabId): number | undefined => {
    switch (t) {
      case 'naming': return naming?.count
      case 'translate': return translation?.count
      case 'layers': {
        // Badge = objects without a layer that the user has not accepted —
        // exactly what the no-layer worklist shows (tagging preview parked).
        const nodes = report?.nodes
        if (!nodes) return undefined
        return nodes.reduce((c, n) =>
          c + (!n.layer && !keeps.layers.has(n.name) ? 1 : 0), 0)
      }
      case 'structure': return structure?.count ?? report?.misplaced?.length
      case 'materials': {
        // Badge = the same "todos" the score counts: unused (deletable)
        // materials + still-missing textures.
        const m = report?.materials
        if (!m && report?.textures == null) return undefined
        return (m?.deletable_count ?? m?.unused?.length ?? 0)
          + (report?.textures?.missing_count ?? 0)
      }
      default: return undefined
    }
  }, [naming, translation, layers, structure, report, keeps.layers])

  // Per-area score (0..100) for the ring next to the navigation. The score
  // measures DECISIONS, not absolute cleanliness: an open todo counts
  // against it, an applied fix OR an accepted-as-is both clear it — so 100
  // is always reachable by working through the list.
  const namingHyg = useMemo(() => report
    ? computeHygiene(report.nodes || [], report.total_polys || 0,
        { casing, kept: keeps.naming })
    : null, [report, casing, keeps.naming])

  // Latest tags scan, shared from the Tags tab via the audit cache — feeds
  // the tags area score without re-running the scan here.
  const tagsScan = useAuditData<{
    summary?: { missing_phong?: number; duplicate_material_tags?: number }
  }>('tags_scan')
  const filesScan = useAuditData<{
    summary?: { total?: number; missing_count?: number }
  }>('files_scan')

  const areaScore = useCallback((t: TabId): number | null => {
    if (!report) return null
    // An empty scene has nothing to judge — scoring it 100 (or 0) is noise.
    // No objects and no materials => no score anywhere.
    if (!(report.nodes?.length || report.object_count)
      && !(report.materials?.total)) return null
    switch (t) {
      case 'naming': {
        // Score = what the tab actually shows as open work: the rename plan
        // (settings-aware — turning a rule off clears its todos) plus the
        // name-cleanup lists, unioned per object. Model-based fallback until
        // the plan has loaded.
        const nodes = report.nodes || []
        if (!nodes.length) return null
        if (!naming?.diff) return namingHyg?.namingScore ?? null
        // Only count objects that exist in the current report: the plan can
        // cover objects the report perspective excludes (hidden/selection),
        // which used to push the open count past the total → negative score.
        const guids = new Set<number>(nodes.map((n) => n.guid))
        const open = new Set<number>(naming.diff.map((d) => d.guid).filter((g) => guids.has(g)))
        namingHyg?.defaults.forEach((n) => open.add(n.guid))
        namingHyg?.dupeGuids.forEach((g) => open.add(g))
        return capped(open.size, (nodes.length - open.size) / nodes.length)
      }
      case 'translate': {
        const open = translation?.count
        const total = translation?.detected?.total ?? report.object_count ?? 0
        if (open == null || !total) return null
        return capped(open, Math.max(0, total - open) / total)
      }
      case 'layers': {
        // Layer coverage: how much of the scene is assigned to ANY layer.
        // Accepting an object as fine-without-layer counts as covered.
        const nodes = report.nodes || []
        if (!nodes.length) return null
        const open = nodes.reduce((c, n) =>
          c + (!n.layer && !keeps.layers.has(n.name) ? 1 : 0), 0)
        return capped(open, (nodes.length - open) / nodes.length)
      }
      case 'materials': {
        // Unused materials + MISSING textures count against the score.
        // Absolute vs relative paths deliberately do not — that is a
        // pipeline preference, not a defect.
        const m = report.materials
        const texTotal = report.textures?.total ?? 0
        const total = (m?.total ?? 0) + texTotal
        if (!total) return null
        const bad = (m?.deletable_count ?? m?.unused?.length ?? 0)
          + (report.textures?.missing_count ?? 0)
        return capped(bad, Math.max(0, total - bad) / total)
      }
      case 'structure':
        return Math.max(0, Math.min(100, Math.round((report.structure_compliance || 0) * 100)))
      case 'tags': {
        // Missing phong tags and duplicate material tags are defects; a
        // scene without either scores 100. Needs the tags scan (runs when
        // the Tags tab opens) — no ring before that.
        const t = tagsScan?.summary
        if (!t) return null
        const bad = (t.missing_phong || 0) + (t.duplicate_material_tags || 0)
        const total = report.nodes?.length || report.object_count || 0
        if (!total) return bad ? 0 : 100
        return capped(bad, Math.max(0, total - bad) / total)
      }
      case 'files': {
        // Missing external files are the defect; a scene with no external
        // references at all is trivially clean.
        const f = filesScan?.summary
        if (!f) return null
        const total = f.total || 0
        if (!total) return 100
        const bad = f.missing_count || 0
        return capped(bad, Math.max(0, total - bad) / total)
      }
      default:
        return null
    }
  }, [report, namingHyg, naming, translation, keeps.layers, tagsScan, filesScan])

  // The Overview shows every area's score: quietly prefetch the audit scans
  // it needs. Naming/translate previews are already loaded eagerly by the
  // boot sequence above (and kept fresh by the tab preview effects).
  useEffect(() => {
    if (tab !== 'overview' || !report) return
    prefetchAudit('tags_scan')   // tags score without visiting the Tags tab
    prefetchAudit('files_scan')  // external-files size for the size tile
  }, [tab, report])

  // First time a scene is analyzed and no casing is chosen yet: pick the
  // scene's dominant producible casing (e.g. mostly PascalCase -> PascalCase).
  useEffect(() => {
    if (casing !== '') return
    const d = dominantCasing(report?.casing)
    if (d) setCasing(d)
  }, [report, casing])

  // Change history: load when the tab opens or the scene changed after an apply.
  const loadChanges = useCallback(() => {
    call('changes').then((r) => setChanges(r.changes || [])).catch(() => {})
  }, [])

  useEffect(() => {
    if (tab === 'misc') loadChanges()
  }, [tab, sceneVersion, loadChanges])

  // Revert a whole run (items omitted) or selected ops within it (items =
  // op indices). Missing/renamed targets are skipped, never abort the run.
  const doRevertChange = useCallback((id: string, items?: number[]) => {
    setStatus(items ? 'Reverting op…' : 'Reverting run…')
    call('revert_change', items ? { id, items } : { id })
      .then((r) => {
        setStatus(r.reverted != null
          ? `Reverted ${r.reverted} change${r.reverted === 1 ? '' : 's'}${r.missing ? ` · ${r.missing} skipped (object gone)` : ''} ✓ (undoable)`
          : 'Reverted ✓')
        loadChanges()
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Revert ✗') })
  }, [loadChanges, doAnalyze])

  const doClearChanges = useCallback(() => {
    call('clear_changes').then(() => loadChanges()).catch(() => {})
  }, [loadChanges])

  // Direct single-object rename (Name cleanup inline edit).
  const doRenameObject = useCallback((guid: number, name: string) => {
    setStatus('Renaming…')
    call('rename_object', { guid, name })
      .then((r) => {
        setStatus(r.ok ? `Renamed to “${name}” ✓ (undoable)` : 'Rename ✗')
        refreshSoon(300)
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Rename ✗') })
  }, [refreshSoon])

  const compliance = report ? Math.round(report.structure_compliance * 100) : null

  return {
    tab, setTab, scope, setScope: chooseScope, includeHidden, setIncludeHidden,
    autoRefresh, setAutoRefresh, sel, selStale,
    casing, setCasing, language, setLanguage, numberPad, setNumberPad,
    applyCasing, setApplyCasing, keepSeparators, setKeepSeparators,
    keepSpecials, setKeepSpecials,
    applyNumbering, setApplyNumbering, dedupe, setDedupe,
    safe, setSafe, tidy, setTidy, translateTarget, setTranslateTarget,
    translateEngine, setTranslateEngine,
    busy, status, setStatus, error, previewing, progress, ready, reloadProgress, reloadEverything,
    report, detectInfo, compliance,
    naming, structure, layers, translation,
    layerSuggestions, layerMismatches, doDeleteLayer, doDeleteEmptyLayers,
    keeps, keep, unkeep, unkeepAll, keepAll, keepMany, planCount, areaScore, doRenameObject,
    changes, doRevertChange, doClearChanges,
    rules, exported, history, presets, activePreset,
    doAnalyze, doDetect, doExportJson, doExportCsv, doFocus, doFocusMaterial,
    doAssignLayer, doMoveToGroup,
    doDeleteMaterial, doDeleteAllUnused, doFixTexturesRelative, doCollectTextures,
    doRelinkTextures, doClearMissingTextures, doSetTexturePath, doPickTexturePath,
    doTextureResize, doTextureRepath,
    applyNaming, applyNamingOne, applyNamingMany,
    applyStructure, applyStructureOne,
    applyLayers, applyLayerOne,
    applyTranslate, applyTranslateOne, applyTranslateMany, applyPreset,
  }
}

export type Organizer = ReturnType<typeof useOrganizer>
