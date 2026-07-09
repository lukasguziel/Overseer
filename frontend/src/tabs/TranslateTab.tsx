import type { Organizer } from '../hooks/useOrganizer'
import Workbench from '../components/Workbench'
import SuggestionRow from '../components/SuggestionRow'
import AcceptedSection from '../components/AcceptedSection'
import EmptyState from '../components/EmptyState'
import Pager, { usePager } from '../components/Pager'
import { DiffOld, DiffNew } from '../components/DiffText'

const LANG_LABEL: Record<string, string> = {
  de: 'German', en: 'English', fr: 'French', es: 'Spanish', it: 'Italian',
  nl: 'Dutch', pl: 'Polish', cs: 'Czech', pt: 'Portuguese', ru: 'Russian',
  tr: 'Turkish', uk: 'Ukrainian', zh: 'Chinese', ja: 'Japanese', ko: 'Korean',
  ar: 'Arabic', auto: 'auto', unknown: 'Unknown',
}

// Offline dictionaries only translate into EN/DE; Google takes any code.
const OFFLINE_TARGETS = ['en', 'de']
const GOOGLE_TARGETS = ['en', 'de', 'fr', 'es', 'it', 'pt', 'nl', 'pl', 'cs',
  'ru', 'uk', 'tr', 'zh', 'ja', 'ko', 'ar']

export default function TranslateTab({ org }: { org: Organizer }) {
  const { translation, keeps, busy, previewing,
    translateTarget, setTranslateTarget, translateEngine, setTranslateEngine } = org
  const pager = usePager(translation?.diff || [])
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

        <label>Target language
          <select value={translateTarget} onChange={(e) => setTranslateTarget(e.target.value)}>
            {(translateEngine === 'google' ? GOOGLE_TARGETS : OFFLINE_TARGETS).map((lg) => (
              <option key={lg} value={lg}>→ {LANG_LABEL[lg]}</option>
            ))}
          </select>
        </label>

        <label>Engine
          <select value={translateEngine} onChange={(e) => {
            const eng = e.target.value
            setTranslateEngine(eng)
            // Offline only knows EN/DE — snap back if a Google-only target was picked.
            if (eng !== 'google' && !OFFLINE_TARGETS.includes(translateTarget)) setTranslateTarget('en')
          }}>
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
              </p>
            </>
          )
          : <p className="hint-sm">Run an analysis to detect the language.</p>}
      </aside>

      <Workbench
        title="Translation preview" count={translation?.count ?? 0} loading={previewing}
        empty={`Every name is already ${LANG_LABEL[translateTarget]} 🎉`}
        hint="Click a row to select & frame the object in Cinema 4D · ✓ translates it · = keeps the name"
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

    <AcceptedSection items={Array.from(keeps.translate)}
      onRestore={(nm) => org.unkeep('translate', nm)} />
    </div>
  )
}
