import { describe, expect, it } from 'vitest'
import { humanBytes, humanNum } from './format'

describe('humanNum', () => {
  it('passes small numbers through', () => {
    expect(humanNum(0)).toBe('0')
    expect(humanNum(999)).toBe('999')
  })

  it('abbreviates thousands, millions, billions', () => {
    expect(humanNum(1500)).toBe('1.5K')
    expect(humanNum(25000)).toBe('25K')
    expect(humanNum(1_500_000)).toBe('1.5M')
    expect(humanNum(2_000_000_000)).toBe('2.0B')
  })

  it('treats null/undefined as zero', () => {
    expect(humanNum(null)).toBe('0')
    expect(humanNum(undefined)).toBe('0')
  })
})

describe('humanBytes', () => {
  it('shows a dash for empty values', () => {
    expect(humanBytes(0)).toBe('—')
    expect(humanBytes(null)).toBe('—')
    expect(humanBytes(undefined)).toBe('—')
  })

  it('scales through the unit ladder', () => {
    expect(humanBytes(512)).toBe('512 B')
    expect(humanBytes(2048)).toBe('2.0 KB')
    expect(humanBytes(5 * 1024 * 1024)).toBe('5.0 MB')
    expect(humanBytes(3 * 1024 ** 3)).toBe('3.0 GB')
  })

  it('drops decimals at three digits', () => {
    expect(humanBytes(150 * 1024)).toBe('150 KB')
  })
})
