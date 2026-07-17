import type { Organizer } from '../hooks/useOrganizer'
import ActionButton from '../components/ActionButton'
import ChangeHistory from '../components/ChangeHistory'
import PhoneAccess from '../components/PhoneAccess'
import HistoryList, { type HistoryRow } from '../components/HistoryList'
import Tip from '../components/Tip'
import type { HistoryEntry } from '../types'
import { humanBytes, humanNum } from '../lib/format'
import { version } from '../../package.json'

// The artists who ran the plugin on real production scenes before it shipped.
const BETA_TESTERS = ['Cornelius Dämmrich', 'Raphael Rau']

// Analysis snapshots in the change-history look: time · chip · summary,
// expandable to the full numbers of that run.
function analysisRows(history: HistoryEntry[]): HistoryRow[] {
  return history.map((h, i) => ({
    id: `${h.ts || i}`,
    time: h.at.length >= 16 ? h.at.slice(5, 16) : h.at,   // "MM-DD HH:MM"
    kind: 'analysis',
    kindLabel: 'Analyze',
    // The log is per project — the file name would repeat on every row.
    summary: `${humanNum(h.objects)} obj`,
    details: (
      <table className="diff ch-items"><tbody>
        <tr><td className="ch-field dim">objects</td><td>{humanNum(h.objects)}</td></tr>
        {h.polys != null && <tr><td className="ch-field dim">polygons</td><td>{humanNum(h.polys)}</td></tr>}
        {h.size != null && <tr><td className="ch-field dim">size</td><td>{humanBytes(h.size)}</td></tr>}
      </tbody></table>
    ),
  }))
}

function SectionHead({ title }: { title: string }) {
  return <div className="section-head"><span>{title}</span></div>
}

export default function MiscTab({ org }: { org: Organizer }) {
  const { history, changes } = org
  return (
    <div className="misc misc-grid">
      <SectionHead title="History" />
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head">
            <Tip text="Every change made through the tool, newest first. Expand to see before → after; “Revert” restores the old values in one undo step.">
              <h3>Change history</h3>
            </Tip>
            {changes.length > 0 && (
              <ActionButton onClick={org.doClearChanges}
                title="Clear the log (does not undo anything in the scene)">Clear log</ActionButton>
            )}
          </div>
          <p className="hint-sm">
            Every change made through the tool <b>across all areas</b>, newest
            first — expand to read the before → after per object. <b>Revert</b>{' '}
            restores those values in one undo step. Material/texture actions are
            logged but not revertible here. Each work tab also shows its own
            slice of this log at its foot.
          </p>
          <ChangeHistory changes={changes} onRevert={org.doRevertChange} />
        </section>

        <section className="card">
          <div className="card-head">
            <Tip text="Every analysis run of THIS project, newest first. Expand to see the full metrics of that snapshot. Up to 100 are kept per project.">
              <h3>Analysis history</h3>
            </Tip>
            {history.length > 0 && (
              <ActionButton onClick={org.doClearHistory}
                title="Clear this project's log (the scene is untouched; trend sparklines start over)">Clear log</ActionButton>
            )}
          </div>
          <p className="hint-sm">
            Every analysis run of this project, newest first — expand an entry
            for the full numbers of that snapshot. Up to 100 are kept.
          </p>
          {history.length === 0
            ? <p className="hint-sm">No analyses recorded yet.</p>
            : <HistoryList rows={analysisRows(history)} perPage={10} />}
        </section>
      </div>

      <SectionHead title="Additional" />
      {/* Left column: Credits (+ the dev-only Debug card below it — Vite drops
          it from the production bundle). Right column: open-on-phone QR. */}
      <div className="ov-cols2">
        <div className="stacked">
          <section className="card credits-card">
            <div className="card-head"><h3>Credits</h3></div>
            <p className="hint-sm">Overseer — analyze, name and structure your C4D scenes.</p>
            <p className="hint-sm">Version v{version}</p>
            <p className="hint-sm">
              <b className="credits-label">Special thanks:</b>
              <a className="act" href="https://corneliusdammrich.com"
                target="_blank" rel="noreferrer">Cornelius Dämmrich ↗</a> — many of the
              features in here exist because of him; his input pushed the plugin far
              beyond what I had imagined for it. Also thanks to him I could use
              juicy production scenes to improve the plugin.
            </p>
            <p className="hint-sm">
              <b className="credits-label">Beta testers:</b>
              {BETA_TESTERS.join(', ')}
            </p>
          </section>

          {import.meta.env.DEV && (
            <section className="card">
              <div className="card-head"><h3>Debug</h3></div>
              <p className="hint-sm">
                The server runs while the “Overseer” window is open in
                C4D — closing that window stops it.
              </p>
              <div className="btns btns-auto">
                <ActionButton onClick={() => window.location.reload()}>Reload UI</ActionButton>
                <ActionButton onClick={() => window.open('/', '_blank')}>Open in new tab</ActionButton>
              </div>
              <p className="example" style={{ marginTop: 12 }}>
                Serving at <code>{window.location.origin}</code>
              </p>
            </section>
          )}
        </div>

        <section className="card">
          <div className="card-head"><h3>Read the scene on your phone</h3></div>
          <PhoneAccess />
        </section>
      </div>

      {/* Support sits BELOW the cards, spanning the whole tab. The hearts drift
          out of the button itself — decorative, hence aria-hidden and no pointer
          events (see styles.css). */}
      <span className="donate-wrap">
        <a className="credits-link donate" href="https://www.paypal.com/donate/?hosted_button_id=XSBBJYYEJZ7TE"
          target="_blank" rel="noreferrer">♥ Support me</a>
        <span className="donate-hearts" aria-hidden="true">
          <i>♥</i><i>♥</i><i>♥</i><i>♥</i>
        </span>
      </span>
    </div>
  )
}
