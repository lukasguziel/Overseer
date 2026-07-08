// Central app state: settings, report, live previews and all API actions.
// The tab components consume only this object — App.tsx stays thin.
import { useCallback, useEffect, useRef, useState } from 'react'
import { call } from '../api'
import type { TabId } from '../lib/constants'
import type {
  DetectInfo, HistoryEntry, LayerDiff, OrganizerSettings, PlanResult, Preset,
  ProgressInfo, RenameDiff, ReparentDiff, SceneReport, TranslateDiff,
} from '../types'

export interface RulesInfo {
  groups?: { name: string; priority: number }[]
}

export function useOrganizer() {
  const [tab, setTab] = useState<TabId>('overview')
  const [scope, setScope] = useState(false)        // false = whole scene, true = selection
  const [includeHidden, setIncludeHidden] = useState(false)  // false = exclude OM-hidden objects from all stats
  const [autoRefresh, setAutoRefresh] = useState(false)  // watch the scene and re-analyze on change

  const [casing, setCasing] = useState('PascalCase')
  const [language, setLanguage] = useState('en')
  const [numberPad, setNumberPad] = useState(2)
  const [safe, setSafe] = useState(true)
  const [tidy, setTidy] = useState(true)           // only collect loose objects
  const [translateTarget, setTranslateTarget] = useState('en')  // Translate tab: target language

  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('Ready.')
  const [error, setError] = useState('')
  const [progress, setProgress] = useState<ProgressInfo | null>(null)

  // Preloader: while an operation runs, poll /api/progress (answered by the
  // bridge's server thread, so it works WHILE the main thread is busy).
  useEffect(() => {
    if (!busy) { setProgress(null); return }
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
  }, [busy])

  const [report, setReport] = useState<SceneReport | null>(null)
  const [detectInfo, setDetectInfo] = useState<DetectInfo | null>(null)
  const [naming, setNaming] = useState<PlanResult<RenameDiff> | null>(null)
  const [structure, setStructure] = useState<PlanResult<ReparentDiff> | null>(null)
  const [layers, setLayers] = useState<PlanResult<LayerDiff> | null>(null)
  const [translation, setTranslation] = useState<PlanResult<TranslateDiff> | null>(null)
  const [accepted, setAccepted] = useState<Set<number>>(() => new Set())  // guids for the rename
  const [rules, setRules] = useState<RulesInfo | null>(null)
  const [previewing, setPreviewing] = useState(false)
  const [exported, setExported] = useState('')
  const [history, setHistory] = useState<HistoryEntry[]>([])
  const [presets, setPresets] = useState<Preset[]>([])
  const [activePreset, setActivePreset] = useState<string | null>(null)

  const settings = useCallback((): OrganizerSettings => ({
    casing,
    language: language === 'none' ? null : language,
    number_pad: numberPad,
    selection: scope,
    safe,
    tidy,
  }), [casing, language, numberPad, scope, safe, tidy])

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
  const lastDirty = useRef<{ dirty: number; name: string } | null>(null)

  const doAnalyze = useCallback(() => run('Analysis', async () => {
    // Selection scope + the eye toggle narrow every stat in the report
    // (Overview, Assets, compliance, …) — the server re-aggregates the tree.
    const r = await call('analyze', { settings: { selection: scope, include_hidden: includeHidden } })
    setReport(r.report)
    lastDirty.current = { dirty: r.report?.dirty ?? 0, name: r.report?.doc_name ?? '' }
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
  const applyStructure = () => run('Apply structure', async () => {
    const r = await call('apply_structure', { settings: settings() })
    setStructure(r); doAnalyze()
  })
  const applyLayers = () => run('Apply layers', async () => {
    const r = await call('apply_layers', { settings: settings() })
    setLayers(r)
  })
  const reloadTranslate = useCallback(async () => {
    const p = await call('plan_translate', { settings: settings(), target: translateTarget })
    setTranslation(p)
    setAccepted(new Set((p.diff || []).map((d: TranslateDiff) => d.guid)))
  }, [settings, translateTarget])

  const applyTranslate = () => run('Apply translations', async () => {
    const guids = Array.from(accepted)
    const r = await call('apply_translate', { settings: settings(), target: translateTarget, guids })
    setStatus(`Translated ${r.applied} names ✓ (undoable)`)
    doAnalyze()
    await reloadTranslate()  // the just-renamed ones drop out
  })

  // Translate a single entry immediately (per-row button).
  const applyTranslateOne = (guid: number, name?: string) => run('Translate', async () => {
    const r = await call('apply_translate', { settings: settings(), target: translateTarget, guids: [guid] })
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

  // Auto-refresh watcher: while enabled, poll the cheap `dirty` change token
  // (~1.2 s). When the scene has moved past the last-analyzed token — a cube
  // added, geometry edited, objects reparented — or the active document
  // switched, re-run the analysis so every graph reflects the live scene.
  const refreshing = useRef(false)
  useEffect(() => {
    if (!autoRefresh) return
    let stop = false
    const tick = async () => {
      if (stop || busy || refreshing.current) return
      try {
        const d = await call('dirty')
        const last = lastDirty.current
        if (!stop && last && (d.dirty !== last.dirty || d.name !== last.name)) {
          refreshing.current = true
          Promise.resolve(doAnalyze()).finally(() => { refreshing.current = false })
        }
      } catch { /* main thread busy/gone — try again next tick */ }
    }
    const t = setInterval(tick, 1200)
    return () => { stop = true; clearInterval(t) }
  }, [autoRefresh, busy, doAnalyze])

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
  }, [casing, language, numberPad, scope, settings])

  usePreview('structure', 350, async () => {
    const [r, rl] = await Promise.all([
      call('plan_structure', { settings: settings() }),
      rules ? Promise.resolve(null) : call('rules'),
    ])
    setStructure(r)
    if (rl) setRules(rl)
  }, [safe, scope, settings, rules])

  usePreview('translate', 300, async () => {
    await reloadTranslate()
  }, [scope, settings, translateTarget, reloadTranslate])

  usePreview('layers', 300, async () => {
    const r = await call('plan_layers', { settings: settings() })
    setLayers(r)
  }, [scope, settings])

  const compliance = report ? Math.round(report.structure_compliance * 100) : null

  return {
    tab, setTab, scope, setScope, includeHidden, setIncludeHidden,
    autoRefresh, setAutoRefresh,
    casing, setCasing, language, setLanguage, numberPad, setNumberPad,
    safe, setSafe, tidy, setTidy, translateTarget, setTranslateTarget,
    busy, status, error, previewing, progress,
    report, detectInfo, compliance,
    naming, structure, layers, translation, accepted, setAccepted,
    rules, exported, history, presets, activePreset,
    doAnalyze, doDetect, doExportJson, doExportCsv, doFocus,
    doDeleteMaterial, doDeleteAllUnused, doFixTexturesRelative,
    applyNaming, applyStructure, applyLayers, applyTranslate, applyTranslateOne,
    applyPreset,
  }
}

export type Organizer = ReturnType<typeof useOrganizer>
