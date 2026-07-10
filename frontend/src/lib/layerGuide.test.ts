import { describe, expect, it } from 'vitest'
import { buildLayerGuideSteps } from './layerGuide'
import type { LayerMismatch, SceneNode } from '../types'

const node = (name: string, guid: number): SceneNode => ({
  guid, name, type: 'Polygon', category: 'mesh', depth: 1,
  children: 0, polygons: 10, points: 10,
})

const mismatch = (name: string, guid: number): LayerMismatch => ({
  guid, name, path: `/${name}`, parent: 'Room',
  parent_layer: 'A', child_layer: 'B',
})

describe('buildLayerGuideSteps', () => {
  it('orders suggestions, then plain no-layer, then mismatches', () => {
    // setup
    const noLayer = [node('Chair', 1), node('Table', 2)]
    const suggestions = new Map<number, string>([[1, 'Furniture']])
    const mismatches = [mismatch('Lamp', 3)]

    // do it
    const steps = buildLayerGuideSteps(noLayer, suggestions, mismatches)

    // postcondition
    expect(steps.map((s) => s.kind)).toEqual(['suggestion', 'no-layer', 'mismatch'])
    expect(steps[0]).toMatchObject({ guid: 1, name: 'Chair', layer: 'Furniture' })
    expect(steps[1]).toMatchObject({ guid: 2, name: 'Table' })
    expect(steps[2]).toMatchObject({ guid: 3, name: 'Lamp', parentLayer: 'A', childLayer: 'B' })
  })

  it('is empty when there is nothing to decide', () => {
    // do it
    const steps = buildLayerGuideSteps([], new Map(), [])

    // postcondition
    expect(steps).toEqual([])
  })
})
