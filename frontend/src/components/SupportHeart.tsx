import { useEffect, useState } from 'react'

// Tiny "support me" heart next to the version. On the initial open it glows
// and puffs out a few mini hearts for a second — just enough to be noticed —
// then settles into a quiet, dim button.
export default function SupportHeart() {
  const [burst, setBurst] = useState(true)
  useEffect(() => {
    const t = setTimeout(() => setBurst(false), 1400)
    return () => clearTimeout(t)
  }, [])
  return (
    <a className={'support-heart' + (burst ? ' burst' : '')}
      href="https://www.paypal.com/donate/?hosted_button_id=XSBBJYYEJZ7TE" target="_blank" rel="noreferrer"
      title="Support me if you like this plugin — Overseer is free; a coffee keeps it going ♥">
      ♥
      {burst && [0, 1, 2, 3, 4].map((i) => (
        <span key={i} className={'sh-mini sh-mini-' + i}>♥</span>
      ))}
    </a>
  )
}
