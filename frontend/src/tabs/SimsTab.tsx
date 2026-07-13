import { useMemo, useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import useAudit from '../hooks/useAudit'
import EmptyState from '../components/EmptyState'
import ConfirmModal from '../components/ConfirmModal'
import Pager, { usePager } from '../components/Pager'
import Tip from '../components/Tip'
import { IconCheck } from '../components/icons'
import './sims.css'
import ActionButton from '../components/ActionButton'
import InfoButton from '../components/InfoButton'

interface SimHit {
  guid: number
  object: string
  carrier: 'tag' | 'object'
  kind: string
  label: string
  enabled: boolean | null
  cached: boolean | null
  hidden: boolean
  notes: string[]
}

interface SimsScan {
  ok: boolean
  hits: SimHit[]
  findings: {
    active_hidden: SimHit[]
    unbaked: SimHit[]
    disabled_leftovers: SimHit[]
  }
  summary: {
    total: number
    by_kind: Record<string, number>
    active_hidden: number
    unbaked: number
    disabled: number
  }
}

// Group hits by kind, then issue one set_enabled call per kind (the backend
// toggle is per-kind because each sim type has its own enable parameter).
function groupByKind(hits: SimHit[]): Record<string, number[]> {
  const out: Record<string, number[]> = {}
  for (const h of hits) (out[h.kind] ||= []).push(h.guid)
  return out
}

function StateBadges({ hit }: { hit: SimHit }) {
  return (
    <Tip className="sim-badges-tip" text="State of this simulation: enabled/disabled, whether a cache is baked (without a cache it solves live) and whether the object is hidden.">
    <span className="sim-badges">
      {hit.enabled === true && <span className="pill sim-ok">enabled</span>}
      {hit.enabled === false && <span className="pill sim-dim">disabled</span>}
      {hit.cached === true && <span className="pill sim-ok">cached</span>}
      {hit.cached === false && <span className="pill sim-warn">no cache</span>}
      {hit.hidden && <span className="pill sim-warn">hidden</span>}
    </span>
    </Tip>
  )
}

export default function SimsTab({ org }: { org: Organizer }) {
  const { data, loading, error, reload } = useAudit<SimsScan>('sims_scan', true)
  const [note, setNote] = useState<string | null>(null)
  const [confirmDisable, setConfirmDisable] = useState<SimHit[] | null>(null)
  const busy = org.busy

  const groups = useMemo(() => {
    const by: Record<string, SimHit[]> = {}
    for (const h of data?.hits || []) (by[h.kind] ||= []).push(h)
    return Object.entries(by).sort((a, b) => b[1].length - a[1].length)
  }, [data])

  if (!data) {
    return loading
      ? <EmptyState message="Scanning the scene for simulation setups…" />
      : error
        ? <EmptyState message={`Sims scan failed: ${error}`}
            actionLabel="Retry" onAction={reload} busy={loading} />
        : <EmptyState message="No simulation data yet." actionLabel="Scan"
            onAction={reload} busy={busy} />
  }

  const s = data.summary
  if (s.total === 0) {
    return <div className="empty-note">No simulation setups found in this scene.</div>
  }

  const doFocus = (h: SimHit) => org.doFocus(h.guid, h.object)

  const doDisable = async (hits: SimHit[], label: string) => {
    const byKind = groupByKind(hits)
    let applied = 0
    let failed = 0
    let lastError = ''
    for (const [kind, guids] of Object.entries(byKind)) {
      try {
        const r = await call('sims_set_enabled', { guids, kind, enabled: false })
        applied += r.applied || 0
      } catch (e: any) {
        failed += guids.length
        lastError = String(e.message || e)
      }
    }
    setNote(applied
      ? `${label}: ${applied} disabled ✓ (undoable)${failed ? ` — ${failed} failed: ${lastError}` : ''}`
      : `${label}: nothing disabled ✗${lastError ? ` — ${lastError}` : ''}`)
    reload()
  }

  const doSelect = async (kind: string) => {
    try {
      const r = await call('sims_select', { kind })
      setNote(`Selected ${r.selected} ${kind} object${r.selected === 1 ? '' : 's'} in Cinema 4D`)
    } catch (e: any) { setNote(`Select ✗ ${String(e.message || e)}`) }
  }

  return (
    <div className="stacked">
      <section className="card">
        <div className="card-head"><h3>Simulations</h3></div>
        <div className="substats">
          <span><b>{s.total}</b> participants</span>
          {Object.entries(s.by_kind).map(([k, n]) => (
            <span key={k}><b>{n}</b> {k}</span>
          ))}
          <Tip text="Active simulations on hidden objects — they cost solve time without the result ever being visible.">
            <span className={s.active_hidden ? 'warn' : ''}>
              <b>{s.active_hidden}</b> active on hidden
            </span>
          </Tip>
        </div>
        {note && <p className="wb-note">{note}</p>}
        <InfoButton doc="sims-findings" />
      </section>

      <FindingCard
        title="Active on hidden objects"
        hint="Enabled simulations on hidden objects still cost solve time you never see. The green ✓ disables one · click a row to frame it."
        hits={data.findings.active_hidden} tone="warn"
        rowAction={(h) => (
          <button className="rn-ok" disabled={busy} title="Disable this simulation (undoable)"
            onClick={() => doDisable([h], h.object)}><IconCheck /></button>
        )}
        onFocus={doFocus}
        batch={data.findings.active_hidden.length > 0 ? {
          label: `Disable ${data.findings.active_hidden.length}`,
          onClick: () => setConfirmDisable(data.findings.active_hidden),
        } : undefined}
      />

      <FindingCard
        title="Unbaked simulations"
        hint="These run live with no cache — consider baking before handing the scene off."
        hits={data.findings.unbaked} tone="info" onFocus={doFocus}
      />

      {/* Leftovers next to the full roster: same width, read side by side. */}
      <div className={'sim-split' + (data.findings.disabled_leftovers.length ? '' : ' single')}>
        <FindingCard
          title="Disabled leftovers"
          hint="Disabled simulation tags left in the scene — clutter you may want to delete by hand (deleting a sim is your call, not the tool's)."
          hits={data.findings.disabled_leftovers} tone="dim" onFocus={doFocus}
        />

        <section className="card">
          <div className="card-head"><h3>All simulation participants</h3></div>
          {groups.map(([kind, hits]) => (
            <KindGroup key={kind} kind={kind} hits={hits}
              onFocus={doFocus} onSelect={() => doSelect(kind)} />
          ))}
          <InfoButton doc="sims-all" />
        </section>
      </div>

      {confirmDisable && (
        <ConfirmModal title="Disable simulations"
          message={`Disable ${confirmDisable.length} simulation${confirmDisable.length === 1 ? '' : 's'} running on hidden objects? One undo step in Cinema 4D.`}
          confirmLabel={`✓ Disable ${confirmDisable.length}`}
          onConfirm={() => { const h = confirmDisable; setConfirmDisable(null); doDisable(h, 'Active on hidden') }}
          onCancel={() => setConfirmDisable(null)} />
      )}
    </div>
  )
}

function FindingCard({ title, hint, hits, tone, rowAction, onFocus, batch }: {
  title: string
  hint: string
  hits: SimHit[]
  tone: 'warn' | 'info' | 'dim'
  rowAction?: (h: SimHit) => React.ReactNode
  onFocus: (h: SimHit) => void
  batch?: { label: string; onClick: () => void }
}) {
  const pager = usePager(hits)
  if (hits.length === 0) return null
  return (
    <section className="card">
      <div className="card-head">
        <h3 className={'sim-find-' + tone}>{title}</h3>
        <span className="head-count">{hits.length} found</span>
        {batch && (
          <ActionButton tone="go" onClick={batch.onClick}
            title="Disable all of these in one undo step">{batch.label}</ActionButton>
        )}
      </div>
      <p className="hint-sm">{hint}</p>
      <div className="rename-list">
        {pager.rows.map((h) => (
          <SimRow key={h.guid + ':' + h.kind} hit={h} onFocus={onFocus}
            action={rowAction ? rowAction(h) : undefined} />
        ))}
      </div>
      <Pager pager={pager} />
      <InfoButton doc="sims-findings" />
    </section>
  )
}

function SimRow({ hit, onFocus, showCarrier, action }: {
  hit: SimHit
  onFocus: (h: SimHit) => void
  showCarrier?: boolean
  action?: React.ReactNode
}) {
  return (
    <div className="sg-row rename-row sg-focusable">
      <span className="sg-body" onClick={() => onFocus(hit)}
        title="Click to select & frame it in Cinema 4D">
        <span className="pill sim-kind">{hit.label}</span>
        <span className="rn-old" title={hit.object}>{hit.object}</span>
        {showCarrier && <span className="dim sim-carrier">{hit.carrier}</span>}
        <StateBadges hit={hit} />
      </span>
      {action && <span className="rn-actions">{action}</span>}
    </div>
  )
}

function KindGroup({ kind, hits, onFocus, onSelect }: {
  kind: string
  hits: SimHit[]
  onFocus: (h: SimHit) => void
  onSelect: () => void
}) {
  const pager = usePager(hits)
  return (
    <div className="sim-group">
      <div className="section-head sm">
        <span>{kind}</span>
        <span className="head-count">{hits.length}</span>
        <ActionButton onClick={onSelect}
          title={`Select all ${kind} objects in Cinema 4D`}>Select in C4D</ActionButton>
      </div>
      <div className="rename-list">
        {pager.rows.map((h) => (
          <SimRow key={h.guid + ':' + h.kind} hit={h} onFocus={onFocus} showCarrier />
        ))}
      </div>
      <Pager pager={pager} />
    </div>
  )
}
