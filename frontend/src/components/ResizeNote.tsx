import { humanBytes } from '../lib/format'

// What a shrink actually bought, shown instead of asserted.
//
// The trap this exists for: "50%" sounds like half. It is half the EDGE, so a
// quarter of the pixels — and pixels are what cost memory. Two nested boxes,
// drawn to scale, make that obvious at a glance: the small one visibly covers a
// quarter of the big one.
export default function ResizeNote({ fromW, fromH, toW, toH, file }: {
  fromW: number
  fromH: number
  toW: number
  toH: number
  file: string
}) {
  if (!fromW || !fromH || !toW || !toH) return null

  // Draw the ORIGINAL to a fixed box and the copy to the same scale, so the
  // ratio of the drawn areas is the real ratio of the pixel counts.
  const BOX = 26
  const scale = BOX / Math.max(fromW, fromH)
  const ow = Math.max(2, Math.round(fromW * scale))
  const oh = Math.max(2, Math.round(fromH * scale))
  const nw = Math.max(1, Math.round(toW * scale))
  const nh = Math.max(1, Math.round(toH * scale))

  // Uncompressed memory is what the GPU pays: w*h*4 bytes, +1/3 for mipmaps
  // (same formula as core/textures.vram_bytes).
  const vram = (w: number, h: number) => Math.round(w * h * 4 * (4 / 3))
  const before = vram(fromW, fromH)
  const after = vram(toW, toH)
  const savedPct = before > 0 ? Math.round((1 - after / before) * 100) : 0

  return (
    <div className="rz-note"
      title={`Replaced ${file} (${fromW}×${fromH}). The material now links to the smaller copy — undo in Cinema 4D to go back.`}>
      <svg className="rz-fig" width={BOX} height={BOX} viewBox={`0 0 ${BOX} ${BOX}`} aria-hidden="true">
        <rect x="0.5" y="0.5" width={ow - 1} height={oh - 1} className="rz-old" />
        <rect x="0.5" y="0.5" width={nw} height={nh} className="rz-new" />
      </svg>
      <span className="rz-dims">
        <s>{fromW}×{fromH}</s> → <b>{toW}×{toH}</b>
      </span>
      <span className="rz-vram">
        {humanBytes(before)} → <b>{humanBytes(after)}</b> VRAM
      </span>
      {savedPct > 0 && <span className="rz-saved">−{savedPct}%</span>}
    </div>
  )
}
