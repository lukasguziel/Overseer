import type { Organizer } from '../hooks/useOrganizer'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedPanel from '../components/AcceptedPanel'
import AreaHistory from '../components/AreaHistory'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'
import Tip from '../components/Tip'
import { DiffOld, DiffNew } from '../components/DiffText'
import { OFFLINE_TARGETS, GOOGLE_TARGETS } from '../lib/constants'

const LANG_LABEL: Record<string, string> = {
  de: 'German', en: 'English', fr: 'French', es: 'Spanish', it: 'Italian',
  nl: 'Dutch', pl: 'Polish', cs: 'Czech', pt: 'Portuguese', ru: 'Russian',
  tr: 'Turkish', uk: 'Ukrainian', zh: 'Chinese', ja: 'Japanese', ko: 'Korean',
  ar: 'Arabic', auto: 'auto', unknown: 'Unknown',
}

export default function TranslateTab({ org }: { org: Organizer }) {
  const { translation, busy, previewing,
    translateTarget, setTranslateTarget, translateEngine, setTranslateEngine } = org
  const pager = usePager(translation?.diff || [], 10)
  const detected = translation?.detected

  if (!org.report) {
    return <EmptyState onAction={org.doAnalyze} busy={busy} />
  }

  return (
    <div className="stacked">
    <div className="workbench">
      <aside className={'wb-side' + (previewing ? ' side-loading' : '')}>
        <h3>Translate names</h3>
        <p className="hint-sm">
          Rewrites object names into the target language, word by word. Casing,
          separators and numbers are kept — only the words change. Runs on its
          own; it never touches your casing convention.
        </p>

        <label>
          <Tip text="Target language the object names are translated into word by word. Casing, separators and numbers stay unchanged.">
            <span>Target language</span>
          </Tip>
          <select value={translateTarget} onChange={(e) => setTranslateTarget(e.target.value)}>
            {(translateEngine === 'google' ? GOOGLE_TARGETS : OFFLINE_TARGETS).map((lg) => (
              <option key={lg} value={lg}>→ {LANG_LABEL[lg]}</option>
            ))}
          </select>
        </label>

        <label>
          <Tip text="Offline stays on your machine and knows a smaller set of words (English ↔ German). Google understands any language, but the names are sent online.">
            <span>Engine</span>
          </Tip>
          <select value={translateEngine} onChange={(e) => {
            const eng = e.target.value
            setTranslateEngine(eng)
            // Offline only knows EN/DE — snap back if a Google-only target was picked.
            if (eng !== 'google' && !OFFLINE_TARGETS.includes(translateTarget)) setTranslateTarget('en')
          }}>
            <option value="offline">Offline (smaller word set)</option>
            <option value="google">Google online (any language)</option>
          </select>
        </label>
        {translateEngine === 'google' && (
          <p className="hint-sm">⚠ Online: names are sent to Google; needs
            internet and takes a moment on large scenes.</p>
        )}

        <Tip text="Language of the existing names, detected automatically. A name only counts toward its source language as long as a translation would actually change it.">
          <h3>Detected in scene</h3>
        </Tip>
        {detected && detected.total > 0
          ? (
            <>
              <ul className="grouplist">
                {Object.entries(detected.counts || {})
                  .sort((a, b) => b[1] - a[1])
                  .map(([lg, n]) => (
                    <li key={lg} className={detected.dominant === lg ? 'lang-dom' : ''}>
                      <b>{LANG_LABEL[lg] || lg.toUpperCase()}</b><span>{n}</span>
                    </li>
                  ))}
              </ul>
              <p className="hint-sm">
                Mostly <b>{LANG_LABEL[detected.dominant] || detected.dominant}</b> across {detected.total} names.
                A name counts under its source language only while a translation
                would actually change it — once everything is applied, all
                counts sit on the target language.
              </p>
            </>
          )
          : <p className="hint-sm">Run an analysis to detect the language.</p>}
      </aside>

      <Workbench
        doc="translate-preview"
        title="Translation preview" count={translation?.count ?? 0} loading={previewing}
        empty={`Every name is already ${LANG_LABEL[translateTarget]}`}
        hint="Click a row to select & frame the object in Cinema 4D · the green ✓ translates it · the grey one keeps the name"
        applyLabel="Apply all" onApply={org.applyTranslate}
        onAcceptAll={() => org.keepAll('translate')} busy={busy}
        progress={org.progress}
        note={translation?.applied != null ? `${translation.applied} applied (undoable).` : null}
      >
        <div className="rename-list">
          {pager.rows.map((d) => (
            <SuggestionRow key={d.guid} busy={busy}
              applyTitle="Apply — translate now (undoable)"
              onApply={() => org.applyTranslateOne(d.guid, d.old)}
              onAcceptAsIs={() => org.keep('translate', d.old)}
              onFocus={() => org.doFocus(d.guid, d.old)}
            >
              {d.lang && d.lang !== 'unknown'
                ? <span className="rule-tag">{d.lang.toUpperCase()}</span>
                : <span className="rule-tag rt-casing">?</span>}
              <span className="rn-old" title={d.old}><DiffOld oldS={d.old} newS={d.new} /></span>
              <span className="rn-arrow">→</span>
              <span className="rn-new"
                title={(d.words || []).map((w) => `${w[0]}→${w[1]}`).join(', ') || d.new}>
                <DiffNew oldS={d.old} newS={d.new} />
              </span>
            </SuggestionRow>
          ))}
        </div>
        <Pager pager={pager} />
      </Workbench>
    </div>

    <AcceptedPanel org={org} />
    <AreaHistory org={org} area="translation" kinds={['translate']} />
    </div>
  )
}
