// Uniform "no scene yet" placeholder used by every tab that needs a report.
export default function EmptyState({ message, actionLabel, onAction, busy }: {
  message?: string
  actionLabel?: string
  onAction?: () => void
  busy?: boolean
}) {
  return (
    <div className="empty-state">
      <p>{message || 'No scene analyzed yet — open your scene in Cinema 4D, then run an analysis.'}</p>
      {onAction && (
        <button onClick={onAction} disabled={busy}>{actionLabel || 'Analyze scene'}</button>
      )}
    </div>
  )
}
