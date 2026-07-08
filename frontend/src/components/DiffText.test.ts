import { describe, expect, it } from 'vitest'
import { diffParts } from './DiffText'

describe('diffParts', () => {
  it('highlights a casing change in the middle', () => {
    expect(diffParts('kitchen_cabinets', 'KitchenCabinets')).toEqual({
      prefix: '', oldMid: 'kitchen_c', newMid: 'KitchenC', suffix: 'abinets',
    })
  })

  it('highlights a numbering suffix change', () => {
    expect(diffParts('Pillow_2', 'Pillow_02')).toEqual({
      prefix: 'Pillow_', oldMid: '', newMid: '0', suffix: '2',
    })
  })

  it('handles a pure append', () => {
    expect(diffParts('Chair', 'Chair01')).toEqual({
      prefix: 'Chair', oldMid: '', newMid: '01', suffix: '',
    })
  })

  it('handles identical strings', () => {
    expect(diffParts('Same', 'Same')).toEqual({
      prefix: 'Same', oldMid: '', newMid: '', suffix: '',
    })
  })

  it('handles a full replacement', () => {
    const d = diffParts('Stuhl', 'Chair')
    expect(d.prefix).toBe('')
    expect(d.oldMid).toBe('Stuhl')
    expect(d.newMid).toBe('Chair')
  })
})
