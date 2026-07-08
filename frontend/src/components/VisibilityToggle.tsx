import { IconEye, IconEyeOff } from './icons'

// Eye toggle: by default hidden objects (Object Manager editor dot OFF) are
// excluded from every statistic; flip it to fold them back in. `hidden` is the
// count of hidden objects in the scene, shown as a hint.
export default function VisibilityToggle({ includeHidden, setIncludeHidden, hidden }: {
  includeHidden: boolean
  setIncludeHidden: (v: boolean) => void
  hidden?: number
}) {
  const has = (hidden ?? 0) > 0
  return (
    <button
      className={'eye-toggle' + (includeHidden ? ' on' : '')}
      onClick={() => setIncludeHidden(!includeHidden)}
      title={includeHidden
        ? 'Hidden objects are counted in all stats — click to exclude them'
        : 'Hidden objects (Object Manager visibility off) are excluded from all stats — click to include them'}>
      {includeHidden ? <IconEye /> : <IconEyeOff />}
      <span>{includeHidden ? 'All objects' : 'Visible only'}
        {has && <small>{hidden} hidden</small>}
      </span>
    </button>
  )
}
