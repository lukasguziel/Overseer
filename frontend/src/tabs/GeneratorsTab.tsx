import { useEffect, useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import useAudit from '../hooks/useAudit'
import EmptyState from '../components/EmptyState'
import SuggestionRow from '../components/SuggestionRow'
import ConfirmModal from '../components/ConfirmModal'
import Pager, { usePager } from '../components/Pager'
import BarList from '../components/BarList'
import Tip from '../components/Tip'
import './generators.css'
import ActionButton from '../components/ActionButton'
import { plural } from '../lib/format'

type ParamKind = 'int' | 'bool' | 'choice'

interface GenValue { guid: number; name: string; value: any }
interface GenBucket { value: any; count: number }
interface GenParam {
  key: string
  label: string
  kind: ParamKind
  choices: Record<string, string>
  values: GenValue[]
  distribution: GenBucket[]
  uniform: boolean
  dominant: any
  outliers: GenValue[]
}
interface GenType { key: string; label: string; type_id: number; count: number; params: GenParam[] }
interface GenScan {
  ok: boolean
  types: GenType[]
  summary: { total_generators: number; types_found: number; non_uniform_params: number }
}

// Human-readable value: dropdown values use C4D's own labels (delivered by
// the scan), booleans read on/off — raw ids never reach the screen.
function fmt(value: any, param: GenParam): string {
  if (value === null || value === undefined || value === '') return '—'
  if (param.kind === 'bool') return value ? 'On' : 'Off'
  if (param.kind === 'choice') {
    const label = param.choices?.[String(value)]
    return label || `#${value}`
  }
  if (Array.isArray(value)) return value.map((n) => Number(n).toFixed(2)).join(', ')
  return String(value)
}

function sameValue(a: any, b: any): boolean {
  if (Array.isArray(a) && Array.isArray(b)) return JSON.stringify(a) === JSON.stringify(b)
  return a === b
}

// One MIXED parameter: plain-language headline, the value spread as chips
// (dominant first, outliers amber), then the fix row and the object list.
function MixedParam({ type, param, busy, onApply, onSelectValue }: {
  type: GenType
  param: GenParam
  busy: boolean
  onApply: (param: GenParam, value: any, guids: number[] | undefined, count: number) => void
  onSelectValue: (param: GenParam, value: any) => void
}) {
  const [pick, setPick] = useState<any>(param.dominant)
  const [open, setOpen] = useState(false)
  const pager = usePager(param.outliers)
  const offCount = param.outliers.length
  const sorted = [...param.distribution].sort((a, b) => b.count - a.count)

  // A rescan can drop the picked value from the distribution; without this the
  // select would show something else while `pick` still applies the vanished value.
  const stale = param.kind !== 'int'
    && !param.distribution.some((b) => sameValue(b.value, pick))
  const value = stale ? param.dominant : pick

  return (
    <div className="gens-param">
      <div className="gens-param-head">
        <span className="gens-param-label">{param.label}</span>
        <span className="gens-mixed-note">
          most use <b>{fmt(param.dominant, param)}</b> — {plural(offCount, 'object')} differ{offCount === 1 ? 's' : ''}
        </span>
      </div>
      {/* READ row: the values as they are right now — neutral chips, purely
          informational (click = select those objects in C4D). */}
      <div className="gens-row">
        <Tip text="The values currently set in the scene — informational only. Click a value chip to select the affected objects in Cinema 4D.">
          <span className="gens-microlabel">Current values</span>
        </Tip>
        <div className="gens-chips">
          {sorted.map((b, i) => {
            const dom = sameValue(b.value, param.dominant)
            return (
              <button key={i} className={'gens-chip' + (dom ? ' dom' : '')}
                title={`${plural(b.count, 'object')} — click to select them in Cinema 4D`}
                onClick={() => onSelectValue(param, b.value)}>
                <span className="gens-chip-val">{fmt(b.value, param)}</span>
                <span className="gens-chip-n">×{b.count}</span>
                {dom && <span className="gens-chip-most">most</span>}
              </button>
            )
          })}
          <button className="gens-toggle" onClick={() => setOpen((v) => !v)}>
            {open ? '▾ hide' : '▸ show'} the {offCount} differing
          </button>
        </div>
      </div>
      {/* WRITE row: the one editable thing in this block. */}
      <div className="gens-row gens-row-action">
        <Tip text="Sets this setting on all objects of this generator type to the chosen value — in a single undoable step.">
          <span className="gens-microlabel accent">Change all to</span>
        </Tip>
        {param.kind === 'int' ? (
          <input className="gens-num" type="number" value={value ?? ''}
            onChange={(e) => setPick(e.target.value === '' ? '' : Number(e.target.value))} />
        ) : (
          <select className="gens-select" value={JSON.stringify(value)}
            onChange={(e) => setPick(JSON.parse(e.target.value))}>
            {sorted.map((b, i) => (
              <option key={i} value={JSON.stringify(b.value)}>{fmt(b.value, param)}</option>
            ))}
          </select>
        )}
        <button className="apply gens-align-btn" disabled={busy || value === ''}
          title={`Set ${param.label} to ${fmt(value, param)} on all ${type.count} ${type.label} objects (one undo step)`}
          onClick={() => onApply(param, value, undefined, type.count)}>
          ✓ Apply to all {type.count}
        </button>
      </div>
      {open && (
        <div className="rename-list gens-outliers">
          {pager.rows.map((o) => (
            <SuggestionRow key={o.guid} busy={busy}
              applyTitle={`Set this object's ${param.label} to ${fmt(param.dominant, param)} (undoable)`}
              onApply={() => onApply(param, param.dominant, [o.guid], 1)}
              onFocus={() => call('focus', { guid: o.guid })}>
              <span className="rn-old" title={o.name}>{o.name}</span>
              <span className="gens-had">{fmt(o.value, param)}</span>
              <span className="rn-arrow">→</span>
              <span className="rn-new">{fmt(param.dominant, param)}</span>
            </SuggestionRow>
          ))}
          <Pager pager={pager} />
        </div>
      )}
    </div>
  )
}

interface PerfEntry {
  guid: number; name: string; type: string
  ms: number; jitter_ms: number; runs: number
  share: number; level: 'heavy' | 'mid' | 'light'; polygons: number
}
interface PerfScan {
  entries: PerfEntry[]
  baseline_ms: number
  summary: {
    total: number; measured: number; total_ms: number; heavy: number
    slowest: string; slowest_ms: number; slowest_share: number
    scene_ms: number; overlap: number
  }
}

const ms1 = (n: number) => `${n < 10 ? n.toFixed(1) : Math.round(n)} ms`
const LEVEL_COLOR: Record<string, string> = {
  heavy: 'var(--err)', mid: 'var(--warn)', light: 'var(--dim2)',
}

// Rebuild cost per generator/deformer: what actually stalls the viewport.
// Measured on demand — it rebuilds every generator once, which takes real
// seconds on a big scene, so it must never run behind the user's back.
function PerfCard() {
  const [perf, setPerf] = useState<PerfScan | null>(null)
  const [measuring, setMeasuring] = useState(false)
  const [error, setError] = useState('')

  const measure = () => {
    setMeasuring(true)
    setError('')
    call<PerfScan>('perf_scan')
      .then((r) => setPerf(r))
      .catch((e) => setError(String(e.message || e)))
      .finally(() => setMeasuring(false))
  }

  const s = perf?.summary
  // Below 0.5 ms a "cost" is timer noise, not work — those rows are counted,
  // not listed (listing them is what made the list flicker between scans).
  const above = (perf?.entries || []).filter((e) => e.ms >= 0.5)
  const belowNoise = (perf?.entries.length || 0) - above.length
  const rows = above.slice(0, 15).map((e) => ({
    label: e.name,
    sub: `${e.type} · ${Math.round(e.share * 100)}% of the rebuild`,
    value: e.ms,
    color: LEVEL_COLOR[e.level],
    onClick: () => { call('perf_select', { guids: [e.guid] }).catch(() => {}) },
  }))
  // A value is only as good as it is repeatable: if the runs disagree by more
  // than the value itself, say so instead of pretending the number is solid.
  const shaky = above.filter((e) => e.jitter_ms > e.ms).length

  return (
    <section className="card">
      <div className="card-head">
        <Tip text="Each generator is rebuilt on its own while the clock runs — the time it takes is what it costs the viewport on every change. Nothing in the scene is modified.">
          <h3>Viewport cost</h3>
        </Tip>
      </div>
      <p className="hint-sm">
        Which generator makes the viewport crawl? Each one is rebuilt by
        itself and timed, slowest first — click a bar to select that object in
        Cinema 4D. The scene is only rebuilt, never changed.
      </p>
      {/* The one thing this card is FOR — centred under its own description,
          not tucked into the head where it read as a corner decoration. */}
      <div className="card-cta">
        <ActionButton tone="go" disabled={measuring} onClick={measure}>
          {measuring ? 'Measuring…' : perf ? 'Measure again' : 'Measure'}
        </ActionButton>
      </div>
      {error && <div className="error" style={{ marginTop: 10 }}>Measuring failed: {error}</div>}
      {measuring && !perf && (
        <div className="empty-note mid">Rebuilding every generator once — this takes a moment on a heavy scene.</div>
      )}
      {perf && s && (
        <>
          <div className="substats" style={{ margin: '12px 0' }}>
            <Tip text="One pass that rebuilds every generator at once — the real cost of a full scene update.">
              <span><b>{ms1(s.scene_ms)}</b> full rebuild</span>
            </Tip>
            <span><b>{s.total}</b> generators &amp; deformers</span>
            <span className={s.heavy ? 'warn' : ''}><b>{s.heavy}</b> heavy</span>
          </div>
          {/* Honesty check: the rows only mean "this object" when they add up
              to the full rebuild. Nested generators make them add up to more. */}
          {s.overlap >= 1.35 && (
            <p className="hint-sm">
              ⚠ The rows below add up to {ms1(s.total_ms)}, but rebuilding the
              whole scene takes only {ms1(s.scene_ms)}. Generators are nested
              here, so a row is the cost of that object <b>and everything above
              it in the chain</b> — read it as the price of the branch, not of
              the single object.
            </p>
          )}
          {s.slowest ? (
            <p className="hint-sm">
              <b>{s.slowest}</b> alone costs {ms1(s.slowest_ms)} —{' '}
              {Math.round(s.slowest_share * 100)}% of every viewport update.
              Cache it, drop its editor subdivisions, or hide it while you work.
            </p>
          ) : s.measured > 0 ? (
            <p className="hint-sm">No single bottleneck — the cost is spread across the generators below.</p>
          ) : (
            <p className="hint-sm">Everything rebuilds instantly — no generator is holding the viewport back</p>
          )}
          {rows.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <BarList rows={rows} format={ms1} empty="Nothing measurable." />
              <p className="hint-sm" style={{ marginTop: 8 }}>
                Median of 3 runs per object.
                {belowNoise > 0 && ` ${belowNoise} more rebuild in under 0.5 ms — too fast to measure, not worth listing.`}
                {shaky > 0 && ` ${plural(shaky, 'value')} varied more between runs than the value itself — treat ${shaky === 1 ? 'it' : 'them'} as a rough order of magnitude.`}
              </p>
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default function GeneratorsTab({ org }: { org: Organizer }) {
  const { data, loading, error, reload } = useAudit<GenScan>('gens_scan', true)
  const [busy, setBusy] = useState(false)
  const [applyError, setApplyError] = useState('')
  const [icons, setIcons] = useState<Record<string, string>>({})
  const [confirm, setConfirm] = useState<{
    type: GenType; param: GenParam; value: any; guids: number[] | undefined; count: number
  } | null>(null)

  // The real C4D object icons, once per set of type ids.
  const iconKey = (data?.types || []).map((t) => t.type_id).join(',')
  useEffect(() => {
    if (!iconKey) return
    call('type_icons', { ids: iconKey.split(',').map(Number) })
      .then((r) => setIcons(r.icons || {}))
      .catch(() => { /* labels alone are fine */ })
  }, [iconKey])

  if (!org.report && !data) {
    return <EmptyState onAction={org.doAnalyze} busy={org.busy} />
  }
  if (!data) {
    return loading
      ? <EmptyState message="Scanning generators…" />
      : error
        ? <EmptyState message={`Generators scan failed: ${error}`}
            actionLabel="Retry" onAction={reload} busy={loading} />
        : <EmptyState message="No generator data yet." actionLabel="Scan"
            onAction={reload} busy={loading} />
  }
  // No AUDITED types (SDS/Cloner/…) still leaves plenty to measure: the cost
  // audit covers every generator and deformer in the scene.
  if (data.types.length === 0) {
    return (
      <div className="stacked">
        <div className="empty-note">No audited generators in this scene — no Subdivision Surface, Cloner, Extrude, Instance or Symmetry objects found.</div>
        <PerfCard />
      </div>
    )
  }

  const runApply = async () => {
    if (!confirm) return
    const { type, param, value, guids } = confirm
    setConfirm(null)
    setBusy(true)
    setApplyError('')
    try {
      await call('gens_apply', { type_key: type.key, param_key: param.key, value, guids })
      await reload()
    } catch (e: any) {
      setApplyError(`Align failed: ${String(e.message || e)}`)
    } finally {
      setBusy(false)
    }
  }

  const selectValue = (type: GenType, param: GenParam, value: any) => {
    call('gens_select', { type_key: type.key, param_key: param.key, value })
      .catch(() => { /* selection is best-effort */ })
  }

  const s = data.summary
  return (
    <div className="workbench">
      <aside className={'wb-side' + (loading ? ' side-loading' : '')}>
        <h3>Generators</h3>
        <p className="hint-sm">
          Same generator, different settings? Each card on the right is one
          generator type. Settings where all objects agree are summarized in one
          quiet line — only the <b>mixed</b> settings get a block: see who uses
          what, click a value chip to select those objects in C4D, or align
          everyone to one value in a single undoable step.
        </p>
        <div className="substats gens-side-stats">
          <span><b>{s.total_generators}</b> generators</span>
          <span><b>{s.types_found}</b> types</span>
          <Tip text="Settings where generators of the same type have different values — e.g. different subdivision levels. They can be unified to one value on the right.">
            <span className={s.non_uniform_params ? 'mixed' : ''}>
              <b>{s.non_uniform_params}</b> mixed setting{s.non_uniform_params === 1 ? '' : 's'}
            </span>
          </Tip>
        </div>
        {loading && <p className="hint-sm" style={{ marginTop: 12 }}>Refreshing…</p>}
        {error && (
          <div className="error" style={{ marginTop: 12 }}>
            Generators scan failed: {error}{' '}
            <ActionButton onClick={reload} disabled={loading}>Retry</ActionButton>
          </div>
        )}
        {applyError && <div className="error" style={{ marginTop: 12 }}>{applyError}</div>}
      </aside>

      <div className="stacked" style={{ minWidth: 0 }}>
      <PerfCard />
      {data.types.map((type) => {
        const mixed = type.params.filter((p) => !p.uniform)
        const uniform = type.params.filter((p) => p.uniform)
        return (
          <section className="card gens-type" key={type.key}>
            <div className="card-head">
              <h3 className="gens-type-title">
                {icons[String(type.type_id)] && (
                  <img className="gens-icon" src={icons[String(type.type_id)]} alt="" draggable={false} />
                )}
                {type.label} <span className="gens-count">{type.count}</span>
              </h3>
              {mixed.length === 0 && <span className="gens-uniform">all settings uniform ✓</span>}
              <ActionButton className="gens-selall" disabled={busy}
                title={`Select all ${type.count} ${type.label} objects in Cinema 4D`}
                onClick={() => call('gens_select', { type_key: type.key }).catch(() => {})}>
                Select in C4D
              </ActionButton>
            </div>

            {mixed.length > 0 && (
              <div className="gens-section">
                Settings you can change
                <span className="gens-section-n">{mixed.length} mixed</span>
              </div>
            )}
            {mixed.map((param) => (
              <MixedParam key={param.key} type={type} param={param} busy={busy}
                onApply={(p, v, g, c) => setConfirm({ type, param: p, value: v, guids: g, count: c })}
                onSelectValue={(p, v) => selectValue(type, p, v)} />
            ))}

            {uniform.length > 0 && (
              <>
                <div className="gens-section quiet">
                  Already the same on all {type.count}
                </div>
                <div className="gens-uniform-row">
                  {uniform.map((p) => (
                    <span className="gens-uniform-item" key={p.key}
                      title={`All ${type.count} objects share this value`}>
                      {p.label}: <b>{fmt(p.dominant, p)}</b> ✓
                    </span>
                  ))}
                </div>
              </>
            )}
          </section>
        )
      })}
      </div>

      {confirm && (
        <ConfirmModal
          title={`Align ${confirm.param.label}`}
          message={`Set ${confirm.param.label} to ${fmt(confirm.value, confirm.param)} on ${plural(confirm.count, `${confirm.type.label} object`)}? One undo step in Cinema 4D.`}
          confirmLabel={`✓ Set on ${confirm.count}`}
          onConfirm={runApply}
          onCancel={() => setConfirm(null)} />
      )}
    </div>
  )
}
