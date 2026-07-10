// Thin shell: topbar + tab navigation. All state/API flow lives in
// hooks/useOrganizer, each tab in tabs/<Name>Tab.tsx.
import { useOrganizer } from './hooks/useOrganizer'
import { version } from '../package.json'
import logo from './assets/so_logo.jpg'
import { TABS } from './lib/constants'
import ScopeToggle from './components/ScopeToggle'
import VisibilityToggle from './components/VisibilityToggle'
import Tip from './components/Tip'
import { IconRefresh } from './components/icons'
import Preloader from './components/Preloader'
import ReloadOverlay from './components/ReloadOverlay'
import ProgressChip from './components/ProgressChip'
import EmptyState from './components/EmptyState'
import StatusBar from './components/StatusBar'
import Ring, { type Tone } from './components/Ring'
import { scoreRating, scoreTone } from './lib/score'
import OverviewTab from './tabs/OverviewTab'
import AssetsTab from './tabs/AssetsTab'
import NamingTab from './tabs/NamingTab'
import TranslateTab from './tabs/TranslateTab'
import StructureTab from './tabs/StructureTab'
import LayersTab from './tabs/LayersTab'
import MaterialsTab from './tabs/MaterialsTab'
import RulesTab from './tabs/RulesTab'
import MiscTab from './tabs/MiscTab'
import TagsTab from './tabs/TagsTab'
import GeneratorsTab from './tabs/GeneratorsTab'
import FilesTab from './tabs/FilesTab'
import SimsTab from './tabs/SimsTab'

export default function App() {
  const org = useOrganizer()
  const { tab, report, error, busy, previewing } = org
  const spinning = busy || previewing

  // Hold the whole UI behind the preloader until the first boot preload is
  // fully done (analyze + settings hydration + previews). This keeps the wrong
  // pre-hydration badge count off the screen — the app appears already correct.
  if (!org.ready) {
    return (
      <div className="app">
        {org.progress && <Preloader progress={org.progress} />}
      </div>
    )
  }
  // Area score ring next to the nav: how far this area is worked through
  // (fixed OR deliberately accepted both count — 100 is always reachable).
  const score = org.areaScore(tab)
  const tone: Tone = score == null ? 'low' : scoreTone(score)

  return (
    <div className="app">
      {busy && org.progress?.active && <Preloader progress={org.progress} />}
      {org.reloadProgress && <ReloadOverlay progress={org.reloadProgress} />}
      <header className="topbar">
        <div className="brand">
          <img className="brand-logo" src={logo} alt="" />
          <div className="brand-text">
            <span className="brand-title">Scene Organizer
              <span className="brand-version">v{version}</span>
            </span>
            {report && (
              <span className="scene-meta">
                <span className="scene-name">{report.file || '(scene)'}</span>
              </span>
            )}
          </div>
        </div>

        <div className="topbar-right">
          <Tip text="Wirkungsbereich: „Ganze Szene“ analysiert und ändert alle Objekte, „Auswahl“ nur die aktive C4D-Auswahl samt Kindern.">
            <ScopeToggle scope={org.scope} setScope={org.setScope} sel={org.sel} />
          </Tip>
          <Tip text="Ob im Objekt-Manager ausgeblendete Objekte in Statistiken und Funde einbezogen werden.">
            <VisibilityToggle includeHidden={org.includeHidden} setIncludeHidden={org.setIncludeHidden}
              hidden={report?.hidden_count} />
          </Tip>
          <button className={'refresh-btn' + (spinning ? ' spin' : '') + (error ? ' err' : '')}
            onClick={org.doAnalyze} disabled={busy}
            title={org.scope
              ? 'Selection scope updates live — click to force a re-analysis'
              : error ? 'Analysis failed — click to retry' : 'Re-analyze the scene'}>
            <IconRefresh />
          </button>
        </div>
      </header>

      <div className="tabs-row">
        <nav className="tabs">
          {TABS.map(([id, label, soon]) => {
            // `soon` tabs (Rules) are parked — visible but disabled,
            // so the roadmap stays honest without confusing anyone.
            // Generators/Sims are disabled when the analyzed scene has none
            // (flags default undefined → stay clickable until a report says false).
            const emptyArea =
              (id === 'generators' && report?.has_generators === false) ||
              (id === 'sims' && report?.has_sims === false)
            const disabled = !!soon || emptyArea
            // Uniform todo badge per area (live plan count, report fallback).
            const todo = org.planCount(id) ?? 0
            // Thin progress underline: the area's score as a mini bar, same
            // color scale as the health ring — glanceable progress per tab.
            const pct = disabled ? null : org.areaScore(id)
            const tpTone = pct == null ? '' : pct >= 80 ? ' tp-good' : pct >= 50 ? ' tp-mid' : ' tp-low'
            return (
              <button key={id} disabled={disabled}
                className={'tab' + (tab === id ? ' on' : '') + (disabled ? ' off' : '')}
                onClick={() => !disabled && org.setTab(id)}
                title={emptyArea
                  ? (id === 'generators'
                      ? 'No generators in this scene'
                      : 'No simulations in this scene')
                  : soon ? 'Coming soon — being reworked'
                  : pct != null ? `${label}: ${pct}% worked through` : undefined}>
                {label}
                {soon && <span className="soon">soon</span>}
                {!disabled && todo > 0 && <span className="badge">{todo}</span>}
                {pct != null && (
                  <span className="tab-progress">
                    <span className={'tab-progress-fill' + tpTone} style={{ width: pct + '%' }} />
                  </span>
                )}
              </button>
            )
          })}
        </nav>
        {score != null && (
          <div className="area-score"
            title="How far this area is worked through — applied fixes and accepted-as-is both count. Reach 100% by deciding on every item.">
            <Ring pct={score} tone={tone} />
            <span className="area-score-label">{tab}<br />{scoreRating(score)}</span>
          </div>
        )}
      </div>

      {error && tab !== 'rules' && <div className="error">{error}</div>}

      {tab === 'overview' && <OverviewTab org={org} />}
      {tab === 'assets' && (
        report
          ? <AssetsTab nodes={report.nodes || []} onFocus={org.doFocus}
              layerNames={(report.layers_report?.layers || []).map((l) => l.name)}
              busy={busy}
              onAssignLayer={org.doAssignLayer} onMoveToGroup={org.doMoveToGroup} />
          : <EmptyState onAction={org.doAnalyze} busy={busy} />
      )}
      {tab === 'naming' && <NamingTab org={org} />}
      {tab === 'translate' && <TranslateTab org={org} />}
      {tab === 'structure' && <StructureTab org={org} />}
      {tab === 'layers' && <LayersTab org={org} />}
      {tab === 'materials' && <MaterialsTab org={org} />}
      {tab === 'rules' && <RulesTab />}
      {tab === 'tags' && <TagsTab org={org} />}
      {tab === 'generators' && <GeneratorsTab org={org} />}
      {tab === 'files' && <FilesTab org={org} />}
      {tab === 'sims' && <SimsTab org={org} />}
      {tab === 'misc' && <MiscTab org={org} />}

      {/* Background work indicator: progress is active but neither the
          blocking overlay (busy) nor an inline preview loader owns it. */}
      {!busy && !previewing && <ProgressChip progress={org.progress} />}
      <StatusBar status={org.status} busy={busy} />
    </div>
  )
}
