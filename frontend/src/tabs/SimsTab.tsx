import type { Organizer } from '../hooks/useOrganizer'

// Placeholder — implemented by the Sims audit area.
export default function SimsTab({ org }: { org: Organizer }) {
  void org
  return <div className="fl-empty">Sims audit — coming right up.</div>
}
