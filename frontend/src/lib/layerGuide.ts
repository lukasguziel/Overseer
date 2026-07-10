import type { LayerMismatch, SceneNode } from '../types'

export type LayerGuideKind = 'suggestion' | 'no-layer' | 'mismatch'

export interface LayerGuideStep {
  kind: LayerGuideKind
  guid: number
  name: string
  layer?: string
  parent?: string
  parentLayer?: string
  childLayer?: string
}

// Ordered walk-through of every Layers-tab finding: the easy ancestor-layer
// suggestions first, then the remaining layerless objects, finally the
// informational parent/child mismatches. Each step maps to exactly one
// existing backend action (assign the layer, or accept the state as-is).
export function buildLayerGuideSteps(
  noLayer: SceneNode[],
  suggestionByGuid: Map<number, string>,
  mismatches: LayerMismatch[],
): LayerGuideStep[] {
  const suggestions: LayerGuideStep[] = []
  const plain: LayerGuideStep[] = []

  for (const n of noLayer) {
    const layer = suggestionByGuid.get(n.guid)
    if (layer) suggestions.push({ kind: 'suggestion', guid: n.guid, name: n.name, layer })
    else plain.push({ kind: 'no-layer', guid: n.guid, name: n.name })
  }

  const mixed: LayerGuideStep[] = mismatches.map((m) => ({
    kind: 'mismatch', guid: m.guid, name: m.name,
    parent: m.parent, parentLayer: m.parent_layer, childLayer: m.child_layer,
  }))

  return [...suggestions, ...plain, ...mixed]
}
