import { useState } from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import type { TextureEntry } from '../types'
import { humanBytes } from '../lib/format'
import { IconTrash } from '../components/icons'

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

export default function TexturesTab({ org }: { org: Organizer }) {
  const { report, busy } = org
  const [confirm, setConfirm] = useState(false)
  const tex = report?.textures

  if (!report) {
    return (
      <div className="empty-state">
        <p>No scene analyzed yet.</p>
        <button onClick={org.doAnalyze} disabled={busy}>Analyze scene</button>
      </div>
    )
  }
  if (!tex) {
    return <div className="misc"><section className="card">
      <div className="card-head"><h3>Textures</h3></div>
      <div className="fl-empty">No texture data.</div>
    </section></div>
  }

  const fixable = tex.relocatable_count
  const absolute = [...tex.absolute].sort(bySize)
  const relative = [...tex.relative].sort(bySize)

  return (
    <div className="misc">
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
      </section>

      <section className="card" style={{ marginTop: 16 }}>
        <div className="card-head">
          <h3><IconTrash /> Absolute paths</h3>
          <span className="dim" style={{ fontSize: 11 }}>{tex.absolute_count}</span>
        </div>
        {absolute.length
          ? <div className="focuslist">{absolute.map((e, i) => <TexRow key={i} e={e} />)}</div>
          : <div className="fl-empty">No absolute texture paths 🎉</div>}
      </section>

      <section className="card" style={{ marginTop: 16 }}>
        <div className="card-head">
          <h3>Relative paths</h3>
          <span className="dim" style={{ fontSize: 11 }}>{tex.relative_count}</span>
        </div>
        {relative.length
          ? <div className="focuslist">{relative.map((e, i) => <TexRow key={i} e={e} />)}</div>
          : <div className="fl-empty">No relative texture paths.</div>}
      </section>
    </div>
  )
}
