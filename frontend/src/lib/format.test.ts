import { describe, expect, it } from 'vitest'
import { humanBytes, humanNum, plural, resTag } from './format'

describe('plural', () => {
  it('keeps the singular at exactly one', () => {
    expect(plural(1, 'file')).toBe('1 file')
  })

  it('adds an s everywhere else, including zero', () => {
    expect(plural(0, 'file')).toBe('0 files')
    expect(plural(2, 'file')).toBe('2 files')
  })

  it('the s lands after the full word group', () => {
    expect(plural(3, 'unused material')).toBe('3 unused materials')
    expect(plural(1, 'missing file name')).toBe('1 missing file name')
  })
})

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

  it('promotes to the next unit when the rounded value reaches 1000', () => {
    expect(humanNum(999_950)).toBe('1.0M')
    expect(humanNum(999_999_999)).toBe('1.0B')
  })

  it('treats null/undefined as zero', () => {
    expect(humanNum(null)).toBe('0')
    expect(humanNum(undefined)).toBe('0')
  })
})

describe('resTag', () => {
  it('labels the exact K count, not a bucket', () => {
    expect(resTag(8192)).toBe('8K')
    expect(resTag(6144)).toBe('6K')   // 6144 is 6K — never "4K"
    expect(resTag(12288)).toBe('12K')
    expect(resTag(4096)).toBe('4K')
    expect(resTag(2048)).toBe('2K')
    expect(resTag(1024)).toBe('1K')
  })

  it('shows raw pixels below 1K', () => {
    expect(resTag(512)).toBe('512px')
    expect(resTag(0)).toBe('')
  })

  it('rounds half-to-even like the backend resolution_tag', () => {
    expect(resTag(2560)).toBe('2K')   // Python round(2.5) == 2
    expect(resTag(3584)).toBe('4K')   // Python round(3.5) == 4
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

  it('never prints "1024 B" — it rounds up into the next unit', () => {
    expect(humanBytes(1023.6)).toBe('1.0 KB')
    expect(humanBytes(1023)).toBe('1023 B')
  })
})
