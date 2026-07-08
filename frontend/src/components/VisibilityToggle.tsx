import { IconEye, IconEyeOff } from './icons'

// Segmented switch (built like ScopeToggle): "All objects" folds hidden
// objects (Object Manager editor dot OFF) into every statistic, "Visible only"
// excludes them. `hidden` is the count of hidden objects, surfaced on the
// Visible-only side so it's clear what that mode leaves out.
export default function VisibilityToggle({ includeHidden, setIncludeHidden, hidden }: {
  includeHidden: boolean
  setIncludeHidden: (v: boolean) => void
  hidden?: number
}) {
  const count = hidden ?? 0
  const hiddenLabel = count > 0 ? `${count} hidden` : 'none hidden'

  return (
    <div className="scope-toggle vis-toggle" role="group" aria-label="Visibility">
      <button className={includeHidden ? 'on' : ''} onClick={() => setIncludeHidden(true)}
        title="Count every object, including ones hidden in the Object Manager">
        <IconEye /><span>All objects<small>incl. hidden</small></span>
      </button>
      <button className={!includeHidden ? 'on' : ''} onClick={() => setIncludeHidden(false)}
        title="Exclude objects hidden in the Object Manager from all stats">
        <IconEyeOff />
        <span>Visible only<small className={!includeHidden && count > 0 ? 'sel-live' : ''}>{hiddenLabel}</small></span>
      </button>
    </div>
  )
}
