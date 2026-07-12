import { useEffect, useState } from 'react'
import ActionButton from './ActionButton'
import { humanBytes } from '../lib/format'

// Pick the size for ONE texture. The row button only carries the shrink icon —
// the numbers belong here, where the artist can see what each choice actually
// produces. A percentage means nothing on its own: 50% of an 8K map is a 4K
// map, and it is a QUARTER of the memory. So every option states the three
// things that matter — the resolution tier, the pixel size, and the VRAM.
const SIZES = [25, 50, 75] as const

const dim = (px: number, percent: number) => Math.max(1, Math.round(px * percent / 100))

// Same tiers as the texture list, so "8K" means the same thing everywhere.
function tier(longest: number): string {
  if (longest >= 8192) return '8K'
  if (longest >= 4096) return '4K'
  if (longest >= 2048) return '2K'
  if (longest >= 1024) return '1K'
  return '< 1K'
}

// Uncompressed memory: w × h × 4 bytes + 1/3 for the mip chain — the same
// formula the backend uses (core/textures.vram_bytes).
const vram = (w: number, h: number) => Math.round(w * h * 4 * (4 / 3))

// The copy's file name is predictable (stem_<percent>.ext) — show it, so
// nobody has to guess what will appear next to the original.
function copyName(file: string, percent: number): string {
  const dot = file.lastIndexOf('.')
  return dot < 0 ? `${file}_${percent}` : `${file.slice(0, dot)}_${percent}${file.slice(dot)}`
}

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

  const fromTier = tier(Math.max(width, height))
  const nw = dim(width, percent)
  const nh = dim(height, percent)
  const before = vram(width, height)
  const after = vram(nw, nh)
  const saved = before > 0 ? Math.round((1 - after / before) * 100) : 0

  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-box" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <h3 className="confirm-title">Shrink texture</h3>
        <p className="confirm-msg">
          <b>{file}</b> — currently <b>{fromTier}</b> ({width}×{height},{' '}
          {humanBytes(before)} VRAM). A downsized <b>copy</b> is written next to
          the original and the material is relinked to it. The original file is
          never touched; the relink is one undo step.
        </p>
        <div className="shrink-sizes">
          {SIZES.map((p) => {
            const w = dim(width, p)
            const h = dim(height, p)
            return (
              <button key={p} type="button"
                className={'shrink-size' + (percent === p ? ' on' : '')}
                title={`${fromTier} → ${tier(Math.max(w, h))} · ${humanBytes(vram(w, h))} VRAM`}
                onClick={() => setPercent(p)}>
                <span className="shrink-tier">{fromTier} → {tier(Math.max(w, h))}</span>
                <span className="shrink-dims">{w}×{h}</span>
                <span className="shrink-pct">{p}% · {humanBytes(vram(w, h))}</span>
              </button>
            )
          })}
        </div>
        <p className="hint-sm shrink-note">
          Writes <code>{copyName(file, percent)}</code> next to the original —{' '}
          {humanBytes(before)} → <b>{humanBytes(after)}</b> VRAM
          {saved > 0 && <> (<b>−{saved}%</b>)</>}.
        </p>
        <div className="confirm-actions">
          <button className="ghost" onClick={onCancel}>Cancel</button>
          <ActionButton autoFocus disabled={busy}
            onClick={() => onConfirm(percent)}>
            Shrink to {tier(Math.max(nw, nh))} ({nw}×{nh})
          </ActionButton>
        </div>
      </div>
    </div>
  )
}
