import { describe, expect, it } from 'vitest'
import type { SceneNode } from '../types'
import { matchesSearch } from './AssetsTab'

const node = (over: Partial<SceneNode>): SceneNode => ({
  guid: 1, name: 'Cube', type: 'Polygon Object', category: 'mesh',
  depth: 0, children: 0, polygons: 12, points: 8, ...over,
})

describe('matchesSearch', () => {
  it('matches on name, raw type and layer', () => {
    expect(matchesSearch(node({ name: 'Wheel' }), 'whe')).toBe(true)
    expect(matchesSearch(node({ type: 'Polygon Object' }), 'polygon')).toBe(true)
    expect(matchesSearch(node({ layer: 'Set' }), 'set')).toBe(true)
  })

  it('matches the shown type abbreviation, not just the raw label', () => {
    const sds = node({ type: 'Subdivision Surface' })
    expect(matchesSearch(sds, 'sds')).toBe(true)          // the abbreviation the Type column shows
    expect(matchesSearch(sds, 'subdivision')).toBe(true)  // the raw label still matches too
  })

  it('returns everything for an empty query and misses on no match', () => {
    expect(matchesSearch(node({}), '')).toBe(true)
    expect(matchesSearch(node({ name: 'Cube', type: 'Polygon Object' }), 'zzz')).toBe(false)
  })
})
