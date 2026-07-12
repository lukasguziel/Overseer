import { useMemo, useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import useAudit from '../hooks/useAudit'
import { humanBytes } from '../lib/format'
import ConfirmModal from '../components/ConfirmModal'
import AcceptedSection from '../components/AcceptedSection'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'
import Tip from '../components/Tip'
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
  accepted?: string[]   // raw paths accepted as missing (keeps section 'files')
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

// Status dot: only a MISSING file is a defect (err). Absolute vs relative
// is a pipeline preference — both count as healthy, the badge tells which.
function statusColor(e: FileEntry): string {
  return e.missing ? 'var(--err)' : 'var(--apply)'
}

function FileTable({ rows, onFocus, onPick, onAccept }: {
  rows: FileEntry[]
  onFocus: (e: FileEntry) => void
  onPick?: (e: FileEntry) => void
  onAccept?: (e: FileEntry) => void
}) {
  return (
    <div className="fa-table">
      <div className="fa-tr fa-thead">
        <Tip text="File name of the external reference. Colored badge = kind (Alembic, cache, IES …)."><span>File</span></Tip>
        <Tip text="Object or material that references the file. Click a row to select it in Cinema 4D."><span>Owner</span></Tip>
        <Tip text="File size on disk."><span className="num">Size</span></Tip>
        <Tip text="Stored path. Badge shows absolute / relative / missing."><span>Path</span></Tip>
      </div>
      {rows.map((e, i) => {
        const actionable = e.missing && (onPick || onAccept)
        return (
          <div className={'fa-tr fa-click' + (actionable ? ' fa-actionable' : '')}
            key={e.path + '|' + e.owner + '|' + i}
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
                  : <span className="tex-badge">{e.absolute ? 'absolute' : 'relative'}</span>}
            </span>
            {actionable && (
              <span className="rn-actions" onClick={(ev) => ev.stopPropagation()}>
                {onPick && (
                  <button className="rn-ok" title="Browse — pick the replacement file in Cinema 4D's file dialog (undoable)"
                    onClick={() => onPick(e)}>…</button>
                )}
                {onAccept && (
                  <button className="rn-keep" title="Accept as missing — stops counting as a problem (restore below)"
                    onClick={() => onAccept(e)}>=</button>
                )}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}

export default function FilesTab({ org }: { org: Organizer }) {
  const active = org.tab === 'files'
  const { data, loading, error, reload } = useAudit<FilesScan>('files_scan', active)
  const [kind, setKind] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [note, setNote] = useState('')
  // Missing-files batching: relink after folder pick / accept-all confirm.
  const [relinkDir, setRelinkDir] = useState('')
  const [relinkConfirm, setRelinkConfirm] = useState(false)
  const [acceptConfirm, setAcceptConfirm] = useState(false)

  const accepted = data?.accepted || []
  const setFileKeeps = async (keys: string[]) => {
    try {
      await call('set_keeps', { section: 'files', keys })
      await reload()
    } catch (e: any) { setNote(String(e.message || e)) }
  }
  const acceptOne = (e: FileEntry) => {
    setNote(`Accepted “${e.file}” as missing ✓ (restore below)`)
    setFileKeeps([...accepted, e.path])
  }
  const pickOne = async (e: FileEntry) => {
    setNote('Pick the file in the Cinema 4D window…')
    try {
      const r = await call('files_pick_path', { path: e.path })
      if (r.error) { setNote(r.error); return }
      if (r.cancelled) { setNote('File picker cancelled.'); return }
      setNote(`Reference → “${r.picked}” ✓ (undoable)`)
      await reload()
    } catch (err: any) { setNote(String(err.message || err)) }
  }
  const doRelink = async () => {
    setRelinkConfirm(false)
    setNote('Searching for the missing files…')
    try {
      const r = await call('files_relink', { folder: relinkDir })
      if (r.error) { setNote(r.error); return }
      setNote(`Relinked ${r.relinked} file${r.relinked === 1 ? '' : 's'} ✓ (undoable)`
        + (r.not_found ? ` · ${r.not_found} not found there` : ''))
      await reload()
    } catch (e: any) { setNote(String(e.message || e)) }
  }

  const entries = data?.entries || []
  const byKind = (e: FileEntry) => !kind || e.kind === kind
  const missing = useMemo(() => entries.filter((e) => e.missing && byKind(e)), [entries, kind])
  const present = useMemo(() => entries.filter((e) => !e.missing && byKind(e)), [entries, kind])
  const missPager = usePager(missing, undefined, kind)
  const pager = usePager(present, undefined, kind)

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
      ? <div className="empty-note">Scanning external files…</div>
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
      {/* Workbench layout like Textures: settings/filters left, lists right. */}
      <div className="workbench">
        <aside className="wb-side">
          <h3>External files</h3>
          <p className="hint-sm">
            Every external file the scene references — Alembic caches,
            referenced scenes, volume/point caches, IES profiles, audio and
            video — excluding image textures (see the Materials tab).
            Heaviest first.
          </p>
          <div className="substats" style={{ marginBottom: 12 }}>
            <span><b>{s.total}</b> files</span>
            <span><b>{humanBytes(s.total_bytes)}</b> on disk</span>
            <span className={s.missing_count ? 'warn' : ''}><b>{s.missing_count}</b> missing</span>
          </div>

          <div className="section-head sm"><span>Kind</span></div>
          <div className="tex-filter tex-filter-col">
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

          <div className="section-head sm"><span>Actions</span></div>
          <h4 className="side-action-title">Relative paths</h4>
          {!data.doc_path && (
            <p className="hint-sm">Project not saved — paths cannot be made relative yet.</p>
          )}
          <button className="mini" disabled={loading || !canFix}
            title={canFix
              ? `Rewrite ${reloc} absolute path(s) under the project folder to relative (undoable)`
              : 'No absolute paths inside the project folder'}
            onClick={() => setConfirm(true)}>
            Make relative ({reloc})
          </button>
          {note && <p className="example" style={{ marginTop: 4 }}>{note}</p>}
        </aside>

        <div className="stacked" style={{ minWidth: 0 }}>
          {missPager.total > 0 && (
            <section className="card">
              <div className="card-head">
                <h3>Missing files</h3>
                <span className="card-hint">{missPager.total}</span>
                <span style={{ marginLeft: 'auto', display: 'flex', gap: 6 }}>
                  <button className="mini" disabled={loading}
                    title="Pick a folder in Cinema 4D — it is searched recursively for the missing file names and every match is relinked (undoable)"
                    onClick={() => {
                      call('pick_folder', { title: 'Folder to search for the missing files' })
                        .then((r) => { if (r.path) { setRelinkDir(r.path); setRelinkConfirm(true) } })
                        .catch(() => {})
                    }}>
                    … Relink {missPager.total}
                  </button>
                  <button className="mini" disabled={loading || !missing.some((e) => e.guid != null)}
                    title="Select every object referencing a missing file in Cinema 4D — inspect or replace them in one go"
                    onClick={async () => {
                      const guids = missing.map((e) => e.guid).filter((g): g is number => g != null)
                      try {
                        const r = await call('files_select', { guids })
                        setNote(`Selected ${r.selected} object${r.selected === 1 ? '' : 's'} with missing files in C4D ✓`)
                      } catch (e: any) { setNote(String(e.message || e)) }
                    }}>
                    Select in C4D
                  </button>
                  <button className="mini" disabled={loading}
                    title="Accept all as missing — they stop counting as problems (restore below)"
                    onClick={() => setAcceptConfirm(true)}>
                    = Accept {missPager.total}
                  </button>
                </span>
              </div>
              <p className="hint-sm">Per row: … pick the replacement file in C4D's file dialog · = accept it as missing.</p>
              <FileTable rows={missPager.rows} onFocus={onFocus}
                onPick={pickOne} onAccept={acceptOne} />
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
              : <div className="empty-note">No external files{kind ? ` of kind “${KIND_LABEL[kind]}”` : ''} 🎉</div>}
          </section>

          <AcceptedSection items={accepted}
            onRestore={(p) => setFileKeeps(accepted.filter((a) => a !== p))}
            onRestoreAll={() => setFileKeeps([])}
            hint="Accepted-as-missing files are remembered (config) and no longer count as problems — restore to treat them as missing again." />
        </div>
      </div>

      {relinkConfirm && (
        <ConfirmModal
          title="Relink missing files"
          message={`Search “${relinkDir}” (including subfolders) for the ${missPager.total} missing file name${missPager.total === 1 ? '' : 's'} and relink every match (project-relative when possible, one undo step). Files not found there are left as-is. Continue?`}
          confirmLabel={`✓ Relink ${missPager.total}`}
          onConfirm={doRelink}
          onCancel={() => setRelinkConfirm(false)}
        />
      )}
      {acceptConfirm && (
        <ConfirmModal
          title="Accept all as missing"
          message={`Accept all ${missPager.total} missing file${missPager.total === 1 ? '' : 's'} as missing. Nothing changes in the scene — they just stop counting as problems (restore any time below). Continue?`}
          confirmLabel={`= Accept ${missPager.total}`}
          onConfirm={() => {
            setAcceptConfirm(false)
            setFileKeeps([...accepted, ...missing.map((e) => e.path)])
          }}
          onCancel={() => setAcceptConfirm(false)}
        />
      )}

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
