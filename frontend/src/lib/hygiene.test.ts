import { describe, expect, it } from 'vitest'
import { computeHygiene, detectCasing, isDefaultName } from './hygiene'
import type { SceneNode } from '../types'

const node = (name: string, i: number): SceneNode => ({
  guid: i, name, type: 'Polygon', category: 'mesh', depth: 1,
  children: 0, polygons: 10, points: 10,
})

describe('detectCasing', () => {
  it('classifies the producible styles', () => {
    expect(detectCasing('KeyLight')).toBe('PascalCase')
    expect(detectCasing('keyLight')).toBe('camelCase')
    expect(detectCasing('key_light')).toBe('lower_snake')
    expect(detectCasing('KEY_LIGHT')).toBe('UPPER_SNAKE')
    expect(detectCasing('key-light')).toBe('kebab')
    expect(detectCasing('Chair01')).toBe('Capitalized')
    expect(detectCasing('chair')).toBe('lower')
    expect(detectCasing('My Chair')).toBe('spaced')
  })
})

describe('isDefaultName', () => {
  it('flags the bare type word, a numbered copy and a "copy" suffix', () => {
    expect(isDefaultName('Camera', 'Camera')).toBe(true)
    expect(isDefaultName('Camera.1', 'Camera')).toBe(true)
    expect(isDefaultName('Camera copy', 'Camera')).toBe(true)
    expect(isDefaultName('Cube', 'Polygon')).toBe(true)
  })

  it('keeps type-prefixed descriptive names', () => {
    expect(isDefaultName('Camera_Main', 'Camera')).toBe(false)
    expect(isDefaultName('Light_Key', 'Light')).toBe(false)
    expect(isDefaultName('SplineProfile', 'Spline')).toBe(false)
  })
})

describe('computeHygiene naming score (decision-based)', () => {
  it('clean consistent scene scores 100', () => {
    const h = computeHygiene([node('KeyLight', 1), node('BackWall', 2)], 20,
      { casing: 'PascalCase' })
    expect(h.namingScore).toBe(100)
    expect(h.namingTodos).toBe(0)
  })

  it('off-style casing counts as an open todo', () => {
    const h = computeHygiene([node('KeyLight', 1), node('back_wall', 2)], 20,
      { casing: 'PascalCase' })
    expect(h.namingTodos).toBe(1)
    expect(h.namingScore).toBe(50)
  })

  it('accepting a name as-is clears ALL its todos — 100 is reachable', () => {
    const nodes = [node('Cube', 1), node('back_wall', 2), node('back_wall', 3)]
    const before = computeHygiene(nodes, 30, { casing: 'PascalCase' })
    expect(before.namingScore).toBe(0)
    const after = computeHygiene(nodes, 30,
      { casing: 'PascalCase', kept: new Set(['Cube', 'back_wall']) })
    expect(after.namingScore).toBe(100)
    expect(after.defaults).toHaveLength(0)
    expect(after.dupes).toHaveLength(0)
  })

  it('survives names that collide with Object.prototype members', () => {
    const nodes = [node('__proto__', 1), node('constructor', 2), node('constructor', 3)]
    const h = computeHygiene(nodes, 30, { casing: 'PascalCase' })
    expect(h.dupes).toEqual([{ name: 'constructor', count: 2, guid: 2 }])
    expect(h.dupeGuids).toEqual([2, 3])
  })

  it('duplicates only clash among siblings, not across containers', () => {
    // Walls > Wall, Wall  +  Backup > Wall : only the two siblings collide.
    const group = (name: string, i: number, depth: number): SceneNode => ({
      guid: i, name, type: 'Null', category: 'null', depth,
      children: 2, polygons: 0, points: 0,
    })
    const at = (name: string, i: number, depth: number): SceneNode =>
      ({ ...node(name, i), depth })
    const nodes = [
      group('Walls', 1, 0), at('Wall', 2, 1), at('Wall', 3, 1),
      group('Backup', 4, 0), at('Wall', 5, 1),
    ]
    const h = computeHygiene(nodes, 30, { casing: 'PascalCase' })
    expect(h.dupes).toEqual([{ name: 'Wall', count: 2, guid: 2 }])
    expect(h.dupeGuids).toEqual([2, 3])
  })

  it('without a chosen casing the best-fitting style wins', () => {
    const h = computeHygiene(
      [node('key_light', 1), node('back_wall', 2), node('Odd', 3)], 30, {})
    expect(h.namingTodos).toBe(1)   // lower_snake fits 2/3; 'Odd' stays a todo
    expect(h.casingScore).toBe(67)
  })
})
