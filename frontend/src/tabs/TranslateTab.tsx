import type { Organizer } from '../hooks/useOrganizer'
import Workbench from '../components/Workbench'

export default function TranslateTab({ org }: { org: Organizer }) {
  const { translation, accepted, setAccepted, busy, previewing } = org
  const rows = translation?.diff || []
  const allOn = rows.length > 0 && rows.every((d) => accepted.has(d.guid))
  const toggle = (guid: number) => setAccepted((s) => {
    const n = new Set(s)
    if (n.has(guid)) n.delete(guid); else n.add(guid)
    return n
  })
  const toggleAll = () => setAccepted(allOn ? new Set() : new Set(rows.map((d) => d.guid)))

  return (
    <div className="workbench">
      <aside className="wb-side">
        <h3>Translate names</h3>
        <p className="hint-sm">
          Detects object names containing non-English (German) words and
          proposes an English rename. Casing, separators and numbers are
          kept — only the words change. Tick the ones you want, then apply.
        </p>
        <label className="check">
          <input type="checkbox" checked={allOn} onChange={toggleAll} />
          Select all ({rows.length})
        </label>
        <p className="hint-sm">{accepted.size} selected</p>
        <p className="hint-sm">Missing a word? Add it in the <b>Rules</b> tab’s
          translations, then re-open this tab.</p>
      </aside>

      <Workbench
        title="Translation preview" count={accepted.size} loading={previewing}
        empty="No non-English names found. 🎉"
        applyLabel="Rename selected" onApply={org.applyTranslate} busy={busy}
        note={translation?.count ? `${translation.count} names detected · ${accepted.size} chosen.` : null}
      >
        <table className="diff"><tbody>
          {rows.slice(0, 400).map((d) => (
            <tr key={d.guid}>
              <td style={{ width: 24 }}>
                <input type="checkbox" checked={accepted.has(d.guid)} onChange={() => toggle(d.guid)} />
              </td>
              <td className="dim">{d.old}</td>
              <td className="arrow">→</td>
              <td>{d.new}</td>
              <td className="dim" style={{ fontSize: 11 }}>
                {(d.words || []).map((w) => `${w[0]}→${w[1]}`).join(', ')}
              </td>
            </tr>
          ))}
        </tbody></table>
      </Workbench>
    </div>
  )
}
