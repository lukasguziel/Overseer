import { describe, expect, it } from 'vitest'
import type { FilesScan } from '../types'
import { acceptBase } from './FilesTab'

const scan = (over: Partial<FilesScan & { accepted_all?: string[] }>): FilesScan & { accepted_all?: string[] } => ({
  ok: true, doc_path: '/proj', entries: [],
  summary: { total: 0, by_kind: {}, missing_count: 0, absolute_count: 0, relocatable_count: 0, total_bytes: 0 },
  ...over,
})

describe('acceptBase', () => {
  it('merges onto the FULL config set, not this scene’s missing-only intersection', () => {
    // setup: another scene accepted b.abc, only a.abc is missing in THIS scan
    const s = scan({ accepted: ['a.abc'], accepted_all: ['a.abc', 'b.abc'] })

    // do it
    const base = acceptBase(s)

    // postcondition: accepting a new path keeps the other scene's accept
    expect(base).toEqual(['a.abc', 'b.abc'])
    expect([...base, 'c.abc']).toContain('b.abc')
  })

  it('falls back to the scene-scoped accepted when accepted_all is absent', () => {
    expect(acceptBase(scan({ accepted: ['a.abc'] }))).toEqual(['a.abc'])
  })

  it('returns an empty base for a null scan', () => {
    expect(acceptBase(null)).toEqual([])
  })
})
