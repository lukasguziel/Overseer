import { describe, expect, it } from 'vitest'
import { planWarning } from './TranslateTab'

describe('planWarning', () => {
  it('surfaces a partial online-translate warning carried on the plan', () => {
    // setup: a Google plan that fell back to the cache mid-run
    const plan = { count: 3, warning: 'Google translation was incomplete (timeout).' }

    // do it
    const w = planWarning(plan)

    // postcondition: the caution text is returned for the tab to render
    expect(w).toBe('Google translation was incomplete (timeout).')
  })

  it('returns null for a clean plan, a blank warning, or no plan', () => {
    expect(planWarning({ count: 3 })).toBeNull()
    expect(planWarning({ count: 3, warning: '   ' })).toBeNull()
    expect(planWarning(null)).toBeNull()
    expect(planWarning(undefined)).toBeNull()
  })
})
