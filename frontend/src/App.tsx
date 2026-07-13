// Thin shell: topbar + tab navigation. All state/API flow lives in
// hooks/useOrganizer, each tab in tabs/<Name>Tab.tsx.
import { useState } from 'react'
import { useOrganizer } from './hooks/useOrganizer'
import { version } from '../package.json'
import HandGuide from './components/HandGuide'
import logo from './assets/so_logo.png'
import { TABS } from './lib/constants'
import ScopeToggle from './components/ScopeToggle'
import VisibilityToggle from './components/VisibilityToggle'
import Tip from './components/Tip'
import { IconRefresh } from './components/icons'
import Preloader from './components/Preloader'
import ReloadOverlay from './components/ReloadOverlay'
import GlobalTooltip from './components/GlobalTooltip'
import ProgressChip from './components/ProgressChip'
import EmptyState from './components/EmptyState'
import StatusBar from './components/StatusBar'
import SectionIntro from './components/SectionIntro'
import SupportHeart from './components/SupportHeart'
import type { TabId } from './lib/constants'
import AreaScore from './components/AreaScore'
import { scoreTone } from './lib/score'
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

// Headline + one-line description shown at the top of each area (Overview,
// Naming and Misc intentionally excluded — they carry their own intros).
const TAB_INTRO: Partial<Record<TabId, { title: string; desc: string }>> = {
  translate: { title: 'Translate', desc: 'Translate object names into your target language — offline on your machine, or Google online for any language.' },
  structure: { title: 'Structure', desc: 'Group loose objects into a clean container hierarchy. Generator children stay protected; changes apply as one undo step.' },
  layers: { title: 'Layers', desc: 'Assign objects to layers and tidy the layer table. Nothing changes until you apply a suggestion.' },
  materials: { title: 'Materials', desc: 'Audit materials and textures: unused materials, missing maps, oversized textures and absolute paths.' },
  tags: { title: 'Tags', desc: 'Audit object tags across the scene — missing phong tags and duplicate material tags.' },
  generators: { title: 'Generators', desc: 'Inspect generator objects (Cloner, Array, Subdivision…) and spot heavy parameter values.' },
  files: { title: 'Files', desc: 'External files the scene references — Alembic and simulation caches and other on-disk assets.' },
  sims: { title: 'Sims', desc: 'Simulation setups in the scene — dynamics, cloth, pyro and their cache state.' },
  assets: { title: 'Assets', desc: 'Browse and filter every object in the scene; batch-assign layers or move objects into groups.' },
}

// "Take my hand" is parked for now — flip to bring the guide button back
// (the whole feature stays wired underneath).
const SHOW_HAND_GUIDE = false

export default function App() {
  const org = useOrganizer()
  const { tab, report, error, busy, previewing } = org
  const spinning = busy || previewing
  // "Take my hand" guided mode — reachable from every tab via the small
  // hand button next to the area score.
  const [hand, setHand] = useState(false)
  // Phone layout: the tab nav folds behind a burger button (CSS shows the
  // burger only below the mobile breakpoint; on desktop the nav is always
  // visible and this state is irrelevant).
  const [navOpen, setNavOpen] = useState(false)

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
  // Area score ring in the tab's intro line: how far this area is worked
  // through (fixed OR deliberately accepted both count — 100 is reachable).
  const score = org.areaScore(tab)

  return (
    <div className="app">
      {busy && org.progress?.active && <Preloader progress={org.progress} />}
      {org.reloadProgress && !hand && <ReloadOverlay progress={org.reloadProgress} />}
      {hand && <HandGuide org={org} onExit={() => setHand(false)} />}
      <header className="topbar">
        <div className="brand">
          <img className="brand-logo" src={logo} alt="" />
          <div className="brand-text">
            <span className="brand-title">Overseer
              <span className="brand-version">v{version}</span>
              <SupportHeart />
            </span>
            {report && (
              <span className="scene-meta">
                <span className="scene-name">{report.file || '(scene)'}</span>
              </span>
            )}
          </div>
        </div>

        <div className="topbar-right">
          <Tip text="Scope: “Whole scene” analyzes and changes all objects, “Selection” only the active C4D selection including children.">
            <ScopeToggle scope={org.scope} setScope={org.setScope} sel={org.sel} />
          </Tip>
          <Tip text="Whether objects hidden in the Object Manager are included in statistics and findings.">
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
        <button className="nav-burger" onClick={() => setNavOpen((o) => !o)}
          aria-expanded={navOpen}
          title={navOpen ? 'Close the menu' : 'Open the menu'}>
          <span className="nav-burger-icon">{navOpen ? '✕' : '☰'}</span>
          {TABS.find(([id]) => id === tab)?.[1] || 'Menu'}
        </button>
        <nav className={'tabs' + (navOpen ? ' nav-open' : '')}>
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
            const tpTone = pct == null ? '' : ' tp-' + scoreTone(pct)
            return (
              <button key={id} disabled={disabled}
                className={'tab' + (tab === id ? ' on' : '') + (disabled ? ' off' : '')}
                onClick={() => { if (!disabled) { org.setTab(id); setNavOpen(false) } }}
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
        {/* The area score ring moved into the tab's intro line — only the
            (parked) "Take my hand" entry point still docks right of the tabs. */}
        {tab === 'overview' && SHOW_HAND_GUIDE && (
          <div className="tabs-right">
            <button className="hand-nav-btn" onClick={() => setHand(true)}
              title="Take my hand — let the guide walk you through every area, one clear question at a time. Big groups become a single decision.">
              🫱
            </button>
          </div>
        )}
      </div>

      {error && tab !== 'rules' && <div className="error">{error}</div>}

      {TAB_INTRO[tab] && (
        <SectionIntro lead title={TAB_INTRO[tab]!.title} desc={TAB_INTRO[tab]!.desc}
          aside={<AreaScore score={score} />} />
      )}

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
      <GlobalTooltip />
    </div>
  )
}
