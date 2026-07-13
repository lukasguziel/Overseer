import { useEffect, useMemo, useRef, useState } from 'react'
import type { Organizer } from '../hooks/useOrganizer'
import { buildHandGuideSteps, type HandStep } from '../lib/handGuide'
import GuideFlow, { type GuideCard } from './GuideFlow'

const AREA_LABEL: Record<HandStep['area'], string> = {
  naming: 'Naming', translate: 'Translate', layers: 'Layers', materials: 'Materials',
}

// "Take my hand" — fullscreen guided walk-through across ALL areas. On start
// it refreshes every plan (stepped overlay from reloadEverything), then walks
// the batched decisions from lib/handGuide via the shared GuideFlow cards.
// Steps are frozen at start: applying a batch must not reshuffle the deck.
export default function HandGuide({ org, onExit }: { org: Organizer; onExit: () => void }) {
  const [phase, setPhase] = useState<'loading' | 'guiding'>('loading')
  const [steps, setSteps] = useState<HandStep[]>([])
  const started = useRef(false)

  // Snapshot the plans AFTER the full reload so the deck reflects fresh data.
  const orgRef = useRef(org)
  orgRef.current = org
  useEffect(() => {
    if (started.current) return
    started.current = true
    ;(async () => {
      try { await orgRef.current.reloadEverything() } catch { /* stale plans still work */ }
      const o = orgRef.current
      setSteps(buildHandGuideSteps({
        report: o.report, naming: o.naming, translation: o.translation,
        layerSuggestions: o.layerSuggestions,
        keptLayers: o.keeps.layers,
      }))
      setPhase('guiding')
    })()
  }, [])

  const runStep = (s: HandStep) => {
    const o = orgRef.current
    const a = s.action
    const label = `${s.count} item${s.count === 1 ? '' : 's'}`
    if (a.kind === 'rename') o.applyNamingMany(a.guids, label)
    else if (a.kind === 'translate') o.applyTranslateMany(a.guids, label)
    else if (a.kind === 'assign-layer') o.doAssignLayer(a.guids, a.layer)
    else if (a.kind === 'keep-layerless') o.keepMany('layers', a.names)
    else if (a.kind === 'delete-material') o.doDeleteMaterial(a.name)
    else if (a.kind === 'delete-materials') o.doDeleteAllUnused(a.count)
  }

  const cards: GuideCard[] = useMemo(() => steps.map((s) => ({
    key: s.key,
    headline: (
      <>
        <span className={'hand-area hand-area-' + s.area}>{AREA_LABEL[s.area]}</span>
        {s.headline}
      </>
    ),
    body: (
      <div className="hand-examples">
        {s.examples.map((ex, i) => (
          <div className="hand-ex" key={i}>
            <span className="rn-old">{ex.from}</span>
            <span className="rn-arrow">→</span>
            <span className="rn-new">{ex.to}</span>
          </div>
        ))}
        {s.count > s.examples.length && (
          <div className="hand-more">… and {s.count - s.examples.length} more —
            one click decides the whole batch (undoable).</div>
        )}
      </div>
    ),
    yesLabel: s.yesLabel,
    onYes: () => runStep(s),
  })), [steps])

  return (
    <div className="hand-overlay">
      <div className="hand-box">
        <div className="hand-head">
          <span className="hand-icon">🫱</span>
          <h2>Take my hand</h2>
        </div>
        {phase === 'loading'
          ? (
            <div className="hand-loading">
              {org.reloadProgress
                ? <>Checking every area… ({org.reloadProgress.step + 1}/{org.reloadProgress.total} · {org.reloadProgress.label})</>
                : 'Checking every area…'}
            </div>
          )
          : (
            <GuideFlow cards={cards} onExit={onExit}
              header={({ index, jump }) => {
                // Area chips: show where in the walk-through you are and jump
                // between areas (first card of each area).
                const current = steps[index]?.area
                const areas = [...new Set(steps.map((s) => s.area))]
                return (
                  <div className="hand-areas">
                    {areas.map((a) => {
                      const first = steps.findIndex((s) => s.area === a)
                      const n = steps.filter((s) => s.area === a).length
                      return (
                        <button key={a}
                          className={'hand-area-chip' + (current === a ? ' on' : '')}
                          title={`Jump to the ${n} ${AREA_LABEL[a]} decision${n === 1 ? '' : 's'}`}
                          onClick={() => jump(first)}>
                          {AREA_LABEL[a]} <em>{n}</em>
                        </button>
                      )
                    })}
                  </div>
                )
              }}
              labels={{
                no: 'No',
                skip: 'Skip',
                exit: 'Exit guide',
                done: 'That was everything — your scene is worked through.',
                empty: 'Nothing to decide — every area is already clean.',
              }} />
          )}
      </div>
    </div>
  )
}
