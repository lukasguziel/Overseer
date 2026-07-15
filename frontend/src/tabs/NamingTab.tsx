import React, { useState } from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import { CASINGS, exampleName } from '../lib/constants'
import { computeHygiene } from '../lib/hygiene'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedPanel from '../components/AcceptedPanel'
import AreaHistory from '../components/AreaHistory'
import Cleanup, { type CleanupBucket } from '../components/Cleanup'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'
import Tip from '../components/Tip'
import { DiffOld, DiffNew } from '../components/DiffText'
import SectionIntro from '../components/SectionIntro'
import AreaScore from '../components/AreaScore'
import { plural } from '../lib/format'

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

// One rename rule in the settings sidebar: the section head carries the on/off
// switch, and the controls below only exist while the rule is on — switched off
// it collapses to a single line stating what stays untouched.
function RuleSection({ title, tip, on, onToggle, off, children }: {
  title: string
  tip: string
  on: boolean
  onToggle: (v: boolean) => void
  off: string
  children: React.ReactNode
}) {
  return (
    <div className={'rule-section' + (on ? '' : ' is-off')}>
      <div className="section-head sm">
        <label className="check rule-switch" title={on ? `Turn the ${title.toLowerCase()} rule off` : `Turn the ${title.toLowerCase()} rule on`}>
          <input type="checkbox" checked={on} onChange={(e) => onToggle(e.target.checked)} />
          <Tip text={tip}><span>{title}</span></Tip>
        </label>
      </div>
      {on ? children : <p className="hint-sm tight">{off}</p>}
    </div>
  )
}

const DEFAULT_PAD = 2

