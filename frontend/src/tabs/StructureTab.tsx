import React from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import { computeHygiene } from '../lib/hygiene'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedSection from '../components/AcceptedSection'
import Cleanup, { type CleanupBucket } from '../components/Cleanup'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'
import Tip from '../components/Tip'

export default function StructureTab({ org }: { org: Organizer }) {
  const { report, tidy, safe, rules, structure, keeps, busy, previewing } = org

  const hyg = React.useMemo(
    () => computeHygiene(report?.nodes || [], report?.total_polys || 0),
    [report])
  const pager = usePager(structure?.diff || [])
  const notKept = (n: { name: string }) => !keeps.structure.has(n.name)
  const groupBuckets: CleanupBucket[] = [
    { key: 'empty', label: 'Empty groups', items: hyg.emptyGroups.filter(notKept).map((n) => ({ guid: n.guid, name: n.name })) },
    { key: 'root', label: 'Root clutter', items: hyg.rootClutter.filter(notKept).map((n) => ({ guid: n.guid, name: n.name, meta: n.type })) },
  ]

  if (!report) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  return (
    <div className="stacked">
      <div className="workbench">
        <aside className={'wb-side' + (previewing ? ' side-loading' : '')}>
          <h3>Options</h3>
          <label className="check">
            <input type="checkbox" checked={tidy} onChange={(e) => org.setTidy(e.target.checked)} />
            <Tip text="Collects only loose objects into their group. Objects already inside a group (even nested) are left untouched — the hierarchy is never flattened.">
              <span>Tidy mode</span>
            </Tip>
          </label>
          <p className="hint-sm">
            Only collects <b>loose</b> objects into their group. Objects already
            inside a (even nested) group are left untouched — your hierarchy is
            never flattened. Turn off for aggressive flat regrouping.
          </p>
          <label className="check">
            <input type="checkbox" checked={safe} onChange={(e) => org.setSafe(e.target.checked)} />
            <Tip text="Protects generator children (Cloner, Boole, Sweep …) from being moved.">
              <span>Safety filter</span>
            </Tip>
          </label>
          <p className="hint-sm">Protects generator children (Cloner, Boole, Sweep …) from being moved.</p>
          {!tidy && <p className="wb-note" style={{ padding: '8px 0' }}>⚠ Aggressive mode can pull objects out of existing groups and flatten spatial nesting.</p>}

          <h3>Target groups</h3>
          {rules?.groups?.length
            ? <ul className="grouplist">
                {rules.groups.map((g) => <li key={g.name}><b>{g.name}</b><span>{g.priority}</span></li>)}
              </ul>
            : <p className="hint-sm">No rules yet.</p>}
          <button className="ghost" onClick={() => org.setTab('rules')}>Edit rules →</button>
        </aside>

        <Workbench
          title="Regroup preview" count={structure?.count ?? 0} loading={previewing}
          empty="Everything is already in the right group 🎉"
          hint="Click a row to select & frame the object in Cinema 4D · ✓ moves it · = keeps its place"
          applyLabel="Apply all" onApply={org.applyStructure}
          onAcceptAll={() => org.keepAll('structure')} busy={busy}
          progress={org.progress}
          note={
            structure?.applied != null ? `${structure.applied} applied (undoable).`
              : (structure?.skipped ?? 0) > 0 ? `${structure?.skipped} protected by the safety filter.` : null
          }
        >
          <div className="rename-list">
            {pager.rows.map((d) => (
              <SuggestionRow key={d.guid} busy={busy}
                applyTitle="Apply — move into its group now (undoable)"
                onApply={() => org.applyStructureOne(d.guid, d.name)}
                onAcceptAsIs={() => org.keep('structure', d.name)}
                onFocus={() => org.doFocus(d.guid, d.name)}
              >
                <span className="rn-old" title={d.from || '(root)'}>{d.name}</span>
                <span className="rn-arrow">→</span>
                <span className="rn-new dim">{d.to}</span>
              </SuggestionRow>
            ))}
          </div>
          <Pager pager={pager} />
        </Workbench>
      </div>

      <AcceptedSection items={Array.from(keeps.structure)}
        onRestore={(nm) => org.unkeep('structure', nm)} />

      {/* Structure hygiene: empty containers & loose root objects. */}
      <section className="card">
        <div className="card-head">
          <h3>Structure cleanup</h3>
          <span className="card-hint">click an item to select &amp; frame it</span>
        </div>
        <Cleanup buckets={groupBuckets} onFocus={org.doFocus}
          onKeep={(nm) => org.keep('structure', nm)}
          onKeepAll={(names) => org.keepMany('structure', names)} busy={busy} />
      </section>
    </div>
  )
}
