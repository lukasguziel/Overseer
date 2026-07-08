import type { Organizer } from '../hooks/useOrganizer'
import Workbench from '../components/Workbench'

const LANG_LABEL: Record<string, string> = { de: 'German', en: 'English', unknown: '—' }

export default function TranslateTab({ org }: { org: Organizer }) {
  const { translation, accepted, setAccepted, busy, previewing,
    translateTarget, setTranslateTarget } = org
  const rows = translation?.diff || []
  const detected = translation?.detected
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
          Rewrites object names into the target language, word by word. Casing,
          separators and numbers are kept — only the words change. Runs on its
          own; it never touches your casing convention.
        </p>

        <label>Target language
          <select value={translateTarget} onChange={(e) => setTranslateTarget(e.target.value)}>
            <option value="en">→ English</option>
            <option value="de">→ German</option>
          </select>
        </label>

        <h3>Detected in scene</h3>
        {detected && detected.total > 0
          ? (
            <>
              <div className="lang-detect">
                <span className={`lang-pill${detected.dominant === 'de' ? ' on' : ''}`}>DE {detected.de}</span>
                <span className={`lang-pill${detected.dominant === 'en' ? ' on' : ''}`}>EN {detected.en}</span>
                <span className="lang-pill dim">? {detected.unknown}</span>
              </div>
              <p className="hint-sm">
                Mostly <b>{LANG_LABEL[detected.dominant]}</b> across {detected.total} names.
              </p>
            </>
          )
          : <p className="hint-sm">Run an analysis to detect the language.</p>}

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
        empty={`No names to translate into ${LANG_LABEL[translateTarget]}. 🎉`}
        applyLabel="Translate selected" onApply={org.applyTranslate} busy={busy}
        note={translation?.count ? `${translation.count} translatable · ${accepted.size} chosen.` : null}
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
              <td>
                <button className="mini" disabled={busy}
                  title="Translate just this one now (undoable)"
                  onClick={() => org.applyTranslateOne(d.guid, d.old)}>translate</button>
              </td>
            </tr>
          ))}
        </tbody></table>
      </Workbench>
    </div>
  )
}
