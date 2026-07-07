import { IconScene, IconSelection } from './icons'

export default function ScopeToggle({ scope, setScope }: {
  scope: boolean
  setScope: (v: boolean) => void
}) {
  return (
    <div className="scope-toggle" role="group" aria-label="Scope">
      <button className={!scope ? 'on' : ''} onClick={() => setScope(false)}
        title="Operate on every object in the scene">
        <IconScene /><span>Whole scene<small>all objects</small></span>
      </button>
      <button className={scope ? 'on' : ''} onClick={() => setScope(true)}
        title="Operate only on the active selection and its children">
        <IconSelection /><span>Selection<small>active + children</small></span>
      </button>
    </div>
  )
}