export default function NamingTab({ org }: { org: Organizer }) {
  const { report, casing, applyCasing, keepSeparators, keepSpecials, numberPad, applyNumbering, dedupe, naming, busy, previewing, keeps } = org

  // With the rule on, a pad is always chosen — pad 0 ("no padding") is what the
  // rule being OFF means, so the two must not be expressible at the same time.
  const padDigits = numberPad > 0 ? numberPad : DEFAULT_PAD
  const enableNumbering = (on: boolean) => {
    if (on && numberPad === 0) org.setNumberPad(DEFAULT_PAD)
    org.setApplyNumbering(on)
  }

  const hyg = React.useMemo(
    () => computeHygiene(report?.nodes || [], report?.total_polys || 0,
      { casing, kept: keeps.naming }),
    [report, casing, keeps.naming])
  const nameBuckets: CleanupBucket[] = [
    { key: 'default', label: 'Default names',
      hint: 'Objects still carrying the name Cinema 4D gave them (“Cube”, “Null”, “Light”…) — they say nothing about what the object IS. Give each one a descriptive name: click ✎ to rename it right here, or the name to find it in the viewport first.',
      items: hyg.defaults.map((n) => ({ guid: n.guid, name: n.name, meta: n.type })),
      empty: 'Every object carries a descriptive name' },
    { key: 'dupes', label: 'Duplicate names',
      hint: 'The same name is used by several objects (×n = how many). Ambiguous names break the eye in the Object Manager — rename them individually with ✎, or turn on “Make duplicates unique” on the left and let the preview number them for you.',
      items: hyg.dupes.map((d) => ({ guid: d.guid, name: d.name, meta: '×' + d.count })),
      empty: 'No name is used twice within the same group' },
  ]
  const pager = usePager(naming?.diff || [], 10)
  // Open cleanup items (default + duplicate names not yet renamed/accepted) —
  // when the rename preview is empty but these remain, nudge the user down.
  const openCleanup = hyg.defaults.length + hyg.dupes.length

  if (!report) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  return (
    <div className="stacked">
      <SectionIntro title="Rename rules" doc="naming-preview"
        desc="Set the naming convention on the left; every rename is previewed on the right before you apply anything."
        aside={<AreaScore score={org.areaScore('naming')} />} />
      <div className="workbench">
        <aside className={'wb-side' + (previewing ? ' side-loading' : '')}>
          <h3>Settings</h3>

          {/* The section head IS the on/off switch — the rule's name was
              printed twice before: once as the heading, once as the checkbox
              next to it. */}
          <RuleSection title="Casing" on={applyCasing} onToggle={org.setApplyCasing}
            tip="Casing style of the names — e.g. PascalCase, camelCase or lower_snake. Unifies capitalization and separators without changing the language."
            off="Casing and separators kept as-is.">
            <label>Style
              <select value={casing} onChange={(e) => org.setCasing(e.target.value)}>
                {casing === '' && <option value="">Choose preferred casing…</option>}
                {CASINGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            <label className="check">
              <input type="checkbox" checked={keepSeparators}
                onChange={(e) => org.setKeepSeparators(e.target.checked)} />
              Keep separators
            </label>
            <label className="check" title={keepSeparators
              ? 'Already covered: “Keep separators” keeps every character as-is'
              : 'Keep special characters like [ ] ( ) * — [test] stays [Test] instead of Test'}>
              <input type="checkbox"
                checked={keepSeparators ? true : keepSpecials}
                disabled={keepSeparators}
                onChange={(e) => org.setKeepSpecials(e.target.checked)} />
              Keep special characters
            </label>
            <p className="hint-sm tight">
              {keepSeparators
                ? <>Only word case changes — <code>Wand-01_test</code> → <code>WAND-01_TEST</code>.</>
                : keepSpecials
                  ? <>Brackets &amp; co. survive: <code>[test]</code> → <code>[Test]</code>.</>
                  : <>Special characters are stripped: <code>[test]</code> → <code>Test</code>.</>}
            </p>
          </RuleSection>

          {/* The rule's switch is "off" — the pad picker itself always has a
              value. Clicking the selected digit again does nothing; there is no
              such thing as numbering-on-but-padded-by-nothing. */}
          <RuleSection title="Numbering" on={applyNumbering} onToggle={enableNumbering}
            tip="Pad trailing numbers to a fixed digit count (e.g. Wand1 → Wand01)."
            off="Numbers kept exactly as they are.">
            {/* NOT a <label>: a label forwards any click inside it to the first
                control it contains, so clicking the caption or the gap between
                the digits silently selected "1". */}
            <div className="pad-field">Pad <b>{padDigits}-digit</b>
              <div className="pad-btns">
                {[1, 2, 3, 4].map((p) => (
                  <button key={p} type="button"
                    className={'pad-btn' + (padDigits === p ? ' on' : '')}
                    onClick={() => org.setNumberPad(p)}
                    title={`${p}-digit padding`}>
                    {p}
                  </button>
                ))}
              </div>
              {applyCasing && casing !== '' && <div className="example">e.g. <code>{exampleName(casing, padDigits)}</code></div>}
            </div>
          </RuleSection>

          <RuleSection title="Duplicates" on={dedupe} onToggle={org.setDedupe}
            tip="Objects sharing a name get a number appended, so every name is unique."
            off="Duplicate names are left alone.">
            <div className="example tight">e.g. <code>Wall, Wall</code> → <code>Wall{pad(1, numberPad)}, Wall{pad(2, numberPad)}</code></div>
          </RuleSection>
        </aside>

        <Workbench
          title="Rename preview" count={naming?.count ?? 0} loading={previewing}
          empty={
            <>
              Every name already matches your rules
              {openCleanup > 0 && (
                <span className="wb-empty-more">
                  Check the cleanup area below for {plural(openCleanup, 'open item')}
                  <span className="wb-empty-arrow">↓</span>
                </span>
              )}
            </>
          }
          hint="Click a row to select & frame the object in Cinema 4D · the green ✓ renames it · the grey one keeps the name"
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

      {/* Name cleanup: intro, then the area itself — no card wrapping a card,
          and no second heading repeating the intro's title (same shape as
          Materials and Textures). Objects the rules cannot fix on their own. */}
      <SectionIntro title="Name cleanup" doc="naming-cleanup"
        desc="Objects the rules can't fix on their own: placeholder default names and ambiguous duplicates. Click an item to select & frame it, ✎ renames it, the grey ✓ accepts it as-is." />
      {/* Two OWN areas side by side — one card per bucket, not one shared card. */}
      <div className="ov-cols2">
        {nameBuckets.map((b) => (
          <section className="card" key={b.key}>
            <Cleanup buckets={[b]} onFocus={org.doFocus} onRename={org.doRenameObject}
              onKeep={(nm) => org.keep('naming', nm)}
              onKeepAll={(names) => org.keepMany('naming', names)} busy={busy} />
          </section>
        ))}
      </div>

    <AcceptedPanel org={org} />
    <AreaHistory org={org} area="naming" kinds={['naming']} field="name" />
    </div>
  )
}
