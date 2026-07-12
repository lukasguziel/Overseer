import type { ButtonHTMLAttributes, ReactNode } from 'react'
import './ActionButton.css'

// The action button of every listing / preview view (missing files, missing
// phong tags, duplicate material tags, unused materials, rename previews …).
//
// The tone is about CONSEQUENCE, not importance: what happens if the artist
// clicks. It only ever colours the hover — the resting state stays the same
// quiet grey everywhere, so a row of actions reads as a row, not a traffic light.
export type ActionTone =
  | 'neutral'   // nothing changes in the scene: select, browse, accept as-is, clear a log
  | 'go'        // builds or repairs: apply, relink, add tag, rewrite a path
  | 'danger'    // removes: delete, clear a dead reference

export default function ActionButton({ tone = 'neutral', className = '', children, ...rest }: {
  tone?: ActionTone
  children: ReactNode
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  const cls = ['act', tone !== 'neutral' ? tone : '', className]
    .filter(Boolean).join(' ')
  return <button className={cls} {...rest}>{children}</button>
}
