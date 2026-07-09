import { useEffect, useState } from 'react'
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

  return (
    <div className="gens-param">
      <div className="gens-param-head">
        <span className="gens-param-label">{param.label}</span>
        <span className="gens-mixed-note">
          most use <b>{fmt(param.dominant, param)}</b> — {offCount} object{offCount === 1 ? '' : 's'} differ{offCount === 1 ? 's' : ''}
        </span>
      </div>
      <div className="gens-chips">
        {sorted.map((b, i) => {
          const dom = sameValue(b.value, param.dominant)
          return (
            <button key={i}
              className={'gens-chip' + (dom ? ' dom' : ' warn')}
              title={`${b.count} object${b.count === 1 ? '' : 's'} — click to select them in Cinema 4D`}
              onClick={() => onSelectValue(param, b.value)}>
              <span className="gens-chip-val">{fmt(b.value, param)}</span>
              <span className="gens-chip-n">×{b.count}</span>
            </button>
          )
        })}
      </div>
      <div className="gens-align">
        <label className="gens-setter">
          <span className="gens-setter-label">Set {param.label} to</span>
          {param.kind === 'int' ? (
            <input className="gens-num" type="number" value={pick ?? ''}
              onChange={(e) => setPick(e.target.value === '' ? '' : Number(e.target.value))} />
          ) : (
            <select className="gens-select" value={JSON.stringify(pick)}
              onChange={(e) => setPick(JSON.parse(e.target.value))}>
              {sorted.map((b, i) => (
                <option key={i} value={JSON.stringify(b.value)}>{fmt(b.value, param)}</option>
              ))}
            </select>
          )}
        </label>
        <button className="apply gens-align-btn" disabled={busy || pick === ''}
          title={`Set ${param.label} to ${fmt(pick, param)} on all ${type.count} ${type.label} objects (one undo step)`}
          onClick={() => onApply(param, pick, undefined, type.count)}>
          ✓ Align all {type.count}
        </button>
        <button className="gens-toggle" onClick={() => setOpen((v) => !v)}>
          {open ? '▾ hide' : '▸ show'} the {offCount} differing
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

export default function GeneratorsTab({ org }: { org: Organizer }) {
  const { data, loading, error, reload } = useAudit<GenScan>('gens_scan', true)
  const [busy, setBusy] = useState(false)
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
      void e // surfaced through the loader's next scan; keep UI responsive
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
    <div className="stacked">
      <section className="card">
        <div className="card-head"><h3>Generators</h3></div>
        <p className="hint-sm">
          Same generator, different settings? Each card below is one generator
          type. Settings where all objects agree are summarized in one quiet
          line — only the <b>mixed</b> settings get a block: see who uses what,
          click a value chip to select those objects in C4D, or align everyone
          to one value in a single undoable step.
        </p>
        <div className="substats">
          <span><b>{s.total_generators}</b> generators</span>
          <span><b>{s.types_found}</b> types</span>
          <span className={s.non_uniform_params ? 'warn' : ''}>
            <b>{s.non_uniform_params}</b> mixed setting{s.non_uniform_params === 1 ? '' : 's'}
          </span>
        </div>
      </section>

      {loading && <p className="hint-sm">Refreshing…</p>}

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
              <button className="ghost gens-selall" disabled={busy}
                title={`Select all ${type.count} ${type.label} objects in Cinema 4D`}
                onClick={() => call('gens_select', { type_key: type.key }).catch(() => {})}>
                Select all in C4D
              </button>
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

      {confirm && (
        <ConfirmModal
          title={`Align ${confirm.param.label}`}
          message={`Set ${confirm.param.label} to ${fmt(confirm.value, confirm.param)} on ${confirm.count} ${confirm.type.label} object${confirm.count === 1 ? '' : 's'}? One undo step in Cinema 4D.`}
          confirmLabel={`✓ Set on ${confirm.count}`}
          onConfirm={runApply}
          onCancel={() => setConfirm(null)} />
      )}
    </div>
  )
}
