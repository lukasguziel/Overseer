import { describe, expect, it } from 'vitest'
import { buildHandGuideSteps, DETAIL_LIMIT, EXAMPLE_LIMIT } from './handGuide'
import type { HandGuideInput } from './handGuide'

const empty = (): HandGuideInput => ({
  report: null, naming: null, translation: null, structure: null,
  layerSuggestions: null, keptLayers: new Set(),
})

const renames = (n: number, rule = 'casing') =>
  Array.from({ length: n }, (_, i) => ({
    guid: i + 1, old: `wand_${i}`, new: `Wand_${i}`, rules: [rule],
  }))

describe('buildHandGuideSteps', () => {
  it('returns no steps for empty input', () => {
    expect(buildHandGuideSteps(empty())).toEqual([])
  })

  it('emits one card per finding for small groups', () => {
    const steps = buildHandGuideSteps({
      ...empty(),
      naming: { ok: true, count: 2, diff: renames(2) } as any,
    })
    expect(steps).toHaveLength(2)
    expect(steps[0].count).toBe(1)
    expect(steps[0].yesLabel).toBe('Rename')
  })

  it('collapses big groups into one batch card with capped examples', () => {
    const steps = buildHandGuideSteps({
      ...empty(),
      naming: { ok: true, count: 1000, diff: renames(1000) } as any,
    })
    expect(steps).toHaveLength(1)
    expect(steps[0].count).toBe(1000)
    expect(steps[0].examples).toHaveLength(EXAMPLE_LIMIT)
    expect(steps[0].action).toMatchObject({ kind: 'rename' })
    expect((steps[0].action as any).guids).toHaveLength(1000)
  })

  it('splits naming by rule and structure by target group', () => {
    const steps = buildHandGuideSteps({
      ...empty(),
      naming: {
        ok: true, count: 20,
        diff: [...renames(DETAIL_LIMIT + 1, 'casing'), ...renames(DETAIL_LIMIT + 1, 'numbering')],
      } as any,
      structure: {
        ok: true, count: 14,
        diff: Array.from({ length: 14 }, (_, i) => ({
          guid: 100 + i, name: `Obj${i}`, from: null, to: i % 2 ? 'Lights' : 'Cameras',
        })),
      } as any,
    })
    const naming = steps.filter((s) => s.area === 'naming')
    const structure = steps.filter((s) => s.area === 'structure')
    expect(naming).toHaveLength(2)
    expect(structure).toHaveLength(2)
    expect(structure[0].headline).toContain('Cameras')
    expect(structure[1].headline).toContain('Lights')
  })

  it('turns layerless objects into suggestion batches plus one accept-as-is card', () => {
    const nodes = Array.from({ length: 10 }, (_, i) => ({
      guid: i, name: `N${i}`, layer: '',
    }))
    const steps = buildHandGuideSteps({
      ...empty(),
      report: { nodes, materials: { unused: [] } } as any,
      layerSuggestions: {
        ok: true, count: 8,
        diff: nodes.slice(0, 8).map((n) => ({ guid: n.guid, name: n.name, layer: 'Deko' })),
      } as any,
    })
    const assign = steps.find((s) => s.action.kind === 'assign-layer')
    const keep = steps.find((s) => s.action.kind === 'keep-layerless')
    expect(assign?.count).toBe(8)
    expect((assign?.action as any).layer).toBe('Deko')
    expect(keep?.count).toBe(2)
  })

  it('kept names are excluded from the layer worklist', () => {
    const nodes = [{ guid: 1, name: 'KeepMe', layer: '' }, { guid: 2, name: 'Todo', layer: '' }]
    const steps = buildHandGuideSteps({
      ...empty(),
      report: { nodes, materials: { unused: [] } } as any,
      keptLayers: new Set(['KeepMe']),
    })
    const keep = steps.find((s) => s.action.kind === 'keep-layerless')
    expect(keep?.count).toBe(1)
    expect((keep?.action as any).names).toEqual(['Todo'])
  })

  it('unused materials: per-item when few, one sweep when many', () => {
    const few = buildHandGuideSteps({
      ...empty(),
      report: { nodes: [], materials: { unused: ['A', 'B'] } } as any,
    })
    expect(few.filter((s) => s.area === 'materials')).toHaveLength(2)

    const many = buildHandGuideSteps({
      ...empty(),
      report: {
        nodes: [],
        materials: { unused: Array.from({ length: 30 }, (_, i) => `M${i}`) },
      } as any,
    })
    const mat = many.filter((s) => s.area === 'materials')
    expect(mat).toHaveLength(1)
    expect(mat[0].action).toMatchObject({ kind: 'delete-materials', count: 30 })
  })
})
