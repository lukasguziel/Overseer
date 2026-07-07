import { useState } from 'react'
import type { FocusFn } from './Treemap'

export interface CleanupItem {
  guid: number
  name: string
  meta?: string
}

export interface CleanupBucket {
  key: string
  label: string
  items: CleanupItem[]
}

// Cleanup-Accordion: kompakte Liste von Problem-Gruppen, eine offen.
export default function Cleanup({ buckets, onFocus }: {
  buckets: CleanupBucket[]
  onFocus?: FocusFn
}) {
  const [open, setOpen] = useState<string | null>(
    () => buckets.find((b) => b.items.length)?.key || null)
  return (
    <div className="cleanup">
      {buckets.map((b) => {
        const isOpen = open === b.key
        return (
          <div className={'cl-bucket' + (isOpen ? ' open' : '')} key={b.key}>
            <button className="cl-head" onClick={() => setOpen(isOpen ? null : b.key)}>
              <span className="cl-caret">{isOpen ? '▾' : '▸'}</span>
              <span className="cl-label">{b.label}</span>
              <span className={'cl-count' + (b.items.length ? ' warn' : '')}>{b.items.length}</span>
            </button>
            {isOpen && (b.items.length
              ? <div className="cl-items">
                  {b.items.slice(0, 40).map((it, i) => (
                    <button key={i} className="cl-item" onClick={() => onFocus?.(it.guid, it.name)}
                      title="Select & frame in viewport">
                      <span className="fl-name">{it.name}</span>
                      {it.meta && <span className="fl-meta">{it.meta}</span>}
                    </button>
                  ))}
                  {b.items.length > 40 && <div className="fl-more">+{b.items.length - 40} more</div>}
                </div>
              : <div className="cl-clean">Clean 🎉</div>)}
          </div>
        )
      })}
    </div>
  )
}
