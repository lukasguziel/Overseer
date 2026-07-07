// Thin shell: topbar + tab navigation. All state/API flow lives in
// hooks/useOrganizer, each tab in tabs/<Name>Tab.tsx.
import { useOrganizer } from './hooks/useOrganizer'
import logo from './assets/so_logo.jpg'
import { TABS } from './lib/constants'
import ScopeToggle from './components/ScopeToggle'
import Preloader from './components/Preloader'
import OverviewTab from './tabs/OverviewTab'
import AssetsTab from './tabs/AssetsTab'
import NamingTab from './tabs/NamingTab'
import TranslateTab from './tabs/TranslateTab'
import StructureTab from './tabs/StructureTab'
import LayersTab from './tabs/LayersTab'
import RulesTab from './tabs/RulesTab'
import MiscTab from './tabs/MiscTab'

export default function App() {
  const org = useOrganizer()
  const { tab, report, compliance, error, status, busy, previewing } = org

  return (
    <div className="app">
      {org.progress?.active && <Preloader progress={org.progress} />}
      <header className="topbar">
        <div className="brand"><img className="brand-logo" src={logo} alt="" /> Scene Organizer</div>

        {report && compliance != null && (
          <div className="scene-meta">
            <span className="scene-name">{report.file || '(scene)'}</span>
            {report.scoped && (
              <span className="scope-badge" title="Stats cover only the current selection (incl. children)">
                selection
              </span>
            )}
            <span className="sep">·</span>{report.object_count} objects
            <span className="sep">·</span>
            <span className={'compliance ' + (compliance >= 80 ? 'good' : compliance >= 50 ? 'mid' : 'low')}>
              {compliance}% structured
            </span>
            {report.analyzed_at && (
              <><span className="sep">·</span>
              <span className="dim" title={'Analyzed ' + report.analyzed_at}>
                {report.analyzed_at.slice(11, 16)}
              </span></>
            )}
          </div>
        )}

        <div className="topbar-right">
          <ScopeToggle scope={org.scope} setScope={org.setScope} />
          <span className={'dot ' + (busy || previewing ? 'busy' : error ? 'err' : 'ok')} />
          <span className="status" title={error || status}>{error ? 'error' : status}</span>
        </div>
      </header>

      <nav className="tabs">
        {TABS.map(([id, label]) => (
          <button key={id} className={'tab' + (tab === id ? ' on' : '')} onClick={() => org.setTab(id)}>
            {label}
            {id === 'naming' && (org.naming?.count ?? 0) > 0 && <span className="badge">{org.naming?.count}</span>}
            {id === 'structure' && (org.structure?.count ?? 0) > 0 && <span className="badge">{org.structure?.count}</span>}
          </button>
        ))}
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
      {tab === 'rules' && <RulesTab />}
      {tab === 'misc' && <MiscTab org={org} />}
    </div>
  )
}
