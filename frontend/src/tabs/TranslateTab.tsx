import type { Organizer } from '../hooks/useOrganizer'
import Workbench from '../components/Workbench'

const LANG_LABEL: Record<string, string> = {
  de: 'German', en: 'English', fr: 'French', es: 'Spanish', it: 'Italian',
  nl: 'Dutch', pl: 'Polish', cs: 'Czech', pt: 'Portuguese', ru: 'Russian',
  tr: 'Turkish', auto: 'auto', unknown: '—',
}

export default function TranslateTab({ org }: { org: Organizer }) {
  const { translation, accepted, setAccepted, busy, previewing,
    translateTarget, setTranslateTarget, translateEngine, setTranslateEngine } = org
  const rows = translation?.diff || []
  const detected = translation?.detected
  const toggle = (guid: number) => setAccepted((s) => {
    const n = new Set(s)
    if (n.has(guid)) n.delete(guid); else n.add(guid)
    return n
  })

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

        <label>Engine
          <select value={translateEngine} onChange={(e) => setTranslateEngine(e.target.value)}>
            <option value="offline">Offline dictionaries (10 languages)</option>
            <option value="google">Google online (any language)</option>
          </select>
        </label>
        {translateEngine === 'google' && (
          <p className="hint-sm">⚠ Online: names are sent to Google; needs
            internet and takes a moment on large scenes.</p>
        )}

        <h3>Detected in scene</h3>
        {detected && detected.total > 0
          ? (
            <>
              <div className="lang-detect">
                {Object.entries(detected.counts || {})
                  .sort((a, b) => b[1] - a[1])
                  .map(([lg, n]) => (
                    <span key={lg}
                      className={`lang-pill${detected.dominant === lg ? ' on' : ''}${lg === 'unknown' ? ' dim' : ''}`}>
                      {lg === 'unknown' ? '?' : lg.toUpperCase()} {n}
                    </span>
                  ))}
              </div>
              <p className="hint-sm">
                Mostly <b>{LANG_LABEL[detected.dominant] || detected.dominant}</b> across {detected.total} names.
              </p>
            </>
          )
          : <p className="hint-sm">Run an analysis to detect the language.</p>}

        <p className="hint-sm">Missing a word? Add it in the <b>Rules</b> tab’s
          translations, then re-open this tab.</p>
      </aside>

      <Workbench
        title="Translation preview" count={accepted.size} loading={previewing}
        empty={`No names to translate into ${LANG_LABEL[translateTarget]}. 🎉`}
        applyLabel="Process all" onApply={org.applyTranslate} busy={busy}
        progress={org.progress}
        note={translation?.count
          ? `${translation.count} translatable${accepted.size !== rows.length ? ` · ${rows.length - accepted.size} skipped` : ''}.`
          : null}
      >
        <div className="rename-list">
          {rows.slice(0, 400).map((d) => {
            const on = accepted.has(d.guid)
            return (
              <div className={'rename-row' + (on ? '' : ' row-off')} key={d.guid}>
                {d.lang && d.lang !== 'unknown'
                  ? <span className="rule-tag">{d.lang.toUpperCase()}</span>
                  : <span className="rule-tag rt-casing">?</span>}
                <span className="rn-old" title={d.old}>{d.old}</span>
                <span className="rn-arrow">→</span>
                <span className="rn-new"
                  title={(d.words || []).map((w) => `${w[0]}→${w[1]}`).join(', ') || d.new}>{d.new}</span>
                <span className="rn-actions">
                  <button className="rn-ok" title="Accept — translate now (undoable)"
                    onClick={() => org.applyTranslateOne(d.guid, d.old)} disabled={busy}>✓</button>
                  <button className="rn-no" title={on ? 'Skip — leave out of "Process all"' : 'Skipped — click to include again'}
                    onClick={() => toggle(d.guid)} disabled={busy}>{on ? '✕' : '↺'}</button>
                </span>
              </div>
            )
          })}
        </div>
      </Workbench>
    </div>
  )
}
