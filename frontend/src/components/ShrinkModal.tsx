import { useEffect, useState } from 'react'
import ActionButton from './ActionButton'

// Pick the size for ONE texture. The row button only carries the shrink icon —
// the number belongs here, where the artist can see what each choice actually
// produces (a percentage means nothing; "8192 → 4096" means everything).
const SIZES = [25, 50, 75] as const

const dim = (px: number, percent: number) => Math.max(1, Math.round(px * percent / 100))

export default function ShrinkModal({ file, width, height, busy, onConfirm, onCancel }: {
  file: string
  width: number
  height: number
  busy?: boolean
  onConfirm: (percent: number) => void
  onCancel: () => void
}) {
  const [percent, setPercent] = useState<number>(50)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onCancel() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onCancel])

  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-box" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <h3 className="confirm-title">Shrink texture</h3>
        <p className="confirm-msg">
          <b>{file}</b> — currently {width}×{height}. A downsized <b>copy</b> is
          written next to the original and the material is relinked to it. The
          original file is never touched; the relink is one undo step.
        </p>
        <div className="shrink-sizes">
          {SIZES.map((p) => (
            <button key={p} type="button"
              className={'shrink-size' + (percent === p ? ' on' : '')}
              onClick={() => setPercent(p)}>
              <span className="shrink-pct">{p}%</span>
              <span className="shrink-dims">{dim(width, p)}×{dim(height, p)}</span>
            </button>
          ))}
        </div>
        <div className="confirm-actions">
          <button className="ghost" onClick={onCancel}>Cancel</button>
          <ActionButton tone="go" autoFocus disabled={busy}
            onClick={() => onConfirm(percent)}>
            Shrink to {dim(width, percent)}×{dim(height, percent)}
          </ActionButton>
        </div>
      </div>
    </div>
  )
}
