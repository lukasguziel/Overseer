import React, { useState } from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import { CASINGS, exampleName } from '../lib/constants'
import { computeHygiene } from '../lib/hygiene'
import Workbench from '../components/Workbench'
import Cleanup, { type CleanupBucket } from '../components/Cleanup'

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

export default function NamingTab({ org }: { org: Organizer }) {
  const { report, casing, applyCasing, numberPad, applyNumbering, dedupe, naming, busy, previewing, keepNames } = org
  const [showKept, setShowKept] = useState(false)
  const kept = Array.from(keepNames).sort()

  const hyg = React.useMemo(
    () => computeHygiene(report?.nodes || [], report?.total_polys || 0),
    [report])
  const nameBuckets: CleanupBucket[] = [
    { key: 'default', label: 'Default names', items: hyg.defaults.map((n) => ({ guid: n.guid, name: n.name, meta: n.type })) },
    { key: 'dupes', label: 'Duplicate names', items: hyg.dupes.map((d) => ({ guid: d.guid, name: d.name, meta: '×' + d.count })) },
  ]
  const rows = naming?.diff || []

  return (
    <div className="stacked">
      <div className="workbench">
        <aside className="wb-side">
          <h3>Rules</h3>
          <p className="hint-sm">Toggle the rules to apply — all active by
            default. Each row shows which rule changed it, so you decide.</p>

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

          <div className="rule-group-head"><span>Numbering</span></div>
          <label className="check">
            <input type="checkbox" checked={applyNumbering} onChange={(e) => org.setApplyNumbering(e.target.checked)} />
            Numbering
          </label>
          {applyNumbering
            ? (
              <label>Pad <b>{numberPad === 0 ? 'none' : numberPad + '-digit'}</b>
                <input type="range" min="0" max="4" value={numberPad}
                  onChange={(e) => org.setNumberPad(Number(e.target.value))} />
              </label>
            )
            : <p className="hint-sm" style={{ marginTop: 0 }}>Numbers kept exactly as they are.</p>}

          <label className="check">
            <input type="checkbox" checked={dedupe} onChange={(e) => org.setDedupe(e.target.checked)} />
            Make duplicates unique
          </label>

          {applyCasing && casing !== '' && applyNumbering && <div className="example">e.g. <code>{exampleName(casing, numberPad)}</code></div>}
          <p className="hint-sm">Only casing &amp; numbers — never the language, and
            never swallows info (a name like <code>ROCK_UV_2.1</code> keeps its dot).
            To translate names, use the <b>Translate</b> tab.</p>
        </aside>

        <Workbench
          title="Rename preview" count={naming?.count ?? 0} loading={previewing}
          empty="Every name already matches these rules (or is kept)."
          applyLabel="Process all" onApply={org.applyNaming} busy={busy}
          note={naming?.applied != null ? `${naming.applied} applied (undoable).` : null}
        >
          <div className="rename-list">
            {rows.slice(0, 300).map((d) => (
              <div className="rename-row" key={d.guid}>
                <RuleTags rules={d.rules || ['casing']} />
                <span className="rn-old" title={d.old}>{d.old}</span>
                <span className="rn-arrow">→</span>
                <span className="rn-new" title={d.new}>{d.new}</span>
                <span className="rn-actions">
                  <button className="rn-ok" title="Accept — rename now (undoable)"
                    onClick={() => org.applyNamingOne(d.guid, d.old)} disabled={busy}>✓</button>
                  <button className="rn-no" title="Ignore — keep this name as-is"
                    onClick={() => org.keepName(d.old)} disabled={busy}>✕</button>
                </span>
              </div>
            ))}
          </div>
        </Workbench>
      </div>

      {/* Ignored / kept-as-is names, collapsed. */}
      {kept.length > 0 && (
        <section className="card">
          <button className="kept-head" onClick={() => setShowKept(!showKept)}>
            <span className="cl-caret">{showKept ? '▾' : '▸'}</span>
            Ignored — kept as-is <span className="kept-count">{kept.length}</span>
          </button>
          {showKept && (
            <div className="kept-list">
              {kept.map((nm) => (
                <div className="kept-row" key={nm}>
                  <span className="fl-name" title={nm}>{nm}</span>
                  <button className="kept-restore" title="Un-keep — allow renaming again"
                    onClick={() => org.unkeepName(nm)}>restore</button>
                </div>
              ))}
            </div>
          )}
          <p className="hint-sm" style={{ marginTop: 8 }}>
            Kept names are remembered (config) and never counted as problems.
          </p>
        </section>
      )}

      {/* Name hygiene: default & duplicate names — click to select in C4D. */}
      <section className="card">
        <div className="card-head">
          <h3>Name cleanup</h3>
          <span className="dim" style={{ fontSize: 11 }}>click an item to select &amp; frame it</span>
        </div>
        <Cleanup buckets={nameBuckets} onFocus={org.doFocus} />
      </section>
    </div>
  )
}
