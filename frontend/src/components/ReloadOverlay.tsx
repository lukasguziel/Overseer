// Loading style for the "reload all areas" pass (selection changed under
// selection scope): a fullscreen overlay with a client-side stepped progress
// bar — one tick per area (report, naming, translate, structure, layers,
// audits) as each is refreshed in turn. Distinct from Preloader, which mirrors
// the backend's per-item /api/progress for a single blocking operation.
export interface ReloadStep { step: number; total: number; label: string }

export default function ReloadOverlay({ progress }: { progress: ReloadStep }) {
  const { step, total, label } = progress
  const pct = total > 0 ? Math.round((step / total) * 100) : 0
  return (
    <div className="preloader">
      <div className="pl-box">
        <div className="pl-spinner" />
        <div className="pl-phase">Updating all areas…</div>
        <div className="pl-track">
          <div className="pl-fill" style={{ width: pct + '%' }} />
        </div>
        <div className="pl-meta"><b>{step + 1}</b> / {total} · {label}</div>
      </div>
    </div>
  )
}
