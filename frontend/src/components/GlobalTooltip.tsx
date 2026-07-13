import { useEffect, useLayoutEffect, useRef, useState, type ReactElement } from 'react'

// One tooltip to style them all. Instead of each `title=""` falling back to the
// OS's ugly native tooltip, a single document-level listener intercepts any
// element carrying a title: it strips the attribute (so the native bubble never
// fires), remembers it, and renders one nicely styled dark bubble near the
// element — restoring the title when the pointer leaves so keyboard/native
// access still works. Multi-line titles (\n) keep their line breaks.
interface Anchor { rect: DOMRect; text: string }

const SHOW_DELAY = 110

export default function GlobalTooltip() {
  const [anchor, setAnchor] = useState<Anchor | null>(null)
  const [coords, setCoords] = useState<{ left: number; top: number; place: 'top' | 'bottom'; arrow: number } | null>(null)
  const bubbleRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    let current: HTMLElement | null = null
    let timer: ReturnType<typeof setTimeout> | null = null

    const stash = (el: HTMLElement): string | null => {
      const text = el.getAttribute('title')
      if (!text || !text.trim()) return null
      el.setAttribute('data-tip', text)
      el.removeAttribute('title')      // suppress the native OS tooltip
      return text
    }
    const restore = () => {
      if (current) {
        const kept = current.getAttribute('data-tip')
        if (kept != null) {
          current.setAttribute('title', kept)
          current.removeAttribute('data-tip')
        }
        current = null
      }
    }
    const clearTimer = () => { if (timer) { clearTimeout(timer); timer = null } }

    const show = (el: HTMLElement) => {
      const text = stash(el)
      if (text == null) return
      current = el
      timer = setTimeout(() => {
        setCoords(null)
        setAnchor({ rect: el.getBoundingClientRect(), text })
      }, SHOW_DELAY)
    }
    const hide = () => {
      clearTimer()
      restore()
      setAnchor(null)
      setCoords(null)
    }

    const onOver = (e: Event) => {
      const target = e.target as HTMLElement | null
      const el = target?.closest?.('[title]') as HTMLElement | null
      if (!el || el === current) return
      if (current) hide()
      show(el)
    }
    const onOut = (e: Event) => {
      if (!current) return
      const related = (e as MouseEvent).relatedTarget as Node | null
      if (related && current.contains(related)) return
      hide()
    }

    document.addEventListener('mouseover', onOver, true)
    document.addEventListener('mouseout', onOut, true)
    document.addEventListener('focusin', onOver, true)
    document.addEventListener('focusout', onOut, true)
    window.addEventListener('scroll', hide, true)
    document.addEventListener('mousedown', hide, true)
    window.addEventListener('blur', hide)
    return () => {
      document.removeEventListener('mouseover', onOver, true)
      document.removeEventListener('mouseout', onOut, true)
      document.removeEventListener('focusin', onOver, true)
      document.removeEventListener('focusout', onOut, true)
      window.removeEventListener('scroll', hide, true)
      document.removeEventListener('mousedown', hide, true)
      window.removeEventListener('blur', hide)
      hide()
    }
  }, [])

  // Measure the rendered bubble, then place it above the anchor (flip below if
  // it would clip the top) and clamp it inside the viewport.
  useLayoutEffect(() => {
    if (!anchor || !bubbleRef.current) return
    const b = bubbleRef.current.getBoundingClientRect()
    const r = anchor.rect
    const gap = 8
    let place: 'top' | 'bottom' = 'top'
    let top = r.top - gap - b.height
    if (top < 6) { place = 'bottom'; top = r.bottom + gap }
    const centerX = r.left + r.width / 2
    let left = centerX - b.width / 2
    left = Math.max(6, Math.min(left, window.innerWidth - b.width - 6))
    // Keep the little arrow pointing at the anchor even when the bubble was
    // clamped to the viewport edge.
    const arrow = Math.max(10, Math.min(centerX - left, b.width - 10))
    setCoords({ left, top, place, arrow })
  }, [anchor])

  if (!anchor) return null
  return (
    <div ref={bubbleRef}
      className={'gtip' + (coords ? ' gtip-show gtip-' + coords.place : '')}
      style={coords
        ? { left: coords.left, top: coords.top, ['--gtip-arrow' as string]: coords.arrow + 'px' }
        : { left: -9999, top: -9999 }}
      role="tooltip">
      {renderTip(anchor.text)}
    </div>
  )
}

// Tooltip copy supports a tiny line-based markup so long titles read as a
// structured card instead of a wall of text:
//   "# Heading"      → bold headline (first line only)
//   "- item"/"• item" → bullet list
//   anything else     → paragraph; plain single-line titles render unchanged.
function renderTip(text: string) {
  const lines = text.split('\n')
  if (lines.length === 1 && !lines[0].startsWith('# ')) return text
  const out: ReactElement[] = []
  let bullets: string[] = []
  const flush = () => {
    if (bullets.length) {
      out.push(<ul className="gtip-list" key={out.length}>{bullets.map((b, i) => <li key={i}>{b}</li>)}</ul>)
      bullets = []
    }
  }
  lines.forEach((line, i) => {
    const l = line.trim()
    if (!l) { flush(); return }
    if (i === 0 && l.startsWith('# ')) { out.push(<div className="gtip-title" key="t">{l.slice(2)}</div>); return }
    if (l.startsWith('- ') || l.startsWith('• ')) { bullets.push(l.slice(2)); return }
    flush()
    out.push(<p className="gtip-p" key={out.length}>{l}</p>)
  })
  flush()
  return out
}
