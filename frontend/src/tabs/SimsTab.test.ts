import { describe, it, expect } from 'vitest'
import { simRowKey, simTargets } from './SimsTab'

describe('simRowKey', () => {
  it('disambiguates two carriers that share (guid, kind) by tag index', () => {
    // setup: one object with two Dynamics Body tags -> same guid+kind, different index
    const a = { guid: 7, kind: 'dynamics', index: 0 }
    const b = { guid: 7, kind: 'dynamics', index: 1 }

    // postcondition: the second row is reachable with its own stable key
    expect(simRowKey(a)).not.toBe(simRowKey(b))
    expect(simRowKey(a)).toBe('7:dynamics:0')
  })
})

describe('simTargets', () => {
  it('flattens a mixed-kind batch into one target list for a single request', () => {
    // setup: a batch spanning two kinds, one kind carried by two tags on one object
    const hits = [
      { guid: 7, kind: 'dynamics', index: 0 },
      { guid: 7, kind: 'dynamics', index: 1 },
      { guid: 9, kind: 'cloth', index: 2 },
    ]

    // do it
    const targets = simTargets(hits)

    // postcondition: every guid+kind+index survives so one call can carry the whole batch
    expect(targets).toEqual([
      { guid: 7, kind: 'dynamics', index: 0 },
      { guid: 7, kind: 'dynamics', index: 1 },
      { guid: 9, kind: 'cloth', index: 2 },
    ])
  })
})
