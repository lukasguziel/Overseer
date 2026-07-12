import { useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import useAudit from '../hooks/useAudit'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import ConfirmModal from '../components/ConfirmModal'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'
import Tip from '../components/Tip'
import './tags.css'
import ActionButton from '../components/ActionButton'

interface TagObjectRef { guid: number; name: string; tag_name: string }
interface TagType { type_id: number; label: string; count: number; objects: TagObjectRef[] }
interface MissingPhong { guid: number; name: string }
interface DuplicateMat { guid: number; name: string; material: string; count: number }
interface AngleBucket { angle_deg: number; count: number }
interface TagsData {
  types: TagType[]
  findings: {
    missing_phong: MissingPhong[]
    duplicate_material_tags: DuplicateMat[]
    phong_angles: { distribution: AngleBucket[]; dominant_angle: number | null }
  }
  summary: { total_tags: number; tag_types: number; missing_phong: number; duplicate_material_tags: number }
}

const ANGLE_PRESETS = [30, 40, 60, 80]

// One expandable tag-type row: header with count + "Select in C4D", and a
// paged list of the objects carrying that tag when expanded.
function TagTypeRow({ type, org }: { type: TagType; org: Organizer }) {
  const [open, setOpen] = useState(false)
  const pager = usePager(type.objects)
  return (
    <div className="tags-type">
      <div className="tags-type-head">
        <button className="tags-type-toggle" onClick={() => setOpen(!open)}
          title={open ? 'Collapse' : 'Show objects carrying this tag'}>
          <span className="tags-type-caret">{open ? '▾' : '▸'}</span>
          <span className="tags-type-label">{type.label}</span>
          <span className="pill">{type.count}</span>
        </button>
        <ActionButton disabled={org.busy}
          title="Select every object carrying this tag type in Cinema 4D"
          onClick={() => call('tags_select', { type_id: type.type_id })
            .then((r) => org.setStatus(`Selected ${r.selected ?? type.count} object${type.count === 1 ? '' : 's'} in Cinema 4D`))
            .catch((e) => org.setStatus(`Select ✗ ${String(e.message || e)}`))}>
          Select in C4D
        </ActionButton>
      </div>
      {open && (
        <div className="tags-type-objs">
          {pager.rows.map((o, i) => (
            <button className="tags-obj-row" key={`${o.guid}-${i}`}
              title="Click to select & frame it in Cinema 4D"
              onClick={() => org.doFocus(o.guid, o.name)}>
              <span className="tags-obj-name">{o.name}</span>
              {o.tag_name && <span className="dim tags-obj-tag">{o.tag_name}</span>}
            </button>
          ))}
          <Pager pager={pager} />
        </div>
      )}
    </div>
  )
}

export default function TagsTab({ org }: { org: Organizer }) {
  const { data, loading, error, reload } = useAudit<TagsData>('tags_scan', true)
  const [note, setNote] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<null | { title: string; message: string; label: string; run: () => Promise<any> }>(null)
  const [angleInput, setAngleInput] = useState('')

  const missingPager = usePager(data?.findings.missing_phong || [])
  const dupPager = usePager(data?.findings.duplicate_material_tags || [])

  if (!data && !loading && error) {
    return <div className="empty-note">Tag scan failed: <code>{error}</code></div>
  }
  if (!data && !loading) {
    return <EmptyState message="No tag data yet." actionLabel="Scan tags"
      onAction={reload} busy={loading} />
  }

  const s = data?.summary
  const dominant = data?.findings.phong_angles.dominant_angle ?? null
  const busy = org.busy || loading

  // A number input's min/max only constrain the spinner, not typed text.
  const parsedAngle = parseFloat(angleInput)
  const customAngle = !isNaN(parsedAngle) && parsedAngle >= 0 && parsedAngle <= 180 ? parsedAngle : null

  async function run(fn: () => Promise<any>, describe: (r: any) => string) {
    setNote(null)
    try {
      const r = await fn()
      setNote(describe(r))
    } catch (e: any) {
      setNote('Failed: ' + String(e.message || e))
    }
    await reload()
  }

  function ask(title: string, message: string, label: string, fn: () => Promise<any>, describe: (r: any) => string) {
    setConfirm({ title, message, label, run: async () => { await run(fn, describe) } })
  }

  const setUniformAngle = (deg: number) => ask(
    'Set phong angle',
    `Set the phong angle to ${deg}° on all phong tags in the scene (one undo step). Continue?`,
    `Set ${deg}°`,
    () => call('tags_set_phong_angle', { angle_deg: deg }),
    (r) => `Set ${r.applied} phong tag${r.applied === 1 ? '' : 's'} to ${r.angle_deg}° ✓ (undoable)`,
  )

  return (
    <div className="stacked">
      {confirm && (
        <ConfirmModal title={confirm.title} message={confirm.message}
          confirmLabel={confirm.label}
          onConfirm={() => { const c = confirm; setConfirm(null); c.run() }}
          onCancel={() => setConfirm(null)} />
      )}

      <section className="card">
        <div className="card-head">
          <h3>Tags</h3>
          <span className="card-hint">every tag in the scene, audited</span>
        </div>
        <div className="substats">
          <span><b>{s?.total_tags ?? 0}</b> tags</span>
          <span><b>{s?.tag_types ?? 0}</b> types</span>
          <Tip text="Polygon objects without a Phong tag render hard-faceted. Below they can be given a Phong tag in batch.">
            <span className={s?.missing_phong ? 'warn' : ''}><b>{s?.missing_phong ?? 0}</b> missing phong</span>
          </Tip>
          <Tip text="Objects that carry the same material multiple times via several texture tags. The redundant copies do nothing.">
            <span className={s?.duplicate_material_tags ? 'warn' : ''}><b>{s?.duplicate_material_tags ?? 0}</b> duplicate material tags</span>
          </Tip>
        </div>
        {note && <p className="wb-note">{note}</p>}
      </section>

      {/* ---- Findings: side by side ----------------------------------- */}
      <div className="ov-cols2">
      <section className="card">
        <div className="card-head"><h3>Missing phong tags</h3></div>
        <p className="hint-sm">
          Polygon objects without a Phong tag render with faceted, hard shading.
          Add one at the scene's dominant angle{dominant != null ? ` (${dominant}°)` : ' (40°)'}.
        </p>
        <Workbench
          title="Polygon objects missing a Phong tag"
          count={missingPager.total} loading={loading}
          empty="Every polygon object has a Phong tag 🎉"
          hint="Click a row to select it in Cinema 4D · ✓ adds a Phong tag"
          applyLabel="Add all Phong tags"
          onApply={() => ask(
            'Add Phong tags',
            `Add a Phong tag to ${missingPager.total} object${missingPager.total === 1 ? '' : 's'} (one undo step). Continue?`,
            `Add ${missingPager.total} Phong tags`,
            () => call('tags_add_phong', {}),
            (r) => `Added ${r.applied} Phong tag${r.applied === 1 ? '' : 's'} at ${r.angle_deg}° ✓ (undoable)`,
          )}
          busy={busy} note={null} progress={org.progress}
        >
          <div className="rename-list">
            {missingPager.rows.map((m) => (
              <SuggestionRow key={m.guid} busy={busy}
                applyTitle="Apply — add a Phong tag to this object (undoable)"
                onApply={() => run(
                  () => call('tags_add_phong', { guids: [m.guid] }),
                  (r) => `Added ${r.applied} Phong tag ✓ (undoable)`)}
                onFocus={() => org.doFocus(m.guid, m.name)}
              >
                <span className="rn-old" title={m.name}>{m.name}</span>
                <span className="rn-arrow">→</span>
                <span className="rn-new dim">+ Phong</span>
              </SuggestionRow>
            ))}
          </div>
          <Pager pager={missingPager} />
        </Workbench>
      </section>

      <section className="card">
        <div className="card-head"><h3>Duplicate material tags</h3></div>
        <p className="hint-sm">
          These objects carry the same material more than once via texture tags —
          the redundant copies do nothing but clutter. Deleting keeps the first.
        </p>
        <Workbench
          title="Objects with duplicate material tags"
          count={dupPager.total} loading={loading}
          empty="No duplicate material tags 🎉"
          hint="Click a row to select it in Cinema 4D · ✓ removes the redundant copies"
          applyLabel="Delete all duplicates" applyTone="danger"
          onApply={() => ask(
            'Delete duplicate material tags',
            `Remove the redundant material tags on ${dupPager.total} object${dupPager.total === 1 ? '' : 's'}, keeping the first per material (one undo step). Continue?`,
            `Delete on ${dupPager.total} objects`,
            () => call('tags_delete_duplicates', {}),
            (r) => `Deleted ${r.deleted} duplicate material tag${r.deleted === 1 ? '' : 's'} ✓ (undoable)`,
          )}
          busy={busy} note={null} progress={org.progress}
        >
          <div className="rename-list">
            {dupPager.rows.map((d) => (
              <SuggestionRow key={d.guid} busy={busy}
                applyTitle="Apply — delete the redundant material tags on this object (undoable)"
                onApply={() => run(
                  () => call('tags_delete_duplicates', { guids: [d.guid] }),
                  (r) => `Deleted ${r.deleted} duplicate material tag${r.deleted === 1 ? '' : 's'} ✓ (undoable)`)}
                onFocus={() => org.doFocus(d.guid, d.name)}
              >
                <span className="rn-old" title={d.name}>{d.name}</span>
                <span className="rn-arrow">→</span>
                <span className="rn-new dim">{d.material} ×{d.count}</span>
              </SuggestionRow>
            ))}
          </div>
          <Pager pager={dupPager} />
        </Workbench>
      </section>
      </div>

      {/* ---- Phong angles + all tag types: side by side ---------------- */}
      <div className="ov-cols2">
      <section className="card">
        <div className="card-head">
          <Tip text="The Phong angle sets up to which edge angle surfaces are shaded smoothly. “Dominant” is the value used most often in the scene.">
            <h3>Phong angles</h3>
          </Tip>
          {dominant != null && <span className="card-hint">dominant {dominant}°</span>}
        </div>
        {(data?.findings.phong_angles.distribution.length ?? 0) === 0
          ? <div className="empty-note">No phong tags in the scene.</div>
          : (
            <>
              <div className="tags-dist">
                {data!.findings.phong_angles.distribution.map((b) => (
                  <div className="tags-dist-row" key={b.angle_deg}>
                    <span className={'tags-angle' + (b.angle_deg === dominant ? ' dominant' : '')}>{b.angle_deg}°</span>
                    <span className="dim">{b.count} tag{b.count === 1 ? '' : 's'}</span>
                  </div>
                ))}
              </div>
              <p className="hint-sm" style={{ marginTop: 10 }}>
                Set one uniform angle across all phong tags (one undo step):
              </p>
              <div className="tags-angle-set">
                {ANGLE_PRESETS.map((deg) => (
                  <button key={deg} className="chip-btn"
                    disabled={busy} onClick={() => setUniformAngle(deg)}>{deg}°</button>
                ))}
                <input className="nl-input tags-angle-input" type="number" min={0} max={180}
                  placeholder="custom" value={angleInput}
                  onChange={(e) => setAngleInput(e.target.value)} />
                <ActionButton tone="go" disabled={busy || customAngle === null}
                  title={angleInput !== '' && customAngle === null ? 'Enter an angle between 0 and 180°' : 'Set this angle on all phong tags'}
                  onClick={() => { if (customAngle !== null) setUniformAngle(customAngle) }}>
                  Set
                </ActionButton>
              </div>
            </>
          )}
      </section>

      {/* ---- All tag types ------------------------------------------- */}
      <section className="card">
        <div className="card-head">
          <h3>All tag types</h3>
          <span className="card-hint">{data?.types.length ?? 0}</span>
        </div>
        {(data?.types.length ?? 0) === 0
          ? <div className="empty-note">No tags in the scene.</div>
          : (
            <div className="tags-type-list">
              {data!.types.map((t) => (
                <TagTypeRow key={t.type_id} type={t} org={org} />
              ))}
            </div>
          )}
      </section>
      </div>
    </div>
  )
}
