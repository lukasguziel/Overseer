import { parseMarkdown } from '../lib/markdown'
import type { MdInline } from '../lib/markdown'
import './Markdown.css'

// Renders untrusted markdown (GitHub release notes) through the strict
// subset parser in lib/markdown — real elements only, never raw HTML.
function Spans({ spans }: { spans: MdInline[] }) {
  return (
    <>
      {spans.map((s, i) => {
        if (s.kind === 'bold') return <strong key={i}>{s.text}</strong>
        if (s.kind === 'code') return <code key={i}>{s.text}</code>
        if (s.kind === 'link')
          return <a key={i} href={s.href} target="_blank" rel="noreferrer">{s.text}</a>
        return <span key={i}>{s.text}</span>
      })}
    </>
  )
}

export default function Markdown({ source }: { source: string }) {
  return (
    <div className="md">
      {parseMarkdown(source).map((b, i) => {
        if (b.kind === 'heading') return <p key={i} className="md-h"><Spans spans={b.spans} /></p>
        if (b.kind === 'list')
          return (
            <ul key={i}>
              {b.items.map((item, j) => <li key={j}><Spans spans={item} /></li>)}
            </ul>
          )
        if (b.kind === 'code') return <pre key={i}>{b.text}</pre>
        return <p key={i}><Spans spans={b.spans} /></p>
      })}
    </div>
  )
}
