import { useMemo, useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import type { FileEntry, FilesScan } from '../types'
import useAudit from '../hooks/useAudit'
import { plural, humanBytes } from '../lib/format'
import { statusDot } from '../lib/colors'
import { rowButton } from '../lib/rowButton'
import ConfirmModal from '../components/ConfirmModal'
import FilterChips from '../components/FilterChips'
import AcceptedPanel from '../components/AcceptedPanel'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'
import Tip from '../components/Tip'
import { IconCheck, IconFolder } from '../components/icons'
import './files.css'
import ActionButton from '../components/ActionButton'

// Kind filter chips (order = display order). Alembic first — it is the one the
// artist asked about — then the rest of the external-reference kinds.
const KINDS: [string, string][] = [
  ['', 'All'], ['alembic', 'Alembic'], ['scene', 'Scene'], ['cache', 'Cache'],
  ['ies', 'IES'], ['audio', 'Audio'], ['video', 'Video'], ['other', 'Other'],
]

const KIND_LABEL: Record<string, string> = Object.fromEntries(
  KINDS.filter(([k]) => k).map(([k, l]) => [k, l]))

// What a row can select in C4D, if anything. An external file can also be owned
// by a take or the render settings — those are neither object nor material, and
// clicking them used to ask the server for a material that never existed.
function selectable(e: FileEntry): '' | 'object' | 'material' {
  if (e.guid != null) return 'object'
  if (e.owner && e.owner_kind === 'material') return 'material'
  return ''
}

function FileTable({ rows, onFocus, onPick, onAccept }: {
  rows: FileEntry[]
  onFocus: (e: FileEntry) => void
  onPick?: (e: FileEntry) => void
  onAccept?: (e: FileEntry) => void
}) {
  const hasActions = !!(onPick || onAccept)
  const cols = 'cols-files' + (hasActions ? ' dg-actionable' : '')
  return (
    <div className="dg-table">
      <div className={'dg-tr dg-thead ' + cols}>
        <Tip text="File name of the external reference. Colored badge = kind (Alembic, cache, IES …)."><span>File</span></Tip>
        <Tip text="What references the file — usually an object or a material; a row for either selects it in Cinema 4D when you click it."><span>Owner</span></Tip>
        <Tip text="File size on disk."><span className="num">Size</span></Tip>
        <Tip text="Stored path. Badge shows absolute / relative / missing."><span>Path</span></Tip>
      </div>
      {rows.map((e, i) => {
        const actionable = e.missing && hasActions
        const sel = selectable(e)
        return (
          <div className={'dg-tr ' + (sel ? 'dg-click ' : '') + cols}
            key={e.path + '|' + e.owner + '|' + i}
            title={e.path + '\n' + (
              sel === 'object' ? `Click to select “${e.owner}” in the viewport`
                : sel === 'material' ? `Click to select the material “${e.owner}”`
                  : 'This reference belongs to no object or material (e.g. a take or the render settings) — nothing to select')}
            onClick={() => { if (sel) onFocus(e) }}
            {...(sel ? rowButton(() => onFocus(e)) : {})}>
            <span className="dg-cell-file">
              <span className="fl-dot" style={{ background: statusDot(e.missing) }} />
              <span className={'fa-kind fk-' + e.kind}>{KIND_LABEL[e.kind] || e.kind}</span>
              <span className="dg-cut">{e.file}</span>
            </span>
            <span className="dim dg-cut">{e.owner || '—'}</span>
            <span className="num">{e.bytes > 0 ? humanBytes(e.bytes) : '—'}</span>
            {/* The badge states WHAT THE PATH IS — never what it could become
                (same rule as the texture table: the old "→ relative" read as
                "this is relative"). The rewrite offer lives in the sidebar's
                "Make relative" action, and only Alembic paths qualify. */}
            <span className="dg-cell-path dim">
              <span className="dg-cut">{e.path}</span>
              {e.missing
                ? <span className="pill missing">missing</span>
                : e.absolute
                  ? <span className={'pill' + (e.relocatable && e.kind === 'alembic' ? ' fixable' : '')}
                      title={e.relocatable
                        ? (e.kind === 'alembic'
                            ? `Absolute, but the file lives under the project folder — “Make relative” rewrites it to ${e.rel_target || 'a project-relative path'}`
                            : 'Absolute; the file lives under the project folder, but only Alembic paths can be rewritten so far')
                        : 'Absolute path to a file outside the project folder'}>absolute</span>
                  : <span className="pill" title="Relative to the project folder">relative</span>}
            </span>
            {actionable && (
              <span className="rn-actions" onClick={(ev) => ev.stopPropagation()}>
                {onPick && (
                  <button className="rn-ok" title="Browse — pick the replacement file in Cinema 4D's file dialog (undoable)"
                    onClick={() => onPick(e)}><IconFolder /></button>
                )}
                {onAccept && (
                  <button className="rn-keep" title="Accept as missing — stops counting as a problem (restore below)"
                    onClick={() => onAccept(e)}><IconCheck /></button>
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
  const [query, setQuery] = useState('')
  const [confirm, setConfirm] = useState(false)
  const [note, setNote] = useState('')
  // Missing-files batching: relink after folder pick / accept-all confirm.
  const [relinkDir, setRelinkDir] = useState('')
  const [relinkConfirm, setRelinkConfirm] = useState(false)
  const [acceptConfirm, setAcceptConfirm] = useState(false)

  // Outcomes stay in the sidebar note; FAILURES go to the app's one error
  // banner (dismissable, same place as everywhere else).
  const fail = (e: any) => { org.setError(String(e.message || e)); setNote('') }
  const accepted = data?.accepted || []
  const setFileKeeps = async (keys: string[]) => {
    try {
      await call('set_keeps', { section: 'files', keys })
      await reload()
    } catch (e: any) { fail(e) }
  }
  const acceptOne = (e: FileEntry) => {
    setNote(`Accepted “${e.file}” as missing ✓ (restore below)`)
    setFileKeeps([...accepted, e.path])
  }
  const pickOne = async (e: FileEntry) => {
    setNote('Pick the file in the Cinema 4D window…')
    try {
      const r = await call('files_pick_path', { path: e.path })
      if (r.cancelled) { setNote('File picker cancelled.'); return }
      setNote(`Reference → “${r.picked}” ✓ (undoable)`)
      await reload()
    } catch (err: any) { fail(err) }
  }
  const doRelink = async () => {
    setRelinkConfirm(false)
    setNote('Searching for the missing files…')
    try {
      const r = await call('files_relink', { folder: relinkDir })
      setNote(`Relinked ${plural(r.relinked, 'file')} ✓ (undoable)`
        + (r.not_found ? ` · ${r.not_found} not found there` : ''))
      await reload()
    } catch (e: any) { fail(e) }
  }

  const entries = data?.entries || []
  // The search narrows both lists (file name, stored path, owner); the kind
  // chips stack on top of it.
  const q = query.trim().toLowerCase()
  const matches = (e: FileEntry) => (!kind || e.kind === kind)
    && (!q || e.file.toLowerCase().includes(q)
      || e.path.toLowerCase().includes(q)
      || (e.owner || '').toLowerCase().includes(q))
  /* eslint-disable react-hooks/exhaustive-deps -- `matches` is derived from kind+q */
  const missing = useMemo(() => entries.filter((e) => e.missing && matches(e)), [entries, kind, q])
  const present = useMemo(() => entries.filter((e) => !e.missing && matches(e)), [entries, kind, q])
  /* eslint-enable react-hooks/exhaustive-deps */
  // files_relink re-scans server-side and relinks EVERY missing file, ignoring
  // the kind chip — so the button and its confirm promise the unfiltered count.
  const allMissing = useMemo(() => entries.filter((e) => e.missing), [entries])
  const missPager = usePager(missing, undefined, [kind, q].join('|'))
  const pager = usePager(present, undefined, [kind, q].join('|'))

  const onFocus = (e: FileEntry) => {
    const sel = selectable(e)
    if (sel === 'object') org.doFocus(e.guid!, e.owner)
    else if (sel === 'material') org.doFocusMaterial(e.owner)
  }

  const doMakeRelative = async () => {
    setConfirm(false)
    setNote('')
    try {
      const r = await call('files_make_relative', {})
      setNote(`Rewrote ${plural(r.fixed, 'path')} ✓ (undoable)`
        + (r.skipped ? ` · ${r.skipped} skipped` : ''))
      await reload()
    } catch (e: any) { fail(e) }
  }

  if (!data) {
    return loading
      ? <div className="empty-note">Scanning external files…</div>
      : error
        ? <EmptyState message={`Files scan failed: ${error}`}
            actionLabel="Retry" onAction={reload} busy={loading} />
        : <EmptyState message="No scene scanned yet — open your scene in Cinema 4D."
            actionLabel="Scan files" onAction={reload} busy={loading} />
  }

  const s = data.summary
  // files_make_relative only rewrites Alembic references — every other kind is
  // counted as skipped server-side, so the button must not promise them.
  const reloc = entries.filter((e) => e.relocatable && e.kind === 'alembic').length
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
          <input className="search" placeholder="Search file, path or owner…"
            value={query} onChange={(e) => setQuery(e.target.value)} />
          <div className="substats">
            <span><b>{s.total}</b> files</span>
            <span><b>{humanBytes(s.total_bytes)}</b> on disk</span>
            <span className={s.missing_count ? 'warn' : ''}><b>{s.missing_count}</b> missing</span>
          </div>

          <FilterChips label="Kind" value={kind} empty="" onChange={setKind}
            options={KINDS
              .filter(([key]) => !key || s.by_kind[key])
              .map(([key, label]) => ({
                key,
                label,
                count: key ? (s.by_kind[key] || 0) : s.total,
                title: key ? `Show only ${label} files` : 'Show every kind',
              }))} />

          <div className="section-head sm"><span>Actions</span></div>
          <h4 className="side-action-title">Relative paths</h4>
          {!data.doc_path && (
            <p className="hint-sm">Project not saved — paths cannot be made relative yet.</p>
          )}
          <ActionButton tone="go" disabled={loading || !canFix}
            title={canFix
              ? `Rewrite ${reloc} absolute path(s) under the project folder to relative (undoable)`
              : 'No absolute paths inside the project folder'}
            onClick={() => setConfirm(true)}>
            Make relative ({reloc})
          </ActionButton>
          {note && <p className="example" style={{ marginTop: 4 }}>{note}</p>}
        </aside>

        <div className="stacked" style={{ minWidth: 0 }}>
          {missPager.total > 0 && (
            <section className="card">
              <div className="card-head">
                <h3>Missing files</h3>
                <span className="head-count hc-todo">{missPager.total} missing</span>
                <span className="wb-head-actions">
                  <ActionButton tone="go" disabled={loading}
                    title="Pick a folder in Cinema 4D — it is searched recursively for the missing file names and every match is relinked (undoable)"
                    onClick={() => {
                      call('pick_folder', { title: 'Folder to search for the missing files' })
                        .then((r) => { if (r.path) { setRelinkDir(r.path); setRelinkConfirm(true) } })
                        .catch(() => {})
                    }}>
                    Relink {allMissing.length}
                  </ActionButton>
                  <ActionButton disabled={loading}
                    title="Accept all as missing — they stop counting as problems (restore below)"
                    onClick={() => setAcceptConfirm(true)}>
                    Accept {missPager.total}
                  </ActionButton>
                  <ActionButton disabled={loading || !missing.some((e) => e.guid != null)}
                    title="Select every object referencing a missing file in Cinema 4D — inspect or replace them in one go"
                    onClick={async () => {
                      const guids = missing.map((e) => e.guid).filter((g): g is number => g != null)
                      try {
                        const r = await call('files_select', { guids })
                        setNote(`Selected ${plural(r.selected, 'object')} with missing files in C4D ✓`)
                      } catch (e: any) { fail(e) }
                    }}>
                    Select in C4D
                  </ActionButton>
                </span>
              </div>
              <p className="hint-sm">Per row: the folder icon picks the replacement file in C4D's file dialog · the grey ✓ accepts it as missing.</p>
              <FileTable rows={missPager.rows} onFocus={onFocus}
                onPick={pickOne} onAccept={acceptOne} />
              <Pager pager={missPager} />
            </section>
          )}

          <section className="card">
            <div className="card-head">
              <h3>Referenced files</h3>
              <span className="head-count">{pager.total} files</span>
            </div>
            {pager.total
              ? <>
                  <FileTable rows={pager.rows} onFocus={onFocus} />
                  <Pager pager={pager} />
                </>
              : <div className="empty-note">
                  {q ? 'No external files match the search.'
                    : `No external files${kind ? ` of kind “${KIND_LABEL[kind]}”` : ''}`}
                </div>}
          </section>

        </div>
      </div>

      {relinkConfirm && (
        <ConfirmModal
          title="Relink missing files"
          message={`Search “${relinkDir}” (including subfolders) for the ${plural(allMissing.length, 'missing file name')} in the scene — the kind filter does not narrow this — and relink every match (project-relative when possible, one undo step). Files not found there are left as-is. Continue?`}
          confirmLabel={`✓ Relink ${allMissing.length}`}
          onConfirm={doRelink}
          onCancel={() => setRelinkConfirm(false)}
        />
      )}
      {acceptConfirm && (
        <ConfirmModal
          title="Accept all as missing"
          message={`Accept all ${plural(missPager.total, 'missing file')} as missing. Nothing changes in the scene — they just stop counting as problems (restore any time below). Continue?`}
          confirmLabel={`✓ Accept ${missPager.total}`}
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
          message={`Rewrite ${plural(reloc, 'absolute Alembic path')} that live under the project folder to project-relative paths. Other asset kinds are left untouched. This is a single, undoable step.`}
          confirmLabel={`Make ${reloc} relative`}
          onConfirm={doMakeRelative}
          onCancel={() => setConfirm(false)}
        />
      )}
    <AcceptedPanel org={org} />
    </div>
  )
}
