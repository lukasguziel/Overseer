import React, { useState } from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import { CASINGS, exampleName } from '../lib/constants'
import { computeHygiene } from '../lib/hygiene'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedSection from '../components/AcceptedSection'
import Cleanup, { type CleanupBucket } from '../components/Cleanup'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'
import Tip from '../components/Tip'
import { DiffOld, DiffNew } from '../components/DiffText'

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

// Labelled divider between the tab's two areas — same rule/line look as the
// Misc tab, with a one-line description so each area explains itself.
function SectionBand({ title, desc }: { title: string; desc: string }) {
  return (
    <div className="sec-band">
      <div className="misc-sec"><span>{title}</span><hr /></div>
      <p className="sec-desc">{desc}</p>
    </div>
  )
}

export default function NamingTab({ org }: { org: Organizer }) {
  const { report, casing, applyCasing, keepSeparators, keepSpecials, numberPad, applyNumbering, dedupe, naming, busy, previewing, keeps } = org

  const hyg = React.useMemo(
    () => computeHygiene(report?.nodes || [], report?.total_polys || 0,
      { casing, kept: keeps.naming }),
    [report, casing, keeps.naming])
  const nameBuckets: CleanupBucket[] = [
    { key: 'default', label: 'Default names',
      hint: 'Objects still carrying the name Cinema 4D gave them (“Cube”, “Null”, “Light”…) — they say nothing about what the object IS. Give each one a descriptive name: click ✎ to rename it right here, or the name to find it in the viewport first.',
      items: hyg.defaults.map((n) => ({ guid: n.guid, name: n.name, meta: n.type })) },
    { key: 'dupes', label: 'Duplicate names',
      hint: 'The same name is used by several objects (×n = how many). Ambiguous names break the eye in the Object Manager — rename them individually with ✎, or turn on “Make duplicates unique” on the left and let the preview number them for you.',
      items: hyg.dupes.map((d) => ({ guid: d.guid, name: d.name, meta: '×' + d.count })) },
  ]
  const pager = usePager(naming?.diff || [])

  if (!report) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  return (
    <div className="stacked">
      <SectionBand title="Rename rules"
        desc="Set the naming convention on the left; every rename is previewed on the right before you apply anything." />
      <div className="workbench">
        <aside className={'wb-side' + (previewing ? ' side-loading' : '')}>
          <h3>Settings</h3>
          <p className="hint-sm">Toggle which rules apply — all are active by
            default. Every preview row is tagged with the rule that caused it,
            so you always see why a name would change.</p>

          <div className="rule-group-head">
            <Tip text="Casing style of the names — e.g. PascalCase, camelCase or lower_snake. Unifies capitalization and separators without changing the language.">
              <span>Casing</span>
            </Tip>
          </div>
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
              existing separators and special characters stay — <code>-</code>, <code>_</code>,
              brackets &amp; co. <code>Wand-01_test</code> → <code>WAND-01_TEST</code>,
              <code>[test]</code> → <code>[TEST]</code>.</p>
          )}
          {applyCasing && (
            <label className="check" title={keepSeparators
              ? 'Already covered: “Keep separators” keeps every character as-is'
              : 'Keep special characters like [ ] ( ) * — [test] stays [Test] instead of Test'}>
              <input type="checkbox"
                checked={keepSeparators ? true : keepSpecials}
                disabled={keepSeparators}
                onChange={(e) => org.setKeepSpecials(e.target.checked)} />
              Keep special characters
            </label>
          )}
          {applyCasing && !keepSeparators && (
            <p className="hint-sm" style={{ marginTop: 0 }}>
              {keepSpecials
                ? <>Brackets &amp; co. survive full normalization: <code>[test]</code> → <code>[Test]</code>.</>
                : <>Special characters are stripped: <code>[test]</code> → <code>Test</code>.</>}
            </p>
          )}

          <div className="rule-group-head">
            <Tip text="Pad trailing numbers to a fixed digit count (e.g. Wand1 → Wand01). “None” leaves existing numbers unchanged.">
              <span>Numbering</span>
            </Tip>
          </div>
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
          hint="Click a row to select & frame the object in Cinema 4D · ✓ renames it · = keeps the name"
          applyLabel="Apply all" onApply={org.applyNaming}
          onAcceptAll={() => org.keepAll('naming')} busy={busy}
          progress={org.progress}
          note={naming?.applied != null ? `${naming.applied} applied (undoable).` : null}
        >
          <div className="rename-list">
            {pager.rows.map((d) => (
              <SuggestionRow key={d.guid} busy={busy}
                applyTitle="Apply — rename now (undoable)"
                onApply={() => org.applyNamingOne(d.guid, d.old)}
                onAcceptAsIs={() => org.keep('naming', d.old)}
                onFocus={() => org.doFocus(d.guid, d.old)}
              >
                <RuleTags rules={d.rules || ['casing']} />
                <span className="rn-old" title={d.old}><DiffOld oldS={d.old} newS={d.new} /></span>
                <span className="rn-arrow">→</span>
                <span className="rn-new" title={d.new}><DiffNew oldS={d.old} newS={d.new} /></span>
              </SuggestionRow>
            ))}
          </div>
          <Pager pager={pager} />
        </Workbench>
      </div>

      <SectionBand title="Cleanup"
        desc="Objects the rules can't fix on their own: placeholder default names and ambiguous duplicates — rename them by hand or accept them as-is." />

      {/* Name hygiene: default & duplicate names — click to select in C4D. */}
      <section className="card">
        <div className="card-head">
          <h3>Name cleanup</h3>
          <span className="card-hint">click an item to select &amp; frame it · ✎ to rename</span>
        </div>
        <Cleanup buckets={nameBuckets} onFocus={org.doFocus} onRename={org.doRenameObject}
          onKeep={(nm) => org.keep('naming', nm)}
          onKeepAll={(names) => org.keepMany('naming', names)} busy={busy} />
      </section>

      <AcceptedSection items={Array.from(keeps.naming)}
        onRestore={(nm) => org.unkeep('naming', nm)} />
    </div>
  )
}
