import { describe, expect, it } from 'vitest'
import { gradientColors, hexToRgb01 } from './colors'

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

describe('gradientColors', () => {
  it('puts the first layer on the start and the last on the end color', () => {
    const stops = gradientColors(3, '#000000', '#ffffff')
    expect(stops[0]).toEqual([0, 0, 0])
    expect(stops[2]).toEqual([1, 1, 1])
  })

  it('spaces the stops evenly', () => {
    const stops = gradientColors(5, '#000000', '#ffffff')
    expect(stops.map((c) => c[0])).toEqual([0, 0.25, 0.5, 0.75, 1])
  })

  it('gives a single layer the start color', () => {
    expect(gradientColors(1, '#ff0000', '#0000ff')).toEqual([[1, 0, 0]])
  })

  it('returns an empty list for zero layers', () => {
    expect(gradientColors(0, '#ff0000', '#0000ff')).toEqual([])
  })

  it('rounds to 3 decimals like the backend layer-color read', () => {
    for (const c of gradientColors(7, '#123456', '#fedcba').flat()) {
      expect(c).toBe(Math.round(c * 1000) / 1000)
    }
  })
})
