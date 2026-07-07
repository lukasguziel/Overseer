// Zentraler App-State: Settings, Report, Live-Previews und alle API-Aktionen.
// Die Tab-Komponenten konsumieren nur dieses Objekt — App.tsx bleibt duenn.
import { useCallback, useEffect, useState } from 'react'
import { call } from '../api'
import type { TabId } from '../lib/constants'
import type {
  DetectInfo, HistoryEntry, LayerDiff, OrganizerSettings, PlanResult, Preset,
  RenameDiff, ReparentDiff, SceneReport, TranslateDiff,
} from '../types'

export interface RulesInfo {
  groups?: { name: string; priority: number }[]
}

export function useOrganizer() {
  const [tab, setTab] = useState<TabId>('overview')
  const [scope, setScope] = useState(false)        // false = whole scene, true = selection

  const [casing, setCasing] = useState('PascalCase')
  const [language, setLanguage] = useState('en')
  const [numberPad, setNumberPad] = useState(2)
  const [safe, setSafe] = useState(true)
  const [tidy, setTidy] = useState(true)           // nur lose Objekte einsammeln

  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('Ready.')
  const [error, setError] = useState('')

  const [report, setReport] = useState<SceneReport | null>(null)
  const [detectInfo, setDetectInfo] = useState<DetectInfo | null>(null)
  const [naming, setNaming] = useState<PlanResult<RenameDiff> | null>(null)
  const [structure, setStructure] = useState<PlanResult<ReparentDiff> | null>(null)
  const [layers, setLayers] = useState<PlanResult<LayerDiff> | null>(null)
  const [translation, setTranslation] = useState<PlanResult<TranslateDiff> | null>(null)
  const [accepted, setAccepted] = useState<Set<number>>(() => new Set())  // guids fuers Rename
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

  const doAnalyze = useCallback(() => run('Analysis', async () => {
    const r = await call('analyze')
    setReport(r.report)
    call('history').then((h) => setHistory(h.history || [])).catch(() => {})
  }), [])

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
  const applyTranslate = () => run('Apply translations', async () => {
    const guids = Array.from(accepted)
    const r = await call('apply_translate', { settings: settings(), guids })
    setStatus(`Translated ${r.applied} names ✓ (undoable)`)
    doAnalyze()
    // Vorschau neu laden -> die eben umbenannten fallen raus
    const p = await call('plan_translate', { settings: settings() })
    setTranslation(p)
    setAccepted(new Set((p.diff || []).map((d: TranslateDiff) => d.guid)))
  })

  const applyPreset = (id: string) => run('Apply preset', async () => {
    const r = await call('apply_preset', { id })
    setActivePreset(r.applied || id)
    setRules(null)  // Rules-Tab neu laden lassen
    setStatus(`Preset “${r.applied || id}” applied (${r.groups} groups) — open Rules to see it.`)
  })

  // Auto-Analyse beim ersten Laden.
  useEffect(() => { doAnalyze() }, [doAnalyze])

  // Analyse-Historie + Presets laden, sobald der Misc-Tab aktiv wird.
  useEffect(() => {
    if (tab !== 'misc') return
    call('history').then((r) => setHistory(r.history || [])).catch(() => {})
    call('presets').then((r) => { setPresets(r.presets || []); setActivePreset(r.active || null) }).catch(() => {})
  }, [tab, report])

  // Generischer Live-Preview-Effekt: plan_<op> debounced neu berechnen,
  // sobald der Tab aktiv ist und sich Settings aendern.
  function usePreview(activeTab: TabId, delay: number, load: () => Promise<void>, deps: unknown[]) {
    /* eslint-disable react-hooks/rules-of-hooks -- feste Aufruf-Reihenfolge, nur Wrapper */
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
    const r = await call('plan_translate', { settings: settings() })
    setTranslation(r)
    setAccepted(new Set((r.diff || []).map((d: TranslateDiff) => d.guid)))
  }, [scope, settings])

  usePreview('layers', 300, async () => {
    const r = await call('plan_layers', { settings: settings() })
    setLayers(r)
  }, [scope, settings])

  const compliance = report ? Math.round(report.structure_compliance * 100) : null

  return {
    tab, setTab, scope, setScope,
    casing, setCasing, language, setLanguage, numberPad, setNumberPad,
    safe, setSafe, tidy, setTidy,
    busy, status, error, previewing,
    report, detectInfo, compliance,
    naming, structure, layers, translation, accepted, setAccepted,
    rules, exported, history, presets, activePreset,
    doAnalyze, doDetect, doExportJson, doExportCsv, doFocus,
    doDeleteMaterial, doDeleteAllUnused,
    applyNaming, applyStructure, applyLayers, applyTranslate, applyPreset,
  }
}

export type Organizer = ReturnType<typeof useOrganizer>
