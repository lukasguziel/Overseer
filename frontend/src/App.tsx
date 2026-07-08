// Thin shell: topbar + tab navigation. All state/API flow lives in
// hooks/useOrganizer, each tab in tabs/<Name>Tab.tsx.
import { useOrganizer } from './hooks/useOrganizer'
import logo from './assets/so_logo.jpg'
import { TABS } from './lib/constants'
import ScopeToggle from './components/ScopeToggle'
import VisibilityToggle from './components/VisibilityToggle'
import { IconRefresh } from './components/icons'
import Preloader from './components/Preloader'
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

      <nav className="tabs">
        {TABS.map(([id, label, soon]) => {
          // `soon` tabs (Structure, Rules) are parked — visible but disabled,
          // so the roadmap stays honest without confusing anyone.
          const disabled = !!soon
          return (
            <button key={id} disabled={disabled}
              className={'tab' + (tab === id ? ' on' : '') + (disabled ? ' off' : '')}
              onClick={() => !disabled && org.setTab(id)}
              title={disabled ? 'Coming soon — being reworked' : undefined}>
              {label}
              {disabled && <span className="soon">soon</span>}
              {id === 'naming' && (org.naming?.count ?? 0) > 0 && <span className="badge">{org.naming?.count}</span>}
              {id === 'translate' && (org.translation?.count ?? 0) > 0 && <span className="badge">{org.translation?.count}</span>}
              {id === 'layers' && (report?.layers_report?.no_layer ?? 0) > 0 && <span className="badge">{report?.layers_report?.no_layer}</span>}
              {id === 'materials' && (report?.materials?.unused.length ?? 0) > 0 && <span className="badge">{report?.materials?.unused.length}</span>}
            </button>
          )
        })}
      </nav>

      {error && tab !== 'rules' && <div className="error">{error}</div>}

      {tab === 'overview' && <OverviewTab org={org} />}
      {tab === 'assets' && (
        report
          ? <AssetsTab nodes={report.nodes || []} onFocus={org.doFocus} />
          : <div className="empty-state"><p>No scene analyzed yet.</p>
              <button onClick={org.doAnalyze} disabled={busy}>Analyze scene</button></div>
      )}
      {tab === 'naming' && <NamingTab org={org} />}
      {tab === 'translate' && <TranslateTab org={org} />}
      {tab === 'structure' && <StructureTab org={org} />}
      {tab === 'layers' && <LayersTab org={org} />}
      {tab === 'materials' && <MaterialsTab org={org} />}
      {tab === 'rules' && <RulesTab />}
      {tab === 'misc' && <MiscTab org={org} />}
    </div>
  )
}
