import React, { useState } from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import { CASINGS, exampleName } from '../lib/constants'
import { computeHygiene } from '../lib/hygiene'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedSection from '../components/AcceptedSection'
import Cleanup, { type CleanupBucket } from '../components/Cleanup'
import Pager, { usePager } from '../components/Pager'

// Rule chips for a rename. One rule → shown inline. Several → collapsed behind
// a count chip you click to reveal them all (a rename can trigger more than
// one rule, e.g. casing + unique).
function RuleTags({ rules }: { rules: string[] }) {
  const [open, setOpen] = useState(false)
  const list = rules.length ? rules : ['casing']
  if (list.length === 1) {
    return <span className={'rule-tag rt-' + list[0]}>{list[0]}</span>
  }
  if (!open) {
    return (
      <button className="rule-tag rule-count" title={list.join(' + ')}
        onClick={() => setOpen(true)}>{list.length} rules</button>
    )
  }
  return (
    <span className="rule-tags" onClick={() => setOpen(false)} title="click to collapse">
      {list.map((r) => <span key={r} className={'rule-tag rt-' + r}>{r}</span>)}
    </span>
  )
}

const pad = (n: number, p: number) => (p > 0 ? String(n).padStart(p, '0') : String(n))

export default function NamingTab({ org }: { org: Organizer }) {
  const { report, casing, applyCasing, keepSeparators, numberPad, applyNumbering, dedupe, naming, busy, previewing, keeps } = org

  const hyg = React.useMemo(
    () => computeHygiene(report?.nodes || [], report?.total_polys || 0),
    [report])
  const nameBuckets: CleanupBucket[] = [
    { key: 'default', label: 'Default names', items: hyg.defaults.map((n) => ({ guid: n.guid, name: n.name, meta: n.type })) },
    { key: 'dupes', label: 'Duplicate names', items: hyg.dupes.map((d) => ({ guid: d.guid, name: d.name, meta: '×' + d.count })) },
  ]
  const pager = usePager(naming?.diff || [])

  return (
    <div className="stacked">
      <div className="workbench">
        <aside className="wb-side">
          <h3>Settings</h3>
          <p className="hint-sm">Toggle the settings to apply — all active by
            default. Each row shows which setting changed it, so you decide.</p>

          <div className="rule-group-head"><span>Casing</span></div>
          <label className="check">
            <input type="checkbox" checked={applyCasing} onChange={(e) => org.setApplyCasing(e.target.checked)} />
            Casing
          </label>
          {applyCasing
            ? (
              <label>Style
                <select value={casing} onChange={(e) => org.setCasing(e.target.value)}>
                  {casing === '' && <option value="">Choose preferred casing…</option>}
                  {CASINGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </label>
            )
            : <p className="hint-sm" style={{ marginTop: 0 }}>Casing &amp; separators kept as-is.</p>}
          {applyCasing && (
            <label className="check">
              <input type="checkbox" checked={keepSeparators}
                onChange={(e) => org.setKeepSeparators(e.target.checked)} />
              Keep separators
            </label>
          )}
          {applyCasing && keepSeparators && (
            <p className="hint-sm" style={{ marginTop: 0 }}>Only word case changes;
              existing separators (e.g. <code>-</code>) stay. <code>Wand-01_test</code> → <code>WAND-01_TEST</code>.</p>
          )}

          <div className="rule-group-head"><span>Numbering</span></div>
          <label className="check">
            <input type="checkbox" checked={applyNumbering} onChange={(e) => org.setApplyNumbering(e.target.checked)} />
            Numbering
          </label>
          {applyNumbering
            ? (
              <label>Pad <b>{numberPad === 0 ? 'none' : numberPad + '-digit'}</b>
                <div className="pad-btns">
                  {[1, 2, 3, 4].map((p) => (
                    <button key={p} type="button"
                      className={'pad-btn' + (numberPad === p ? ' on' : '')}
                      onClick={() => org.setNumberPad(numberPad === p ? 0 : p)}
                      title={p + '-digit padding' + (numberPad === p ? ' — click again for none' : '')}>
                      {p}
                    </button>
                  ))}
                </div>
                {applyCasing && casing !== '' && <div className="example">e.g. <code>{exampleName(casing, numberPad)}</code></div>}
              </label>
            )
            : <p className="hint-sm" style={{ marginTop: 0 }}>Numbers kept exactly as they are.</p>}

          <label className="check">
            <input type="checkbox" checked={dedupe} onChange={(e) => org.setDedupe(e.target.checked)} />
            Make duplicates unique
          </label>
          {dedupe && (
            <div className="example">e.g. <code>Wall, Wall</code> → <code>Wall{pad(1, numberPad)}, Wall{pad(2, numberPad)}</code></div>
          )}
          <p className="hint-sm">Only casing &amp; numbers — never the language, and
            never swallows info (a name like <code>ROCK_UV_2.1</code> keeps its dot).
            To translate names, use the <b>Translate</b> tab.</p>
        </aside>

        <Workbench
          title="Rename preview" count={naming?.count ?? 0} loading={previewing}
          empty="Every name already matches your rules 🎉"
          applyLabel="Process all" onApply={org.applyNaming} busy={busy}
          progress={org.progress}
          note={naming?.applied != null ? `${naming.applied} applied (undoable).` : null}
        >
          <div className="rename-list">
            {pager.rows.map((d) => (
              <SuggestionRow key={d.guid} busy={busy}
                applyTitle="Apply — rename now (undoable)"
                onApply={() => org.applyNamingOne(d.guid, d.old)}
                onAcceptAsIs={() => org.keep('naming', d.old)}
              >
                <RuleTags rules={d.rules || ['casing']} />
                <span className="rn-old" title={d.old}>{d.old}</span>
                <span className="rn-arrow">→</span>
                <span className="rn-new" title={d.new}>{d.new}</span>
              </SuggestionRow>
            ))}
          </div>
          <Pager pager={pager} />
        </Workbench>
      </div>

      <AcceptedSection items={Array.from(keeps.naming)}
        onRestore={(nm) => org.unkeep('naming', nm)} />

      {/* Name hygiene: default & duplicate names — click to select in C4D. */}
      <section className="card">
        <div className="card-head">
          <h3>Name cleanup</h3>
          <span className="card-hint">click an item to select &amp; frame it</span>
        </div>
        <Cleanup buckets={nameBuckets} onFocus={org.doFocus} />
      </section>
    </div>
  )
}
