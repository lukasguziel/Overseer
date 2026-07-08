import { useState } from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import type { TextureEntry } from '../types'
import { humanBytes } from '../lib/format'
import { IconTrash } from '../components/icons'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedSection from '../components/AcceptedSection'
import EmptyState from '../components/EmptyState'

// Colour the resolution tag by tier so heavy 4K/8K maps jump out.
function resTier(e: TextureEntry): string {
  const px = Math.max(e.width, e.height)
  if (px >= 8192) return 'res-8k'
  if (px >= 4096) return 'res-4k'
  if (px >= 2048) return 'res-2k'
  return 'res-sm'
}

// One texture row: file + material + path, dimensions, size, status badges.
function TexRow({ e }: { e: TextureEntry }) {
  const dot = e.missing ? 'var(--err)' : e.absolute ? 'var(--warn)' : 'var(--apply)'
  return (
    <div className="fl-row static tex-row" title={e.resolved || e.path}>
      <span className="fl-dot" style={{ background: dot }} />
      <span className="tex-main">
        <span className="fl-name">{e.file}</span>
        <span className="tex-path dim">{e.path}</span>
      </span>
      <span className="tex-specs">
        {e.res_tag && <span className={'tex-badge tex-res ' + resTier(e)}>{e.res_tag}</span>}
        {e.width > 0 && <span className="tex-dim dim">{e.width}×{e.height}</span>}
        {e.bytes > 0 && <span className="tex-size">{humanBytes(e.bytes)}</span>}
      </span>
      <span className="tex-badges">
        <span className="tex-mat dim">{e.material}</span>
        {!e.used && <span className="tex-badge unused">unused</span>}
        {e.missing && <span className="tex-badge missing">missing</span>}
        {e.relocatable && <span className="tex-badge fixable">→ relative</span>}
      </span>
    </div>
  )
}

const bySize = (a: TextureEntry, b: TextureEntry) => b.bytes - a.bytes

