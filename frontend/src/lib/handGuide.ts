import type {
  LayerDiff, PlanResult, RenameDiff, SceneReport, TranslateDiff,
} from '../types'

// "Take my hand" — the cross-area guided walk-through. This module is pure
// planning: it turns the loaded plans into a SHORT list of decisions. Small
// groups (≤ DETAIL_LIMIT findings) become one card per finding; big groups
// collapse into ONE batch card with a count and a few examples — nobody wants
// to answer 1000 individual questions.
export const DETAIL_LIMIT = 6
export const EXAMPLE_LIMIT = 5

export type HandArea = 'naming' | 'translate' | 'layers' | 'materials'

export interface HandStep {
  key: string
  area: HandArea
  // What the yes-button does, dispatched by the overlay component.
  action:
    | { kind: 'rename'; guids: number[] }
    | { kind: 'translate'; guids: number[] }
    | { kind: 'assign-layer'; guids: number[]; layer: string }
    | { kind: 'keep-layerless'; names: string[] }
    | { kind: 'delete-material'; name: string }
    | { kind: 'delete-materials'; count: number }
  count: number
  headline: string
  // old -> new (or name -> target) examples; batch cards show the first few.
  examples: { from: string; to: string }[]
  yesLabel: string
}

const truncate = (s: string, max = 40): string =>
  s.length > max ? s.slice(0, max - 1) + '…' : s

function group<T>(items: T[], keyFn: (t: T) => string): Map<string, T[]> {
  const m = new Map<string, T[]>()
  for (const it of items) {
    const k = keyFn(it)
    const arr = m.get(k)
    if (arr) arr.push(it)
    else m.set(k, [it])
  }
  return m
}

// One area's findings -> per-item cards for small groups, one batch card for
// big ones. `describe` renders the group key into the batch headline.
function stepsForGroups<T>(
  groups: Map<string, T[]>,
  make: (items: T[], groupKey: string, single: boolean) => HandStep,
): HandStep[] {
  const out: HandStep[] = []
  for (const [key, items] of groups) {
    if (items.length <= DETAIL_LIMIT) {
      for (const it of items) out.push(make([it], key, true))
    } else {
      out.push(make(items, key, false))
    }
  }
  return out
}

export interface HandGuideInput {
  report: SceneReport | null
  naming: PlanResult<RenameDiff> | null
  translation: PlanResult<TranslateDiff> | null
  layerSuggestions: PlanResult<LayerDiff> | null
  keptLayers: Set<string>
}

export function buildHandGuideSteps(input: HandGuideInput): HandStep[] {
  const steps: HandStep[] = []

  // 1. Naming — grouped by the rule(s) that caused the rename, so one card
  //    reads "812 names get their casing fixed" instead of 812 questions.
  const namingDiff = input.naming?.diff || []
  const namingGroups = group(namingDiff, (d) => (d.rules || ['casing']).join(' + '))
  steps.push(...stepsForGroups(namingGroups, (items, rule, single) => ({
    key: `naming|${rule}|${items[0].guid}`,
    area: 'naming',
    action: { kind: 'rename', guids: items.map((d) => d.guid) },
    count: items.length,
    headline: single
      ? `Rename “${truncate(items[0].old)}” → “${truncate(items[0].new)}”?`
      : `${items.length} names break the “${rule}” rule — fix them all?`,
    examples: items.slice(0, EXAMPLE_LIMIT).map((d) => ({ from: d.old, to: d.new })),
    yesLabel: single ? 'Rename' : `Rename all ${items.length}`,
  })))

  // 2. Translate — one decision for the whole language move.
  const trDiff = input.translation?.diff || []
  if (trDiff.length) {
    const single = trDiff.length === 1
    steps.push({
      key: 'translate|all',
      area: 'translate',
      action: { kind: 'translate', guids: trDiff.map((d) => d.guid) },
      count: trDiff.length,
      headline: single
        ? `Translate “${truncate(trDiff[0].old)}” → “${truncate(trDiff[0].new)}”?`
        : `${trDiff.length} names are in another language — translate them all?`,
      examples: trDiff.slice(0, EXAMPLE_LIMIT).map((d) => ({ from: d.old, to: d.new })),
      yesLabel: single ? 'Translate' : `Translate all ${trDiff.length}`,
    })
  }

  // 3. Layers — ancestor suggestions grouped by target layer; whatever has
  //    no suggestion becomes one "accept as-is" decision.
  const nodes = input.report?.nodes || []
  const noLayer = nodes.filter((n) => !n.layer && !input.keptLayers.has(n.name))
  const suggestionByGuid = new Map<number, string>()
  for (const d of input.layerSuggestions?.diff || []) suggestionByGuid.set(d.guid, d.layer)
  const suggested = noLayer.filter((n) => suggestionByGuid.has(n.guid))
  const unsuggested = noLayer.filter((n) => !suggestionByGuid.has(n.guid))
  const layerGroups = group(suggested, (n) => suggestionByGuid.get(n.guid)!)
  steps.push(...stepsForGroups(layerGroups, (items, layer, single) => ({
    key: `layers|${layer}|${items[0].guid}`,
    area: 'layers',
    action: { kind: 'assign-layer', guids: items.map((n) => n.guid), layer },
    count: items.length,
    headline: single
      ? `Put “${truncate(items[0].name)}” on layer “${layer}” (like its parent)?`
      : `${items.length} objects sit under “${layer}” parents — assign that layer to all?`,
    examples: items.slice(0, EXAMPLE_LIMIT).map((n) => ({ from: n.name, to: layer })),
    yesLabel: single ? 'Assign layer' : `Assign all ${items.length}`,
  })))
  if (unsuggested.length) {
    steps.push({
      key: 'layers|keep-rest',
      area: 'layers',
      action: { kind: 'keep-layerless', names: unsuggested.map((n) => n.name) },
      count: unsuggested.length,
      headline: unsuggested.length === 1
        ? `“${truncate(unsuggested[0].name)}” has no layer and no suggestion — accept as-is?`
        : `${unsuggested.length} objects have no layer and no suggestion — accept them as-is?`,
      examples: unsuggested.slice(0, EXAMPLE_LIMIT).map((n) => ({ from: n.name, to: '(no layer)' })),
      yesLabel: unsuggested.length === 1 ? 'Accept as-is' : `Accept all ${unsuggested.length}`,
    })
  }

  // 4. Materials — unused ones. Few -> one question each, many -> one sweep.
  const unused = input.report?.materials?.unused || []
  const unusedGroups = unused.length ? new Map([['unused', unused]]) : new Map<string, string[]>()
  steps.push(...stepsForGroups(unusedGroups, (names, _key, single) => (single
    ? {
      key: `materials|${names[0]}`,
      area: 'materials',
      action: { kind: 'delete-material', name: names[0] },
      count: 1,
      headline: `Material “${truncate(names[0])}” is used by nothing — delete it?`,
      examples: [{ from: names[0], to: '(deleted)' }],
      yesLabel: 'Delete',
    }
    : {
      key: 'materials|all-unused',
      area: 'materials',
      action: { kind: 'delete-materials', count: names.length },
      count: names.length,
      headline: `${names.length} materials are used by nothing — delete them all?`,
      examples: names.slice(0, EXAMPLE_LIMIT).map((n) => ({ from: n, to: '(deleted)' })),
      yesLabel: `Delete all ${names.length}`,
    })))

  return steps
}
