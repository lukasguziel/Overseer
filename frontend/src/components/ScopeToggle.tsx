import { IconScene, IconSelection } from './icons'

export default function ScopeToggle({ scope, setScope, sel }: {
  scope: boolean
  setScope: (v: boolean) => void
  sel?: { count: number; names: string[] }
}) {
  // Only show the live C4D selection once selection scope is active; in
  // whole-scene mode the button keeps its plain default label.
  const count = sel?.count ?? 0
  const names = sel?.names ?? []
  let selLabel = 'active + children'
  if (scope) {
    if (count === 0) selLabel = 'nothing selected'
    else if (count === 1) selLabel = names[0] || '1 object'
    else selLabel = `${names[0] || '1 object'} +${count - 1}`
  }

  return (
    <div className="scope-toggle" role="group" aria-label="Scope">
      <button className={!scope ? 'on' : ''} onClick={() => setScope(false)}
        title="Operate on every object in the scene">
        <IconScene /><span>Whole scene<small>all objects</small></span>
      </button>
      <button className={scope ? 'on' : ''} onClick={() => setScope(true)}
        title="Operate only on the active selection and its children">
        <IconSelection />
        <span>Selection<small className={scope && count > 0 ? 'sel-live' : ''}>{selLabel}</small></span>
      </button>
    </div>
  )
}
