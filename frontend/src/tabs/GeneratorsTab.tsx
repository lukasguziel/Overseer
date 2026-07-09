import { useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import useAudit from '../hooks/useAudit'
import EmptyState from '../components/EmptyState'
import SuggestionRow from '../components/SuggestionRow'
import ConfirmModal from '../components/ConfirmModal'
import Pager, { usePager } from '../components/Pager'
import './generators.css'

type ParamKind = 'int' | 'bool' | 'choice'

interface GenValue { guid: number; name: string; value: any }
interface GenBucket { value: any; count: number }
interface GenParam {
  key: string
  label: string
  kind: ParamKind
  values: GenValue[]
  distribution: GenBucket[]
  uniform: boolean
  dominant: any
  outliers: GenValue[]
}
interface GenType { key: string; label: string; count: number; params: GenParam[] }
interface GenScan {
  ok: boolean
  types: GenType[]
  summary: { total_generators: number; types_found: number; non_uniform_params: number }
}

function fmt(value: any, kind: ParamKind): string {
  if (value === null || value === undefined) return '—'
  if (kind === 'bool') return value ? 'on' : 'off'
  if (Array.isArray(value)) return value.map((n) => Number(n).toFixed(2)).join(', ')
  return String(value)
}

function sameValue(a: any, b: any): boolean {
  if (Array.isArray(a) && Array.isArray(b)) return JSON.stringify(a) === JSON.stringify(b)
  return a === b
}

// One parameter of one generator type: its value distribution as chips, plus
// the "align" affordances when the values disagree — a value picker + batch
// apply, and an expandable list of the outlier objects each fixable on its own.
function ParamSection({ type, param, busy, onApply, onSelectValue }: {
  type: GenType
  param: GenParam
  busy: boolean
  onApply: (param: GenParam, value: any, guids: number[] | undefined, count: number) => void
  onSelectValue: (param: GenParam, value: any) => void
}) {
  const [pick, setPick] = useState<any>(param.dominant)
  const [open, setOpen] = useState(false)
  const pager = usePager(param.outliers)

  const numeric = param.kind === 'int'
  const chips = (
    <div className="gens-chips">
      {param.distribution.map((b, i) => {
        const dom = sameValue(b.value, param.dominant)
        return (
          <button key={i}
            className={'gens-chip' + (dom ? ' dom' : ' warn')}
            title={dom
              ? 'Dominant value — click to select these objects in Cinema 4D'
              : 'Outlier value — click to select these objects in Cinema 4D'}
            onClick={() => onSelectValue(param, b.value)}>
            <b>{b.count}×</b> {fmt(b.value, param.kind)}{!dom && ' ⚠'}
          </button>
        )
      })}
    </div>
  )

  if (param.uniform) {
    return (
      <div className="gens-param">
        <div className="gens-param-head">
          <span className="gens-param-label">{param.label}</span>
          <span className="gens-uniform">uniform ✓</span>
        </div>
        {chips}
      </div>
    )
  }

  return (
    <div className="gens-param warn-bd">
      <div className="gens-param-head">
        <span className="gens-param-label warn">{param.label}</span>
        <span className="gens-nonuniform">{param.distribution.length} distinct values ⚠</span>
      </div>
      {chips}
      <div className="gens-align">
        <span className="hint-sm">Align all to</span>
        {numeric ? (
          <input className="gens-num" type="number" value={pick ?? ''}
            onChange={(e) => setPick(e.target.value === '' ? '' : Number(e.target.value))} />
        ) : (
          <select className="gens-select" value={JSON.stringify(pick)}
            onChange={(e) => setPick(JSON.parse(e.target.value))}>
            {param.distribution.map((b, i) => (
              <option key={i} value={JSON.stringify(b.value)}>{fmt(b.value, param.kind)}</option>
            ))}
          </select>
        )}
        <button className="apply gens-align-btn" disabled={busy}
          title={`Set ${param.label} to ${fmt(pick, param.kind)} on all ${type.count} objects`}
          onClick={() => onApply(param, pick, undefined, type.count)}>
          ✓ Align all {type.count}
        </button>
      </div>
      <button className="gens-toggle" onClick={() => setOpen((v) => !v)}>
        {open ? '▾' : '▸'} {param.outliers.length} object{param.outliers.length === 1 ? '' : 's'} off the dominant value
      </button>
      {open && (
        <div className="rename-list gens-outliers">
          {pager.rows.map((o) => (
            <SuggestionRow key={o.guid} busy={busy}
              applyTitle={`Set this object's ${param.label} to ${fmt(param.dominant, param.kind)} (undoable)`}
              onApply={() => onApply(param, param.dominant, [o.guid], 1)}
              onAcceptAsIs={() => onSelectValue(param, o.value)}
              onFocus={() => call('focus', { guid: o.guid })}>
              <span className="rn-old" title={o.name}>{o.name}</span>
              <span className="rn-arrow">→</span>
              <span className="rn-new">{fmt(param.dominant, param.kind)}</span>
              <span className="gens-had">was {fmt(o.value, param.kind)}</span>
            </SuggestionRow>
          ))}
          <Pager pager={pager} />
        </div>
      )}
    </div>
  )
}

export default function GeneratorsTab({ org }: { org: Organizer }) {
  const { data, loading, error, reload } = useAudit<GenScan>('gens_scan', true)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState<{
    type: GenType; param: GenParam; value: any; guids: number[] | undefined; count: number
  } | null>(null)

  if (!org.report && !data) {
    return <EmptyState onAction={org.doAnalyze} busy={org.busy} />
  }
  if (error) {
    return <div className="fl-empty">Generators scan failed: {error}</div>
  }
  if (!data) {
    return <div className="fl-empty">Scanning generators…</div>
  }
  if (data.types.length === 0) {
    return <div className="fl-empty">No audited generators in this scene — no Subdivision Surface, Cloner, Extrude, Instance or Symmetry objects found.</div>
  }

  const runApply = async () => {
    if (!confirm) return
    const { type, param, value, guids } = confirm
    setConfirm(null)
    setBusy(true)
    try {
      await call('gens_apply', { type_key: type.key, param_key: param.key, value, guids })
      await reload()
    } catch (e: any) {
      // surfaced through the loader's next scan; keep UI responsive
      void e
    } finally {
      setBusy(false)
    }
  }

  const selectValue = (type: GenType, param: GenParam, value: any) => {
    call('gens_select', { type_key: type.key, param_key: param.key, value })
      .catch(() => { /* selection is best-effort */ })
  }

  const selectAll = async (type: GenType) => {
    try {
      await call('gens_select', { type_key: type.key })
    } catch { /* best-effort */ }
  }

  const s = data.summary
  return (
    <div className="stacked">
      <section className="card">
        <div className="card-head"><h3>Generators</h3></div>
        <p className="hint-sm">
          Every audited generator grouped by type, with the settings worth comparing.
          Parameters whose values disagree across objects are flagged — align them in one click.
        </p>
        <div className="substats">
          <span><b>{s.total_generators}</b> generators</span>
          <span><b>{s.types_found}</b> types</span>
          <span className={s.non_uniform_params ? 'warn' : ''}>
            <b>{s.non_uniform_params}</b> non-uniform params
          </span>
        </div>
      </section>

      {loading && <p className="hint-sm">Refreshing…</p>}

      {data.types.map((type) => (
        <section className="card gens-type" key={type.key}>
          <div className="card-head">
            <h3>{type.label} <span className="gens-count">{type.count}</span></h3>
            <button className="ghost gens-selall" disabled={busy}
              title={`Select all ${type.count} ${type.label} objects in Cinema 4D`}
              onClick={() => selectAll(type)}>
              Select all in C4D
            </button>
          </div>
          {type.params.map((param) => (
            <ParamSection key={param.key} type={type} param={param} busy={busy}
              onApply={(p, v, g, c) => setConfirm({ type, param: p, value: v, guids: g, count: c })}
              onSelectValue={(p, v) => selectValue(type, p, v)} />
          ))}
        </section>
      ))}

      {confirm && (
        <ConfirmModal
          title={`Align ${confirm.param.label}`}
          message={`Set ${confirm.param.label} to ${fmt(confirm.value, confirm.param.kind)} on ${confirm.count} object${confirm.count === 1 ? '' : 's'}? One undo step in Cinema 4D.`}
          confirmLabel={`✓ Set on ${confirm.count} (undoable)`}
          onConfirm={runApply}
          onCancel={() => setConfirm(null)} />
      )}
    </div>
  )
}