export default function MaterialsTab({ org }: { org: Organizer }) {
  const { report, busy } = org
  const [confirm, setConfirm] = useState(false)         // make textures relative
  const [bulkConfirm, setBulkConfirm] = useState(false) // delete unused materials
  const mat = report?.materials
  const tex = report?.textures

  if (!report) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  const fixable = tex?.relocatable_count ?? 0
  const absolute = tex ? [...tex.absolute].sort(bySize) : []
  const relative = tex ? [...tex.relative].sort(bySize) : []

  const onHidden = new Set(mat?.only_hidden || [])
  const deletable = mat?.deletable_count ?? (mat?.unused.length ?? 0)
  const acceptedList = mat?.accepted || []

  return (
    <div className="stacked">
      {/* ---- Materials overview (shading definitions) ---------------- */}
      <section className="card">
        <div className="card-head">
          <h3>Materials</h3>
        </div>
        {mat ? (
          <>
            <div className="substats" style={{ marginBottom: 12 }}>
              <span><b>{mat.total}</b> total</span>
              <span className={mat.unused.length ? 'warn' : ''}><b>{mat.unused.length}</b> unused</span>
              {acceptedList.length > 0 && <span><b>{acceptedList.length}</b> accepted</span>}
              {onHidden.size > 0 && <span><b>{onHidden.size}</b> on hidden</span>}
              <span className={mat.missing_textures ? 'warn' : ''}><b>{mat.missing_textures || 0}</b> missing tex</span>
            </div>
            <Workbench
              title="Unused materials" count={deletable} loading={busy}
              empty="Every material is in use 🎉"
              applyLabel={bulkConfirm ? `Really delete ${deletable}?` : 'Process all'}
              onApply={() => {
                if (bulkConfirm) { org.doDeleteAllUnused(deletable); setBulkConfirm(false) }
                else setBulkConfirm(true)
              }}
              busy={busy} progress={org.progress}
              note={bulkConfirm ? 'Click again to delete all unused materials (undoable).' : null}
            >
              <div className="rename-list">
                {mat.unused.filter((nm) => !onHidden.has(nm)).map((nm) => (
                  <SuggestionRow key={nm} busy={busy}
                    applyTitle="Apply — delete this material (undoable)"
                    onApply={() => org.doDeleteMaterial(nm)}
                    onAcceptAsIs={() => org.keep('materials', nm)}
                  >
                    <span className="fl-dot" style={{ background: 'var(--dim2)' }} />
                    <span className="rn-old" title={nm}>{nm}</span>
                    <span className="rn-arrow">→</span>
                    <span className="rn-new dim">delete</span>
                  </SuggestionRow>
                ))}
                {mat.unused.filter((nm) => onHidden.has(nm)).map((nm) => (
                  <div className="fl-row static mat-row" key={nm}>
                    <span className="fl-dot" style={{ background: 'var(--warn)' }} />
                    <span className="fl-name">{nm}</span>
                    <span className="tex-badge unused" title="Used only by hidden objects — kept safe from deletion">on hidden</span>
                  </div>
                ))}
              </div>
            </Workbench>
            <AcceptedSection items={mat.accepted_all || []}
              onRestore={(nm) => org.unkeep('materials', nm)}
              hint="Accepted materials stay in the scene, are remembered (config) and no longer count as problems." />
            {mat.missing.length > 0 && (
              <>
                <div className="chipgroup-label" style={{ marginTop: 12 }}>Missing textures</div>
                <div className="focuslist">
                  {mat.missing.slice(0, 10).map((t, i) => (
                    <div className="fl-row static" key={i}>
                      <span className="fl-dot" style={{ background: 'var(--err)' }} />
                      <span className="fl-name">{t.material}</span>
                      <span className="fl-meta dim">{t.file}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        ) : <div className="fl-empty">No material data.</div>}
      </section>

      {/* ---- Textures (image files on disk) -------------------------- */}
      <section className="card">
        <div className="card-head">
          <h3>Textures</h3>
          {fixable > 0 && (
            confirm ? (
              <span className="mat-confirm">
                make {fixable} relative?
                <button className="mat-yes" title="Confirm — rewrite absolute paths to relative"
                  onClick={() => { org.doFixTexturesRelative(); setConfirm(false) }}>✓</button>
                <button className="mat-no" title="Cancel" onClick={() => setConfirm(false)}>✕</button>
              </span>
            ) : (
              <button className="trash-btn fix-btn" disabled={busy}
                title={`Rewrite ${fixable} absolute path(s) that live under the project folder to relative (undoable)`}
                onClick={() => setConfirm(true)}>
                Fix paths<span className="trash-count">{fixable}</span>
              </button>
            )
          )}
        </div>
        {tex ? (
          <>
            <p className="hint-sm">
              Real pixel size, disk size and a resolution tag per map — spot the 8K
              textures eating memory that could be 4K, and the <b>absolute</b> paths
              that break when the project moves. Sorted by file size (heaviest first).
            </p>
            <div className="substats" style={{ marginBottom: 4 }}>
              <span><b>{tex.total}</b> textures</span>
              <span><b>{humanBytes(tex.total_bytes)}</b> on disk</span>
              <span className={tex.absolute_count ? 'warn' : ''}><b>{tex.absolute_count}</b> absolute</span>
              <span><b>{tex.relative_count}</b> relative</span>
              <span className={tex.missing_count ? 'warn' : ''}><b>{tex.missing_count}</b> missing</span>
            </div>
            {tex.doc_path
              ? <p className="example" style={{ marginTop: 8 }}>Project: <code>{tex.doc_path}</code></p>
              : <p className="example warn" style={{ marginTop: 8 }}>Project not saved — paths cannot be made relative yet.</p>}
          </>
        ) : (
          <>
            <div className="fl-empty">No texture data.</div>
            {report.textures_error && (
              <p className="example warn" style={{ marginTop: 8 }}>
                Texture scan failed: <code>{report.textures_error}</code>
              </p>
            )}
          </>
        )}
      </section>

      {tex && (
        <>
          <section className="card">
            <div className="card-head">
              <h3><IconTrash /> Absolute paths</h3>
              <span className="card-hint">{tex.absolute_count}</span>
            </div>
            {absolute.length
              ? <div className="focuslist">{absolute.map((e, i) => <TexRow key={i} e={e} />)}</div>
              : <div className="fl-empty">No absolute texture paths 🎉</div>}
          </section>

          <section className="card">
            <div className="card-head">
              <h3>Relative paths</h3>
              <span className="card-hint">{tex.relative_count}</span>
            </div>
            {relative.length
              ? <div className="focuslist">{relative.map((e, i) => <TexRow key={i} e={e} />)}</div>
              : <div className="fl-empty">No relative texture paths.</div>}
          </section>
        </>
      )}
    </div>
  )
}
