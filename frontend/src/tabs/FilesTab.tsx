import { useMemo, useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import useAudit from '../hooks/useAudit'
import { humanBytes } from '../lib/format'
import ConfirmModal from '../components/ConfirmModal'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'
import './files.css'

interface FileEntry {
  kind: string
  file: string
  path: string
  resolved: string
  exists: boolean
  missing: boolean
  absolute: boolean
  relocatable: boolean
  rel_target: string
  bytes: number
  owner: string
  guid: number | null
}

interface FilesScan {
  ok: boolean
  doc_path: string
  entries: FileEntry[]
  summary: {
    total: number
    by_kind: Record<string, number>
    missing_count: number
    absolute_count: number
    relocatable_count: number
    total_bytes: number
  }
}

// Kind filter chips (order = display order). Alembic first — it is the one the
// artist asked about — then the rest of the external-reference kinds.
const KINDS: [string, string][] = [
  ['', 'All'], ['alembic', 'Alembic'], ['scene', 'Scene'], ['cache', 'Cache'],
  ['ies', 'IES'], ['audio', 'Audio'], ['video', 'Video'], ['other', 'Other'],
]

const KIND_LABEL: Record<string, string> = Object.fromEntries(
  KINDS.filter(([k]) => k).map(([k, l]) => [k, l]))

// Status dot: a missing file is the worst (err); a present-but-absolute path
// breaks when the project moves (warn); a relative path is healthy (ok).
function statusColor(e: FileEntry): string {
  if (e.missing) return 'var(--err)'
  if (e.absolute) return 'var(--warn)'
  return 'var(--apply)'
}

function FileTable({ rows, onFocus }: {
  rows: FileEntry[]
  onFocus: (e: FileEntry) => void
}) {
  return (
    <div className="fa-table">
      <div className="fa-tr fa-thead">
        <span>File</span><span>Owner</span>
        <span className="num">Size</span><span>Path</span>
      </div>
      {rows.map((e, i) => (
        <button className="fa-tr fa-click" key={e.path + '|' + e.owner + '|' + i}
          title={`${e.path}\nClick to select ${e.guid != null ? `“${e.owner}” in the viewport` : `material “${e.owner}”`}`}
          onClick={() => onFocus(e)}>
          <span className="fa-cell-file">
            <span className="fl-dot" style={{ background: statusColor(e) }} />
            <span className={'fa-kind fk-' + e.kind}>{KIND_LABEL[e.kind] || e.kind}</span>
            <span className="fa-cut">{e.file}</span>
          </span>
          <span className="dim fa-cut">{e.owner || '—'}</span>
          <span className="num">{e.bytes > 0 ? humanBytes(e.bytes) : '—'}</span>
          <span className="fa-cell-path dim">
            <span className="fa-cut">{e.path}</span>
            {e.missing
              ? <span className="tex-badge missing">missing</span>
              : e.relocatable
                ? <span className="tex-badge fixable">→ relative</span>
                : e.absolute
                  ? <span className="tex-badge unused">absolute</span>
                  : <span className="tex-badge fixable">relative</span>}
          </span>
        </button>
      ))}
    </div>
  )
}

export default function FilesTab({ org }: { org: Organizer }) {
  const active = org.tab === 'files'
  const { data, loading, error, reload } = useAudit<FilesScan>('files_scan', active)
  const [kind, setKind] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [note, setNote] = useState('')

  const entries = data?.entries || []
  const byKind = (e: FileEntry) => !kind || e.kind === kind
  const missing = useMemo(() => entries.filter((e) => e.missing && byKind(e)), [entries, kind])
  const present = useMemo(() => entries.filter((e) => !e.missing && byKind(e)), [entries, kind])
  const missPager = usePager(missing)
  const pager = usePager(present)

  const onFocus = (e: FileEntry) => {
    if (e.guid != null) org.doFocus(e.guid, e.owner)
    else if (e.owner) org.doFocusMaterial(e.owner)
  }

  const doMakeRelative = async () => {
    setConfirm(false)
    setNote('')
    try {
      const r = await call('files_make_relative', {})
      setNote(`Rewrote ${r.fixed} path${r.fixed === 1 ? '' : 's'} ✓ (undoable)`
        + (r.skipped ? ` · ${r.skipped} skipped` : ''))
      await reload()
    } catch (e: any) {
      setNote(String(e.message || e))
    }
  }

  if (!active) return null

  if (!data) {
    return loading
      ? <div className="fl-empty">Scanning external files…</div>
      : error
        ? <div className="empty-state"><p>Files scan failed: {error}</p>
            <button onClick={reload}>Retry</button></div>
        : <EmptyState message="No scene scanned yet — open your scene in Cinema 4D."
            actionLabel="Scan files" onAction={reload} busy={loading} />
  }

  const s = data.summary
  const reloc = s.relocatable_count
  const canFix = reloc > 0 && !!data.doc_path

  return (
    <div className="stacked">
      <section className="card">
        <div className="card-head">
          <h3>External files</h3>
          {canFix && (
            <button className="trash-btn fix-btn" disabled={loading}
              title={`Rewrite ${reloc} absolute path(s) under the project folder to relative (undoable)`}
              onClick={() => setConfirm(true)}>
              Make relative<span className="trash-count">{reloc}</span>
            </button>
          )}
        </div>
        <p className="hint-sm">
          Every external file the scene references — Alembic caches, referenced
          scenes, volume/point caches, IES profiles, audio and video — excluding
          image textures (see the Materials tab). Sorted by size, heaviest first.
        </p>
        <div className="substats" style={{ marginBottom: 4 }}>
          <span><b>{s.total}</b> external files</span>
          <span className="fa-hi"><b>{s.by_kind.alembic || 0}</b> alembic</span>
          <span><b>{humanBytes(s.total_bytes)}</b> on disk</span>
          <span className={s.missing_count ? 'warn' : ''}><b>{s.missing_count}</b> missing</span>
          <span className={s.absolute_count ? 'warn' : ''}><b>{s.absolute_count}</b> absolute</span>
        </div>
        <div className="tex-filter">
          <span className="tex-filter-label">Kind</span>
          {KINDS.map(([key, label]) => {
            const n = key ? (s.by_kind[key] || 0) : s.total
            if (key && !n) return null
            return (
              <button key={key || 'all'}
                className={'tex-filter-btn' + (kind === key ? ' on' : '')}
                onClick={() => setKind(key)}>
                {label} <em>{n}</em>
              </button>
            )
          })}
        </div>
        {data.doc_path
          ? <p className="example" style={{ marginTop: 8 }}>Project: <code>{data.doc_path}</code></p>
          : <p className="example warn" style={{ marginTop: 8 }}>Project not saved — paths cannot be made relative yet.</p>}
        {note && <p className="example" style={{ marginTop: 4 }}>{note}</p>}
      </section>

      {missPager.total > 0 && (
        <section className="card">
          <div className="card-head">
            <h3>Missing files</h3>
            <span className="card-hint">{missPager.total}</span>
            <button className="mini" disabled={loading || !missing.some((e) => e.guid != null)}
              title="Select every object referencing a missing file in Cinema 4D — inspect or replace them in one go"
              onClick={async () => {
                const guids = missing.map((e) => e.guid).filter((g): g is number => g != null)
                try {
                  const r = await call('files_select', { guids })
                  setNote(`Selected ${r.selected} object${r.selected === 1 ? '' : 's'} with missing files in C4D ✓`)
                } catch (e: any) { setNote(String(e.message || e)) }
              }}>
              Select all in C4D
            </button>
          </div>
          <FileTable rows={missPager.rows} onFocus={onFocus} />
          <Pager pager={missPager} />
        </section>
      )}

      <section className="card">
        <div className="card-head">
          <h3>Referenced files</h3>
          <span className="card-hint">{pager.total}</span>
        </div>
        {pager.total
          ? <>
              <FileTable rows={pager.rows} onFocus={onFocus} />
              <Pager pager={pager} />
            </>
          : <div className="fl-empty">No external files{kind ? ` of kind “${KIND_LABEL[kind]}”` : ''} 🎉</div>}
      </section>

      {confirm && (
        <ConfirmModal
          title="Make paths relative"
          message={`Rewrite ${reloc} absolute Alembic path${reloc === 1 ? '' : 's'} that live under the project folder to project-relative paths. Other asset kinds are left untouched. This is a single, undoable step.`}
          confirmLabel={`Make ${reloc} relative`}
          onConfirm={doMakeRelative}
          onCancel={() => setConfirm(false)}
        />
      )}
    </div>
  )
}
