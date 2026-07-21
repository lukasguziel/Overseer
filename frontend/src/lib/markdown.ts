// Tiny renderer-agnostic parser for the markdown subset our GitHub release
// notes actually use: #-headings, -/* lists, paragraphs, fenced code blocks,
// and inline `code` / **bold** / [links](https://…). Anything fancier renders
// as plain text — release notes must degrade, never break the banner.
export type MdInline =
  | { kind: 'text'; text: string }
  | { kind: 'bold'; text: string }
  | { kind: 'code'; text: string }
  | { kind: 'link'; text: string; href: string }

export type MdBlock =
  | { kind: 'heading'; level: number; spans: MdInline[] }
  | { kind: 'para'; spans: MdInline[] }
  | { kind: 'list'; items: MdInline[][] }
  | { kind: 'code'; text: string }

const INLINE = /(`[^`]+`)|(\*\*[^*]+\*\*)|(\[([^\]]+)\]\((https?:\/\/[^)\s]+)\))/g

export function parseInline(src: string): MdInline[] {
  const spans: MdInline[] = []
  let last = 0
  for (const m of src.matchAll(INLINE)) {
    const at = m.index ?? 0
    if (at > last) spans.push({ kind: 'text', text: src.slice(last, at) })
    if (m[1]) spans.push({ kind: 'code', text: m[1].slice(1, -1) })
    else if (m[2]) spans.push({ kind: 'bold', text: m[2].slice(2, -2) })
    else spans.push({ kind: 'link', text: m[4], href: m[5] })
    last = at + m[0].length
  }
  if (last < src.length) spans.push({ kind: 'text', text: src.slice(last) })
  return spans
}

export function parseMarkdown(src: string): MdBlock[] {
  const blocks: MdBlock[] = []
  let para: string[] = []
  let list: MdInline[][] | null = null
  let code: string[] | null = null
  const flush = () => {
    if (para.length) { blocks.push({ kind: 'para', spans: parseInline(para.join(' ')) }); para = [] }
    if (list) { blocks.push({ kind: 'list', items: list }); list = null }
  }
  for (const raw of (src || '').replace(/\r\n?/g, '\n').split('\n')) {
    if (code) {
      if (/^```/.test(raw.trim())) { blocks.push({ kind: 'code', text: code.join('\n') }); code = null }
      else code.push(raw)
      continue
    }
    const line = raw.trim()
    if (/^```/.test(line)) { flush(); code = []; continue }
    if (!line) { flush(); continue }
    const heading = /^(#{1,6})\s+(.*)$/.exec(line)
    if (heading) { flush(); blocks.push({ kind: 'heading', level: heading[1].length, spans: parseInline(heading[2]) }); continue }
    const item = /^[-*]\s+(.*)$/.exec(line)
    if (item) {
      if (para.length) flush()
      if (!list) list = []
      list.push(parseInline(item[1]))
      continue
    }
    if (list) flush()
    para.push(line)
  }
  if (code) blocks.push({ kind: 'code', text: code.join('\n') })
  flush()
  return blocks
}
