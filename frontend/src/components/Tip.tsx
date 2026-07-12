import type { ReactNode } from 'react'

// Shared hover tooltip. Wraps any control or header label and exposes the copy
// as a `title` — the app-wide <GlobalTooltip> intercepts every title on the
// page and renders one nicely styled dark bubble on hover/focus, so this stays
// a thin, semantic wrapper.
export default function Tip({ text, children, className }: {
  text: string
  children: ReactNode
  className?: string
}) {
  return (
    <span className={'tip' + (className ? ' ' + className : '')} tabIndex={0} title={text}>
      {children}
    </span>
  )
}
