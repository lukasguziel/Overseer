import type { Organizer } from '../hooks/useOrganizer'
import ChangeHistory from '../components/ChangeHistory'
import HistoryList, { type HistoryRow } from '../components/HistoryList'
import type { HistoryEntry } from '../types'
import { humanBytes, humanNum } from '../lib/format'

// Analysis snapshots in the change-history look: time · chip · summary,
// expandable to the full numbers of that run.
function analysisRows(history: HistoryEntry[]): HistoryRow[] {
  return history.map((h, i) => ({
    id: `${h.ts || i}`,
    time: h.at.length >= 16 ? h.at.slice(5, 16) : h.at,   // "MM-DD HH:MM"
    kind: 'analysis',
    kindLabel: 'Analyze',
    summary: `${h.file} · ${humanNum(h.objects)} obj · ${Math.round((h.compliance || 0) * 100)}%`,
    details: (
      <table className="diff ch-items"><tbody>
        <tr><td className="ch-field dim">objects</td><td>{humanNum(h.objects)}</td></tr>
        {h.polys != null && <tr><td className="ch-field dim">polygons</td><td>{humanNum(h.polys)}</td></tr>}
        {h.size != null && <tr><td className="ch-field dim">size</td><td>{humanBytes(h.size)}</td></tr>}
        {h.compliance != null && <tr><td className="ch-field dim">structure</td><td>{Math.round(h.compliance * 100)}%</td></tr>}
      </tbody></table>
    ),
  }))
}

function SectionHead({ title }: { title: string }) {
  return <div className="misc-sec"><span>{title}</span><hr /></div>
}

export default function MiscTab({ org }: { org: Organizer }) {
  const { presets, activePreset, busy, exported, history, changes } = org
  return (
    <div className="misc misc-grid">
      <SectionHead title="Misc" />
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head"><h3>Presets</h3></div>
          <p className="hint-sm">
            Pick a state-of-the-art style — it configures casing, translations,
            groups and the node graph in one go. The <code>scene-rules</code>
            skill can also write a personal “how you work” preset from your
            own projects.
          </p>
          <div className="preset-list">
            {presets.length === 0 && <p className="hint-sm">No presets found.</p>}
            {presets.map((p) => (
              <div key={p.id} className={'preset' + (activePreset === p.id ? ' on' : '')}>
                <div className="preset-main">
                  <b>{p.name}</b>{activePreset === p.id && <span className="preset-badge">active</span>}
                  <div className="hint-sm" style={{ margin: '2px 0 0' }}>{p.description}</div>
                  <div className="dim" style={{ fontSize: 11, marginTop: 4 }}>{(p.groups || []).join(' · ')}</div>
                </div>
                <button className="sm" onClick={() => org.applyPreset(p.id)} disabled={busy}>Apply</button>
              </div>
            ))}
          </div>
        </section>

        <section className="card">
          <div className="card-head"><h3>Export scene hierarchy</h3></div>
          <p className="hint-sm">
            Writes a full snapshot <b>next to your project file</b> (falls back
            to the repo folder if the scene is unsaved). The JSON is what the
            <code>scene-rules</code> skill / Claude reads; the CSV is a flat
            object table for Excel/Sheets.
          </p>
          <div className="btns">
            <button onClick={org.doExportJson} disabled={busy}>Export as JSON</button>
            <button onClick={org.doExportCsv} disabled={busy}>Export as CSV</button>
          </div>
          {exported && <p className="example" style={{ marginTop: 12 }}>Written: <code>{exported}</code></p>}
        </section>
      </div>

      <SectionHead title="History" />
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head">
            <h3>Change history</h3>
            {changes.length > 0 && (
              <button className="ghost sm" onClick={org.doClearChanges}
                title="Clear the log (does not undo anything in the scene)">Clear log</button>
            )}
          </div>
          <p className="hint-sm">
            Every change made through the tool, newest first — expand to read the
            before → after per object. <b>Revert</b> restores those values in one
            undo step. Material/texture actions are logged but not revertible here.
          </p>
          <ChangeHistory changes={changes} onRevert={org.doRevertChange} />
        </section>

        <section className="card">
          <div className="card-head"><h3>Analysis history</h3></div>
          <p className="hint-sm">
            Every analysis run, newest first — expand an entry for the full
            numbers of that snapshot. Up to 100 are kept.
          </p>
          {history.length === 0
            ? <p className="hint-sm">No analyses recorded yet.</p>
            : <HistoryList rows={analysisRows(history)} perPage={10} />}
        </section>
      </div>

      <SectionHead title="Additional" />
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head"><h3>Debug</h3></div>
          <p className="hint-sm">
            The server runs while the “Scene Organizer” window is open in
            C4D — closing that window stops it.
          </p>
          <div className="btns">
            <button onClick={() => window.location.reload()}>Reload UI</button>
            <button onClick={() => window.open('/', '_blank')}>Open in new tab</button>
          </div>
          <p className="example" style={{ marginTop: 12 }}>
            Serving at <code>{window.location.origin}</code>
          </p>
        </section>

        <section className="card about-card">
          <div className="card-head"><h3>About</h3></div>
          <p className="hint-sm">Scene Organizer — analyze, name and structure your C4D scenes.</p>
          <div className="about-links">
            <a className="about-link" href="https://github.com/Goodsoup-Family-Crypt/scene-organizer"
              target="_blank" rel="noreferrer">GitHub ↗</a>
            <a className="about-link donate" href="https://www.buymeacoffee.com/bamerus"
              target="_blank" rel="noreferrer">♥ Donate to support</a>
          </div>
        </section>
      </div>
    </div>
  )
}
