// Thin shell: topbar + tab navigation. All state/API flow lives in
// hooks/useOrganizer, each tab in tabs/<Name>Tab.tsx.
import { useOrganizer } from './hooks/useOrganizer'
import logo from './assets/so_logo.jpg'
import { TABS } from './lib/constants'
import ScopeToggle from './components/ScopeToggle'
import VisibilityToggle from './components/VisibilityToggle'
import { IconRefresh } from './components/icons'
import Preloader from './components/Preloader'
import EmptyState from './components/EmptyState'
import StatusBar from './components/StatusBar'
import Ring, { type Tone } from './components/Ring'
import OverviewTab from './tabs/OverviewTab'
import AssetsTab from './tabs/AssetsTab'
import NamingTab from './tabs/NamingTab'
import TranslateTab from './tabs/TranslateTab'
import StructureTab from './tabs/StructureTab'
import LayersTab from './tabs/LayersTab'
import MaterialsTab from './tabs/MaterialsTab'
import RulesTab from './tabs/RulesTab'
import MiscTab from './tabs/MiscTab'

export default function App() {
  const org = useOrganizer()
  const { tab, report, error, busy, previewing } = org
  const spinning = busy || previewing
  // Area score ring next to the nav: how far this area is worked through
  // (fixed OR deliberately accepted both count — 100 is always reachable).
  const score = org.areaScore(tab)
  const tone: Tone = score == null ? 'low' : score >= 80 ? 'good' : score >= 50 ? 'mid' : 'low'

  return (
    <div className="app">
      {busy && org.progress?.active && <Preloader progress={org.progress} />}
      <header className="topbar">
        <div className="brand">
          <img className="brand-logo" src={logo} alt="" />
          <div className="brand-text">
            <span className="brand-title">Scene Organizer</span>
            {report && (
              <span className="scene-meta">
                <span className="scene-name">{report.file || '(scene)'}</span>
              </span>
            )}
          </div>
        </div>

        <div className="topbar-right">
          <ScopeToggle scope={org.scope} setScope={org.setScope} sel={org.sel} />
          <VisibilityToggle includeHidden={org.includeHidden} setIncludeHidden={org.setIncludeHidden}
            hidden={report?.hidden_count} />
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
            const disabled = !!soon
            // Uniform todo badge per area (live plan count, report fallback).
            const todo = org.planCount(id) ?? 0
            return (
              <button key={id} disabled={disabled}
                className={'tab' + (tab === id ? ' on' : '') + (disabled ? ' off' : '')}
                onClick={() => !disabled && org.setTab(id)}
                title={disabled ? 'Coming soon — being reworked' : undefined}>
                {label}
                {disabled && <span className="soon">soon</span>}
                {!disabled && todo > 0 && <span className="badge">{todo}</span>}
              </button>
            )
          })}
        </nav>
        {score != null && (
          <div className="area-score"
            title="How far this area is worked through — applied fixes and accepted-as-is both count. Reach 100% by deciding on every item.">
            <Ring pct={score} tone={tone} />
            <span className="area-score-label">{tab}<br />score</span>
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
      {tab === 'misc' && <MiscTab org={org} />}

      <StatusBar status={org.status} busy={busy} />
    </div>
  )
}
