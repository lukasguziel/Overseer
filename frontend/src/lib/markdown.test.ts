import { describe, expect, it } from 'vitest'
import { parseInline, parseMarkdown } from './markdown'

describe('parseInline', () => {
  it('splits text, bold, code and links', () => {
    const spans = parseInline('Fixes **bold** and `code` via [gh](https://x.y/z).')
    expect(spans).toEqual([
      { kind: 'text', text: 'Fixes ' },
      { kind: 'bold', text: 'bold' },
      { kind: 'text', text: ' and ' },
      { kind: 'code', text: 'code' },
      { kind: 'text', text: ' via ' },
      { kind: 'link', text: 'gh', href: 'https://x.y/z' },
      { kind: 'text', text: '.' },
    ])
  })

  it('keeps non-http links as plain text', () => {
    expect(parseInline('[x](javascript:alert(1))')).toEqual([
      { kind: 'text', text: '[x](javascript:alert(1))' },
    ])
  })
})

describe('parseMarkdown', () => {
  it('parses headings, lists and paragraphs', () => {
    const blocks = parseMarkdown('## New\n- one\n- two\n\nA paragraph\nwrapped line')
    expect(blocks.map((b) => b.kind)).toEqual(['heading', 'list', 'para'])
    expect(blocks[0]).toMatchObject({ level: 2, spans: [{ kind: 'text', text: 'New' }] })
    expect((blocks[1] as any).items).toHaveLength(2)
    expect((blocks[2] as any).spans[0].text).toBe('A paragraph wrapped line')
  })

  it('keeps fenced code verbatim', () => {
    const blocks = parseMarkdown('```\n**not bold**\n```')
    expect(blocks).toEqual([{ kind: 'code', text: '**not bold**' }])
  })

  it('ends a list when a paragraph follows without a blank line', () => {
    const blocks = parseMarkdown('- a\ntail')
    expect(blocks.map((b) => b.kind)).toEqual(['list', 'para'])
  })

  it('parses empty input to no blocks', () => {
    expect(parseMarkdown('')).toEqual([])
  })
})
