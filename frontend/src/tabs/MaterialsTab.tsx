// Materials tab: the unused-materials worklist, then the Textures area
// (tabs/TexturesSection.tsx — its own file so each area reads in one piece).
import { useEffect, useState } from 'react'
import { call } from '../api'
import type { Organizer } from '../hooks/useOrganizer'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedPanel from '../components/AcceptedPanel'
import AreaHistory from '../components/AreaHistory'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'
import TexturesSection from './TexturesSection'
import './materials.css'

// Material preview sphere (as in the C4D material manager); falls back to the
// plain status dot until the thumbnail arrives (or if C4D can't render one).
function MatThumb({ src, fallback }: { src?: string; fallback: string }) {
  return src
    ? <img className="mat-thumb" src={src} alt="" draggable={false} />
    : <span className="fl-dot" style={{ background: fallback }} />
}

export default function MaterialsTab({ org }: { org: Organizer }) {
  const { report, busy } = org
  const mat = report?.materials
  const tex = report?.textures

  // mat.unused is scope-aware (All objects additionally contains the
  // hidden-only materials); only_hidden just marks which rows get the badge.
  const unusedPager = usePager(mat?.unused || [], 10)
  const onHiddenSet = new Set(mat?.only_hidden || [])

  // Preview spheres for the unused list, fetched once per material set.
  const [previews, setPreviews] = useState<Record<string, string>>({})
  const wanted = [...(mat?.unused || []), ...(mat?.only_hidden || [])].join('\n')
  useEffect(() => {
    const names = wanted ? wanted.split('\n') : []
    if (!names.length) { setPreviews({}); return }
    let alive = true
    ;(async () => {
      for (let i = 0; i < names.length && alive; i += 8) {
        try {
          const r = await call('material_previews', { names: names.slice(i, i + 8), size: 48 })
          if (alive) setPreviews((prev) => ({ ...prev, ...(r.previews || {}) }))
        } catch { /* dots stay as fallback */ }
      }
    })()
    return () => { alive = false }
  }, [wanted])

  if (!report) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  const missingCount = tex?.missing_count ?? 0
  const deletable = mat?.deletable_count ?? (mat?.unused.length ?? 0)
  const acceptedList = mat?.accepted || []

  return (
    <div className="stacked">
      {/* ---- Materials: the scene's numbers, then the ONE worklist.
           No card wrapping a card — the Workbench IS the panel, and its batch
           buttons sit top right like in every other area. The tab's own
           SectionIntro (App.tsx TAB_INTRO) already titles this area. ------ */}
      {mat ? (
          <>
            {/* Visibility toggle = scope: 'Visible only' lists materials used
                NOWHERE; 'All objects' additionally lists the ones used only
                by hidden objects — same list, fully actionable, badge marks
                them. Materials any visible object uses never show up. */}
            <div className="substats">
              <span><b>{mat.total}</b> total</span>
              <span className={deletable ? 'warn' : ''}><b>{deletable}</b> unused</span>
              {(mat.only_hidden?.length ?? 0) > 0 && (
                <span><b>{mat.only_hidden?.length}</b> of them only on hidden</span>
              )}
              {acceptedList.length > 0 && <span><b>{acceptedList.length}</b> accepted</span>}
              <span className={mat.missing_textures ? 'warn' : ''}><b>{mat.missing_textures || 0}</b> missing tex</span>
            </div>
            <Workbench
              title="Unused materials" count={deletable} loading={busy}
              empty={
                <>
                  {org.includeHidden
                    ? 'Every material is in use'
                    : 'Every material is used by a visible object (switch to All objects to include hidden usage)'}
                  {missingCount > 0 && (
                    <span className="wb-empty-more">
                      Check the missing texture paths below — {missingCount} still need{missingCount === 1 ? 's' : ''} attention
                      <span className="wb-empty-arrow">↓</span>
                    </span>
                  )}
                </>
              }
              hint="Click a row to select the material in Cinema 4D · the trash button deletes it · the grey ✓ keeps it"
              applyLabel="Delete all" applyTone="danger"
              onApply={() => org.doDeleteAllUnused(deletable)}
              onAcceptAll={() => org.keepAll('materials')}
              busy={busy} progress={org.progress}
            >
              <div className="rename-list">
                {unusedPager.rows.map((nm, i) => {
                  const onHidden = onHiddenSet.has(nm)
                  return (
                    // Names can legitimately repeat (duplicate materials) —
                    // the index keeps React keys unique, no ghost rows.
                    <SuggestionRow key={`${nm}|${i}`} busy={busy} deletes
                      applyTitle={onHidden
                        ? 'Delete this material. Careful: hidden objects still use it and will lose it (undoable)'
                        : 'Delete this material (undoable)'}
                      onApply={() => org.doDeleteMaterial(nm)}
                      onAcceptAsIs={() => org.keep('materials', nm)}
                      onFocus={() => org.doFocusMaterial(nm)}
                    >
                      <MatThumb src={previews[nm]} fallback={onHidden ? 'var(--warn)' : 'var(--dim2)'} />
                      <span className="rn-old" title={nm}>{nm}</span>
                      {onHidden && (
                        <span className="pill unused"
                          title="Used only by objects that are hidden in the editor — deleting removes it from them too">
                          on hidden
                        </span>
                      )}
                      <span className="rn-arrow">→</span>
                      <span className="rn-new dim">delete</span>
                    </SuggestionRow>
                  )
                })}
              </div>
              <Pager pager={unusedPager} />
            </Workbench>
          </>
      ) : <div className="empty-note">No material data.</div>}

      {/* ---- Textures: ONE area — settings/filters left, paths right --- */}
      <TexturesSection org={org} />

      {/* Everything accepted on this tab, collected at its foot — decisions
          the artist already made belong out of the worklists, not wedged in
          between the Materials section and the Textures one. */}
    <AcceptedPanel org={org} />
    <AreaHistory org={org} area="materials & textures"
      kinds={['materials_delete', 'textures_relative', 'textures_collect',
        'textures_relink', 'textures_edit', 'textures_repath',
        'textures_resize', 'textures_clear']} />
    </div>
  )
}
