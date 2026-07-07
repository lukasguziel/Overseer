import type { Organizer } from '../hooks/useOrganizer'

export default function MiscTab({ org }: { org: Organizer }) {
  const { presets, activePreset, busy, exported, history } = org
  return (
    <div className="misc">
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

      <section className="card" style={{ marginTop: 16 }}>
        <div className="card-head"><h3>Export structure</h3></div>
        <p className="hint-sm">
          Writes a full snapshot of the scene hierarchy to the repo folder.
          The JSON is what the <code>scene-rules</code> skill / Claude reads to
          build the rule set; the CSV is a flat object table for Excel/Sheets.
        </p>
        <div className="btns">
          <button onClick={org.doExportJson} disabled={busy}>Export as JSON</button>
          <button onClick={org.doExportCsv} disabled={busy}>Export as CSV</button>
        </div>
        {exported && <p className="example" style={{ marginTop: 12 }}>Written: <code>{exported}</code></p>}
      </section>

      <section className="card" style={{ marginTop: 16 }}>
        <div className="card-head"><h3>Analysis history</h3></div>
        {history.length === 0
          ? <p className="hint-sm">No analyses recorded yet.</p>
          : <table className="diff hist"><tbody>
              {history.map((h, i) => (
                <tr key={i}>
                  <td>{h.file}</td>
                  <td className="dim">{h.at}</td>
                  <td className="dim">{h.objects} obj</td>
                  <td className="dim">{Math.round((h.compliance || 0) * 100)}%</td>
                </tr>
              ))}
            </tbody></table>}
        <p className="hint-sm">Most recent first · last {history.length} of up to 100 kept.</p>
      </section>

      <section className="card" style={{ marginTop: 16 }}>
        <div className="card-head"><h3>Debug</h3></div>
        <p className="hint-sm">
          The server runs while the “Scene Organizer (Web)” window is open in
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
    </div>
  )
}
