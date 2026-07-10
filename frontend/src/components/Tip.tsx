import type { ReactNode } from 'react'

// Shared hover tooltip. Wraps any control or header label and shows a small
// positioned bubble on hover/focus (CSS-only, no dependency). `text` is German
// UI copy. A native `title` mirror keeps it accessible and works before the
// CSS bubble paints.
export default function Tip({ text, children, className }: {
  text: string
  children: ReactNode
  className?: string
}) {
  return (
    <span className={'tip' + (className ? ' ' + className : '')} tabIndex={0} title={text}>
      {children}
      <span className="tip-bubble" role="tooltip">{text}</span>
    </span>
  )
}
