import type { Organizer } from '../hooks/useOrganizer'

// Placeholder — implemented by the Files audit area.
export default function FilesTab({ org }: { org: Organizer }) {
  void org
  return <div className="fl-empty">Files audit — coming right up.</div>
}
