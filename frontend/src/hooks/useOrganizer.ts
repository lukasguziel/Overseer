// Central app state: settings, report, live previews and all API actions.
// The tab components consume only this object — App.tsx stays thin.
import { useCallback, useEffect, useRef, useState } from 'react'
import { call } from '../api'
import type { TabId } from '../lib/constants'
import { dominantCasing } from '../lib/constants'
import type {
  ChangeEntry, DetectInfo, HistoryEntry, LayerDiff, OrganizerSettings, PlanResult,
  Preset, ProgressInfo, RenameDiff, ReparentDiff, SceneReport, TranslateDiff,
} from '../types'

export interface RulesInfo {
  groups?: { name: string; priority: number }[]
}

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
  const [language, setLanguage] = useState('en')
  const [numberPad, setNumberPad] = useState(2)
  const [applyNumbering, setApplyNumbering] = useState(true)  // rule: pad/normalize numbers
  const [dedupe, setDedupe] = useState(true)                  // rule: renumber duplicate names to be unique
  const [safe, setSafe] = useState(true)
  const [tidy, setTidy] = useState(true)           // only collect loose objects
  const [translateTarget, setTranslateTarget] = useState('en')  // Translate tab: target language
  // 'offline' = bundled dictionaries (10 languages, local); 'google' = online
  const [translateEngine, setTranslateEngine] = useState('offline')

  const [busy, setBusy] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [status, setStatus] = useState('Ready.')
  const [error, setError] = useState('')
  const [progress, setProgress] = useState<ProgressInfo | null>(null)

  // Preloader: while an operation OR a live preview runs, poll /api/progress
  // (answered by the bridge's server thread, so it works WHILE the main
  // thread is busy — e.g. during online translation fetches).
  useEffect(() => {
    if (!busy && !previewing) { setProgress(null); return }
    let stop = false
    const tick = async () => {
      try {
        const p = await call<ProgressInfo>('progress')
        if (!stop) setProgress(p.active ? p : null)
      } catch { /* server busy/gone - keep last state */ }
    }
    tick()
    const t = setInterval(tick, 250)
    return () => { stop = true; clearInterval(t) }
  }, [busy, previewing])

  // Bumped on every completed analysis (manual, auto-refresh, post-apply).
  // Feeds the live-preview deps so the active tab's plan reloads whenever the
  // scene changed — not only when a setting toggles.
  const [sceneVersion, setSceneVersion] = useState(0)

  const [report, setReport] = useState<SceneReport | null>(null)
  const [detectInfo, setDetectInfo] = useState<DetectInfo | null>(null)
  const [naming, setNaming] = useState<PlanResult<RenameDiff> | null>(null)
  const [structure, setStructure] = useState<PlanResult<ReparentDiff> | null>(null)
  const [layers, setLayers] = useState<PlanResult<LayerDiff> | null>(null)
  const [layersAccepted, setLayersAccepted] = useState<Set<number>>(() => new Set())  // guids to tag
  const [translation, setTranslation] = useState<PlanResult<TranslateDiff> | null>(null)
  const [accepted, setAccepted] = useState<Set<number>>(() => new Set())  // guids for the rename
  const [keepNames, setKeepNames] = useState<Set<string>>(() => new Set())  // names kept as-is (persisted in config)
  const [rules, setRules] = useState<RulesInfo | null>(null)
  const [exported, setExported] = useState('')
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [changes, setChanges] = useState<ChangeEntry[]>([])
  const [presets, setPresets] = useState<Preset[]>([])
  const [activePreset, setActivePreset] = useState<string | null>(null)

  const settings = useCallback((): OrganizerSettings => ({
    casing,
    apply_casing: applyCasing,
    language: language === 'none' ? null : language,
    number_pad: numberPad,
    apply_numbering: applyNumbering,
    dedupe,
    selection: scope,
    safe,
    tidy,
  }), [casing, applyCasing, language, numberPad, applyNumbering, dedupe, scope, safe, tidy])

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
    lastDirty.current = { dirty: r.report?.dirty ?? 0, name: r.report?.doc_name ?? '', sel: r.report?.sel ?? 0 }
    setSelStale(false)  // this analysis is in sync with the current selection
    setSceneVersion((v) => v + 1)  // let the active tab's live preview reload
    call('history').then((h) => setHistory(h.history || [])).catch(() => {})
  }), [scope, includeHidden])

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

  const doDeleteMaterial = useCallback((name: string) => {
    setStatus(`Deleting ${name}…`)
    call('delete_material', { name })
      .then((r) => {
        setStatus(r.deleted ? `Deleted material “${name}” ✓ (undoable)` : `“${name}” is in use — kept`)
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Delete ✗') })
  }, [doAnalyze])

  const doDeleteAllUnused = useCallback((count: number) => {
    setStatus(`Deleting ${count} unused material${count === 1 ? '' : 's'}…`)
    call('delete_unused_materials')
      .then((r) => {
        setStatus(`Deleted ${r.deleted} unused material${r.deleted === 1 ? '' : 's'} ✓ (undoable)`)
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Delete ✗') })
  }, [doAnalyze])

  // Accept/un-accept a material as intentionally unused (persisted in config,
  // improves the materials health score). Source of truth: materials.accepted_all.
  const syncAccepted = useCallback((next: Set<string>) => {
    setStatus('Saving…')
    call('set_accepted_unused', { names: Array.from(next) })
      .then(() => doAnalyze())
      .catch((e) => { setError(String(e.message || e)); setStatus('Save ✗') })
  }, [doAnalyze])

  const acceptUnused = useCallback((name: string) => {
    const cur = new Set(report?.materials?.accepted_all || [])
    cur.add(name)
    syncAccepted(cur)
  }, [report, syncAccepted])

  const unacceptUnused = useCallback((name: string) => {
    const cur = new Set(report?.materials?.accepted_all || [])
    cur.delete(name)
    syncAccepted(cur)
  }, [report, syncAccepted])

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

  const applyNaming = () => run('Apply naming', async () => {
    const r = await call('apply_naming', { settings: settings() })
    setNaming(r); doAnalyze()
  })
  // Accept a single rename (green ✓ per row).
  const applyNamingOne = (guid: number, name?: string) => run('Rename', async () => {
    const r = await call('apply_naming', { settings: settings(), guids: [guid] })
    setStatus(r.applied ? `Renamed “${name || ''}” ✓ (undoable)` : 'Nothing renamed')
    doAnalyze()
  })
  const applyStructure = () => run('Apply structure', async () => {
    const r = await call('apply_structure', { settings: settings() })
    setStructure(r); doAnalyze()
  })
  const reloadLayers = useCallback(async () => {
    const r = await call('plan_layers', { settings: settings() })
    setLayers(r)
    setLayersAccepted(new Set((r.diff || []).map((d: LayerDiff) => d.guid)))
  }, [settings])

  const applyLayers = () => run('Apply layers', async () => {
    const r = await call('apply_layers', {
      settings: settings(), guids: Array.from(layersAccepted) })
    setStatus(`${r.applied} objects tagged ✓ (undoable)`)
    doAnalyze()
    await reloadLayers()  // tagged rows drop out of the preview
  })

  // Tag a single object immediately (per-row ✓).
  const applyLayerOne = (guid: number, name?: string) => run('Tag', async () => {
    const r = await call('apply_layers', { settings: settings(), guids: [guid] })
    setStatus(r.applied ? `Tagged “${name || ''}” ✓ (undoable)` : 'Nothing tagged')
    doAnalyze()
    await reloadLayers()
  })
  const reloadTranslate = useCallback(async () => {
    const p = await call('plan_translate', {
      settings: settings(), target: translateTarget, engine: translateEngine })
    setTranslation(p)
    setAccepted(new Set((p.diff || []).map((d: TranslateDiff) => d.guid)))
  }, [settings, translateTarget, translateEngine])

  const applyTranslate = () => run('Apply translations', async () => {
    const guids = Array.from(accepted)
    const r = await call('apply_translate', {
      settings: settings(), target: translateTarget, engine: translateEngine, guids })
    setStatus(`Translated ${r.applied} names ✓ (undoable)`)
    doAnalyze()
    await reloadTranslate()  // the just-renamed ones drop out
  })

  // Translate a single entry immediately (per-row button).
  const applyTranslateOne = (guid: number, name?: string) => run('Translate', async () => {
    const r = await call('apply_translate', {
      settings: settings(), target: translateTarget, engine: translateEngine, guids: [guid] })
    setStatus(r.applied ? `Translated “${name || ''}” ✓ (undoable)` : 'Nothing translated')
    doAnalyze()
    await reloadTranslate()
  })

  const applyPreset = (id: string) => run('Apply preset', async () => {
    const r = await call('apply_preset', { id })
    setActivePreset(r.applied || id)
    setRules(null)  // Let the Rules tab reload
    setStatus(`Preset “${r.applied || id}” applied (${r.groups} groups) — open Rules to see it.`)
  })

  // Auto-analyze on first load.
  useEffect(() => { doAnalyze() }, [doAnalyze])

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
        const last = lastDirty.current
        if (!last) return
        const sceneChanged = d.dirty !== last.dirty || d.name !== last.name
        const selChanged = d.sel !== last.sel
        if (autoRefresh && (sceneChanged || (scope && selChanged))) {
          refreshing.current = true
          Promise.resolve(doAnalyze()).finally(() => { refreshing.current = false })
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
  function usePreview(activeTab: TabId, delay: number, load: () => Promise<void>, deps: unknown[]) {
    /* eslint-disable react-hooks/rules-of-hooks -- fixed call order, wrappers only */
    useEffect(() => {
      if (tab !== activeTab) return
      let cancel = false
      setPreviewing(true)
      const t = setTimeout(async () => {
        try {
          await load()
          if (!cancel) setError('')
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

  usePreview('naming', 350, async () => {
    const r = await call('plan_naming', { settings: settings() })
    setNaming(r)
    if (r.keep_names) setKeepNames(new Set(r.keep_names))
  }, [casing, applyCasing, language, numberPad, applyNumbering, dedupe, scope, settings, sceneVersion])

  // Persist the keep-list to config.json, then re-plan so the score/count sync.
  const syncKeep = useCallback(async (next: Set<string>) => {
    setKeepNames(next)
    await call('set_keep_names', { names: Array.from(next) })
    const r = await call('plan_naming', { settings: settings() })
    setNaming(r)
  }, [settings])

  const keepName = useCallback((name: string) => {
    const next = new Set(keepNames); next.add(name)
    syncKeep(next).catch((e) => setError(String(e.message || e)))
  }, [keepNames, syncKeep])

  const unkeepName = useCallback((name: string) => {
    const next = new Set(keepNames); next.delete(name)
    syncKeep(next).catch((e) => setError(String(e.message || e)))
  }, [keepNames, syncKeep])

  usePreview('structure', 350, async () => {
    const [r, rl] = await Promise.all([
      call('plan_structure', { settings: settings() }),
      rules ? Promise.resolve(null) : call('rules'),
    ])
    setStructure(r)
    if (rl) setRules(rl)
  }, [safe, scope, settings, rules, sceneVersion])

  usePreview('translate', 300, async () => {
    await reloadTranslate()
  }, [scope, settings, translateTarget, translateEngine, reloadTranslate, sceneVersion])

  usePreview('layers', 300, async () => {
    await reloadLayers()
  }, [scope, settings, reloadLayers, sceneVersion])

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

  const doRevertChange = useCallback((id: string) => {
    setStatus('Reverting change…')
    call('revert_change', { id })
      .then((r) => {
        setStatus(r.reverted != null
          ? `Reverted ${r.reverted} change${r.reverted === 1 ? '' : 's'}${r.missing ? ` (${r.missing} object(s) not found)` : ''} ✓ (undoable)`
          : 'Reverted ✓')
        loadChanges()
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Revert ✗') })
  }, [loadChanges, doAnalyze])

  const doClearChanges = useCallback(() => {
    call('clear_changes').then(() => loadChanges()).catch(() => {})
  }, [loadChanges])

  const compliance = report ? Math.round(report.structure_compliance * 100) : null

  return {
    tab, setTab, scope, setScope: chooseScope, includeHidden, setIncludeHidden,
    autoRefresh, setAutoRefresh, sel, selStale,
    casing, setCasing, language, setLanguage, numberPad, setNumberPad,
    applyCasing, setApplyCasing,
    applyNumbering, setApplyNumbering, dedupe, setDedupe,
    safe, setSafe, tidy, setTidy, translateTarget, setTranslateTarget,
    translateEngine, setTranslateEngine,
    busy, status, error, previewing, progress,
    report, detectInfo, compliance,
    naming, structure, layers, translation, accepted, setAccepted,
    layersAccepted, setLayersAccepted,
    keepNames, keepName, unkeepName,
    changes, doRevertChange, doClearChanges,
    rules, exported, history, presets, activePreset,
    doAnalyze, doDetect, doExportJson, doExportCsv, doFocus,
    doDeleteMaterial, doDeleteAllUnused, doFixTexturesRelative,
    acceptUnused, unacceptUnused,
    applyNaming, applyNamingOne, applyStructure, applyLayers, applyLayerOne,
    applyTranslate, applyTranslateOne, applyPreset,
  }
}

export type Organizer = ReturnType<typeof useOrganizer>
