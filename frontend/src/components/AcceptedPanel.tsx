import { useState } from 'react'
import { call } from '../api'
import type { Organizer, KeepSection } from '../hooks/useOrganizer'
import { useAuditData, refreshLoadedAudits } from '../hooks/useAudit'
import Pager, { usePager } from './Pager'
import SectionIntro from './SectionIntro'
import ActionButton from './ActionButton'
import './AcceptedSection.css'
import { plural } from '../lib/format'

// EVERYTHING the artist accepted as-is, in one panel, identical on every tab.
//
// It used to be one list per tab, so "accepted" meant something different
// depending on where you stood, and the decisions you made on other tabs were
// invisible. There is only one pile of accepted decisions in a project — this
// shows all of it, grouped by the area it came from, wherever you are.
//
// The sections the plugin persists (core/keeps.py SECTIONS) are the groups.
// Two of them do not live in the keeps state the hook holds: materials and
// textures come back with the analysis, files with the files scan.
type Group = { section: string; label: string; items: string[] }

const KEEP_SECTIONS: KeepSection[] = ['naming', 'translate', 'layers']

const LABELS: Record<string, string> = {
  naming: 'Naming',
  translate: 'Translate',
  layers: 'Layers',
  materials: 'Materials',
  textures: 'Textures',
  files: 'External files',
}

// Which accepted sections belong to which tab. The panel is the SAME component
// everywhere, but it only shows what the artist can act on right here — the
// decisions of other areas are theirs to review on their own tab, not noise on
// this one. A tab that accepts nothing renders no panel at all.
const TAB_SECTIONS: Record<string, string[]> = {
  naming: ['naming'],
  translate: ['translate'],
  layers: ['layers'],
  materials: ['materials', 'textures'],
  files: ['files'],
}

export default function AcceptedPanel({ org }: { org: Organizer }) {
  const [open, setOpen] = useState(false)
  const filesScan = useAuditData<{ accepted?: string[]; accepted_all?: string[] }>('files_scan')

  const mine = TAB_SECTIONS[org.tab] || []
  const groups: Group[] = [
    ...KEEP_SECTIONS.map((s) => ({
      section: s as string, label: LABELS[s], items: Array.from(org.keeps[s]),
    })),
    { section: 'materials', label: LABELS.materials,
      items: org.report?.materials?.accepted_all || [] },
    { section: 'textures', label: LABELS.textures,
      items: org.report?.textures?.accepted_all || [] },
    { section: 'files', label: LABELS.files,
      items: filesScan?.accepted_all || filesScan?.accepted || [] },
  ].filter((g) => mine.includes(g.section) && g.items.length > 0)

  const total = groups.reduce((n, g) => n + g.items.length, 0)
  if (!total) return null

  // Restoring: the four plan-backed sections go through the hook (it owns that
  // state); materials/textures/files are config-only, so they are written back
  // directly and the views that read them are refreshed.
  const isKeepSection = (s: string): s is KeepSection =>
    (KEEP_SECTIONS as string[]).includes(s) || s === 'materials'

  const writeKeeps = (section: string, keys: string[]) => {
    call('set_keeps', { section, keys })
      .then(() => {
        org.doAnalyze()
        if (section === 'files') refreshLoadedAudits()
      })
      .catch((e) => org.setStatus(`Restore ✗ ${String(e.message || e)}`))
  }

  const restore = (g: Group, key: string) => {
    if (isKeepSection(g.section)) org.unkeep(g.section, key)
    else writeKeeps(g.section, g.items.filter((k) => k !== key))
  }
  const restoreGroup = (g: Group) => {
    if (isKeepSection(g.section)) org.unkeepAll(g.section)
    else writeKeeps(g.section, [])
  }

  return (
    <>
      <SectionIntro title="Accepted as-is" doc="accepted"
        desc="Everything you decided to keep, across all areas. Accepted items are remembered (config) and never counted as todos — restore one to make it a todo again." />
      <section className="card kept-card">
        <div className="kept-head-row">
          <button className={'kept-toggle' + (open ? ' on' : '')} aria-expanded={open}
            title={open ? 'Hide the accepted items' : 'Show the accepted items'}
            onClick={() => setOpen(!open)}>
            <span className="kept-caret">▸</span>
            {open ? 'Hide' : 'Show'} {plural(total, 'accepted item')}
            <span className="kept-areas">
              {groups.map((g) => `${g.label} ${g.items.length}`).join(' · ')}
            </span>
          </button>
        </div>
        {open && (
          <div className="kept-groups">
            {groups.map((g) => (
              <AcceptedGroup key={g.section} group={g}
                onRestore={(key) => restore(g, key)}
                onRestoreAll={() => restoreGroup(g)} />
            ))}
          </div>
        )}
      </section>
    </>
  )
}

// One area inside the panel: its name, how many, restore-all, and the items.
function AcceptedGroup({ group, onRestore, onRestoreAll }: {
  group: Group
  onRestore: (key: string) => void
  onRestoreAll: () => void
}) {
  const pager = usePager([...group.items].sort())
  return (
    <div className="kept-group">
      <div className="section-head sm">
        <span>{group.label}</span>
        <span className="kept-group-n">{group.items.length}</span>
        <ActionButton
          title={`Restore every accepted item in ${group.label} — they all become todos again`}
          onClick={onRestoreAll}>Restore all</ActionButton>
      </div>
      <div className="kept-list">
        {pager.rows.map((key) => (
          <div className="kept-row" key={key}>
            <span className="fl-name" title={key}>{key}</span>
            <ActionButton title="Restore this item — it counts as a todo again"
              onClick={() => onRestore(key)}>Restore</ActionButton>
          </div>
        ))}
      </div>
      <Pager pager={pager} />
    </div>
  )
}
