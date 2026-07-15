import { describe, expect, it } from 'vitest'
import {
  gradientColorAt, hexToRgb01, multiGradientColors, resBucket, RES_BUCKETS,
  RES_TIERS, rgb01ToHex, statusDot,
} from './colors'
import type { GradientStop } from './colors'

describe('resBucket', () => {
  it('buckets by the longest edge into the 4 pill classes', () => {
    expect(resBucket(8192)).toBe('res-8k')
    expect(resBucket(6144)).toBe('res-4k')   // 6K counts as the 4K bucket
    expect(resBucket(4096)).toBe('res-4k')
    expect(resBucket(2048)).toBe('res-2k')
    expect(resBucket(1024)).toBe('res-sm')
    expect(resBucket(0)).toBe('res-sm')
  })

  it('derives its thresholds from RES_TIERS — they cannot drift', () => {
    const min = (label: string) => RES_TIERS.find((t) => t.label === label)!.min
    expect(RES_BUCKETS.find((b) => b.key === 'res-8k')!.min).toBe(min('8K+'))
    expect(RES_BUCKETS.find((b) => b.key === 'res-4k')!.min).toBe(min('4K'))
    expect(RES_BUCKETS.find((b) => b.key === 'res-2k')!.min).toBe(min('2K'))
  })
})

describe('statusDot', () => {
  it('only missing is a defect', () => {
    expect(statusDot(true)).toBe('var(--err)')
    expect(statusDot(false)).toBe('var(--apply)')
  })
})

const ENDS: GradientStop[] = [
  { t: 0, color: '#000000' }, { t: 1, color: '#ffffff' },
]

describe('hexToRgb01', () => {
  it('parses #rrggbb with and without the hash', () => {
    expect(hexToRgb01('#ff0000')).toEqual([1, 0, 0])
    expect(hexToRgb01('00ff00')).toEqual([0, 1, 0])
    expect(hexToRgb01('#0000FF')).toEqual([0, 0, 1])
  })

  it('falls back to mid grey on garbage', () => {
    expect(hexToRgb01('nope')).toEqual([0.5, 0.5, 0.5])
    expect(hexToRgb01('#fff')).toEqual([0.5, 0.5, 0.5])
  })
})

describe('rgb01ToHex', () => {
  it('round-trips through hexToRgb01', () => {
    expect(rgb01ToHex(hexToRgb01('#38bdf8'))).toBe('#38bdf8')
    expect(rgb01ToHex([0, 0, 0])).toBe('#000000')
    expect(rgb01ToHex([1, 1, 1])).toBe('#ffffff')
  })
})

describe('gradientColorAt', () => {
  it('lerps between the two surrounding stops', () => {
    expect(gradientColorAt(ENDS, 0.5)).toEqual([0.5, 0.5, 0.5])
  })

  it('an inner stop bends the blend', () => {
    const stops: GradientStop[] = [...ENDS, { t: 0.5, color: '#ff0000' }]
    expect(gradientColorAt(stops, 0.5)).toEqual([1, 0, 0])
    // halfway between the red stop and the white end
    expect(gradientColorAt(stops, 0.75)).toEqual([1, 0.5, 0.5])
  })

  it('clamps t outside the stop range to the nearest end', () => {
    expect(gradientColorAt(ENDS, -0.2)).toEqual([0, 0, 0])
    expect(gradientColorAt(ENDS, 1.3)).toEqual([1, 1, 1])
  })
})

describe('multiGradientColors', () => {
  it('puts the first layer on the start and the last on the end color', () => {
    const colors = multiGradientColors(3, ENDS)
    expect(colors[0]).toEqual([0, 0, 0])
    expect(colors[2]).toEqual([1, 1, 1])
  })

  it('spaces the layers evenly', () => {
    const colors = multiGradientColors(5, ENDS)
    expect(colors.map((c) => c[0])).toEqual([0, 0.25, 0.5, 0.75, 1])
  })

  it('gives a single layer the start color', () => {
    expect(multiGradientColors(1, ENDS)).toEqual([[0, 0, 0]])
  })

  it('returns an empty list for zero layers', () => {
    expect(multiGradientColors(0, ENDS)).toEqual([])
  })

  it('rounds to 3 decimals like the backend layer-color read', () => {
    const stops: GradientStop[] = [
      { t: 0, color: '#123456' }, { t: 0.37, color: '#a1b2c3' }, { t: 1, color: '#fedcba' },
    ]
    for (const c of multiGradientColors(7, stops).flat()) {
      expect(c).toBe(Math.round(c * 1000) / 1000)
    }
  })
})
