import { describe, it, expect } from 'vitest'
import { ms1 } from './GeneratorsTab'

describe('ms1', () => {
  it('renders a dash when the value is missing (empty scan has no scene_ms)', () => {
    // do it + postcondition: an undefined/null value must not become "NaN ms"
    expect(ms1(undefined)).toBe('—')
    expect(ms1(null)).toBe('—')
  })

  it('shows one decimal below 10 ms and whole ms above', () => {
    expect(ms1(0)).toBe('0.0 ms')
    expect(ms1(4.2)).toBe('4.2 ms')
    expect(ms1(42.6)).toBe('43 ms')
  })
})
