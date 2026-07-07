import React, { useCallback, useEffect, useState } from 'react'
import { call } from './api.js'
import RuleGraph from './RuleGraph.jsx'

const CASINGS = [
  ['PascalCase', 'PascalCase'],
  ['camelCase', 'camelCase'],
  ['lower_snake', 'lower_snake'],
  ['UPPER_SNAKE', 'UPPER_SNAKE'],
  ['kebab', 'kebab-case'],
]
const LANGS = [
  ['en', 'English'],
  ['de', 'German'],
  ['none', 'No translation'],
]
const TABS = [
  ['overview', 'Overview'],
  ['assets', 'Assets'],
  ['naming', 'Naming'],
  ['translate', 'Translate'],
  ['structure', 'Structure'],
  ['layers', 'Layers'],
  ['rules', 'Rules'],
  ['misc', 'Misc'],
]

const CAT_ORDER = ['mesh', 'spline', 'light', 'camera', 'null', 'other']
const SORTS = [
  ['polygons', 'Polygons'],
  ['points', 'Points'],
  ['children', 'Children'],
  ['depth', 'Depth'],
  ['name', 'Name'],
]

// Kleine Client-Vorschau der Konvention (nur fuer die Beispiel-Anzeige).
function exampleName(casing, pad) {
  const words = ['key', 'light']
  const num = pad > 0 ? String(3).padStart(pad, '0') : '3'
  const cap = (w) => w[0].toUpperCase() + w.slice(1)
  switch (casing) {
    case 'PascalCase': return words.map(cap).join('') + num
    case 'camelCase': return words[0] + words.slice(1).map(cap).join('') + num
    case 'lower_snake': return words.join('_') + '_' + num
    case 'UPPER_SNAKE': return words.map((w) => w.toUpperCase()).join('_') + '_' + num
    case 'kebab': return words.join('-') + '-' + num
    default: return ''
  }
}

// ---------------------------------------------------------------------------
// Kleine wiederverwendbare Bausteine
// ---------------------------------------------------------------------------

function Tile({ value, label, tone, spark, delta }) {
  return (
    <div className={'tile' + (tone ? ' tile--' + tone : '')}>
      <div className="tile-top">
        <div className="tile-value">{value}</div>
        {spark && spark.length > 1 && <Sparkline data={spark} />}
      </div>
      <div className="tile-label">
        {label}
        {delta && delta.pct !== 0 && (
          <span className={'tile-delta ' + (delta.dir > 0 ? 'up' : 'down')}>
            {delta.dir > 0 ? '▲' : '▼'} {Math.abs(delta.pct)}%
          </span>
        )}
      </div>
    </div>
  )
}

// Winzige SVG-Sparkline (Verlauf ueber Analysen).
function Sparkline({ data, w = 62, h = 20 }) {
  const min = Math.min(...data); const max = Math.max(...data)
  const span = max - min || 1
  const step = data.length > 1 ? w / (data.length - 1) : w
  const pts = data.map((v, i) => `${(i * step).toFixed(1)},${(h - ((v - min) / span) * (h - 3) - 1.5).toFixed(1)}`).join(' ')
  const last = data[data.length - 1]
  const lx = (data.length - 1) * step
  const ly = h - ((last - min) / span) * (h - 3) - 1.5
  return (
    <svg className="spark" viewBox={`0 0 ${w} ${h}`} width={w} height={h} preserveAspectRatio="none">
      <polyline points={pts} fill="none" stroke="currentColor" strokeWidth="1.4"
        strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r="1.8" fill="currentColor" />
    </svg>
  )
}

// Binary-Split-Treemap: fuellt ein Rechteck rekursiv, gute Seitenverhaeltnisse.
function treemapBinary(items, x, y, w, h, out) {
  if (!items.length) return
  if (items.length === 1) { out.push({ ...items[0], x, y, w, h }); return }
  const total = items.reduce((s, d) => s + d.value, 0)
  let acc = 0; let i = 0
  while (i < items.length - 1 && acc + items[i].value < total / 2) { acc += items[i].value; i++ }
  const a = items.slice(0, i + 1); const b = items.slice(i + 1)
  const frac = a.reduce((s, d) => s + d.value, 0) / total
  if (w >= h) {
    treemapBinary(a, x, y, w * frac, h, out)
    treemapBinary(b, x + w * frac, y, w * (1 - frac), h, out)
  } else {
    treemapBinary(a, x, y, w, h * frac, out)
    treemapBinary(b, x, y + h * frac, w, h * (1 - frac), out)
  }
}

// Poly-Treemap: Flaeche = Polygone, Farbe = Kategorie, Klick -> framen.
function Treemap({ nodes, onFocus, height = 300 }) {
  const cells = React.useMemo(() => {
    const items = nodes.filter((n) => n.polygons > 0)
      .sort((a, b) => b.polygons - a.polygons).slice(0, 60)
      .map((n) => ({ value: n.polygons, node: n }))
    const out = []
    if (items.length) treemapBinary(items, 0, 0, 100, 100, out)
    return out
  }, [nodes])
  if (!cells.length) return <div className="wb-empty">No geometry to map.</div>
  return (
    <div className="treemap" style={{ height }}>
      {cells.map((c, i) => {
        const n = c.node
        const big = c.w > 13 && c.h > 11
        return (
          <button key={n.guid ?? i} className="tm-cell"
            style={{ left: c.x + '%', top: c.y + '%', width: c.w + '%', height: c.h + '%', background: catColor(n.category) }}
            onClick={() => onFocus?.(n.guid, n.name)} title={`${n.name} · ${humanNum(n.polygons)} polys`}>
            {big && <span className="tm-label"><span className="tm-name">{n.name}</span><span className="tm-val">{humanNum(n.polygons)}</span></span>}
          </button>
        )
      })}
    </div>
  )
}

// Dünner 100%-Stacked-Strip + Legende (Composition / Consistency).
const STRIP_PALETTE = ['#38bdf8', '#34d399', '#fbbf24', '#b07bff', '#f87171', '#8b8b93', '#f5843c']
function Strip({ data, colorFn, format = humanNum, legendMax = 6 }) {
  const entries = Object.entries(data || {}).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])
  const total = entries.reduce((s, [, v]) => s + v, 0)
  if (!total) return <div className="fl-empty">No data.</div>
  const col = colorFn || ((_, i) => STRIP_PALETTE[i % STRIP_PALETTE.length])
  return (
    <div className="strip-wrap">
      <div className="strip">
        {entries.map(([k, v], i) => (
          <div key={k} className="strip-seg" style={{ width: v / total * 100 + '%', background: col(k, i) }}
            title={`${k}: ${format(v)} (${Math.round(v / total * 100)}%)`} />
        ))}
      </div>
      <div className="strip-legend">
        {entries.slice(0, legendMax).map(([k, v], i) => (
          <span key={k} className="strip-key">
            <span className="strip-dot" style={{ background: col(k, i) }} />{k}<b>{Math.round(v / total * 100)}%</b>
          </span>
        ))}
      </div>
    </div>
  )
}

// Live-Preview-Panel mit sticky Apply-Leiste. Zeigt eine Diff-Tabelle.
function Workbench({ title, count, loading, empty, applyLabel, onApply, busy, note, children }) {
  return (
    <div className="wb-preview">
      <div className="wb-preview-head">
        <h3>{title}</h3>
        <span className="wb-count">
          {loading ? 'updating…' : count === 0 ? 'nothing to change' : `${count} change${count === 1 ? '' : 's'}`}
        </span>
      </div>
      {note && <p className="wb-note">{note}</p>}
      <div className="wb-scroll">
        {count === 0 && !loading
          ? <div className="wb-empty">{empty}</div>
          : children}
      </div>
      <div className="wb-applybar">
        <button className="apply lg" disabled={busy || !count} onClick={onApply}>
          {applyLabel} {count ? `(${count})` : ''}
        </button>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Formatter + Charts (dependency-frei, SVG/CSS)
// ---------------------------------------------------------------------------

function humanNum(n) {
  n = n || 0
  if (n >= 1e9) return (n / 1e9).toFixed(n >= 1e10 ? 0 : 1) + 'B'
  if (n >= 1e6) return (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + 'M'
  if (n >= 1e3) return (n / 1e3).toFixed(n >= 1e4 ? 0 : 1) + 'K'
  return String(n)
}
function humanBytes(b) {
  if (!b) return '—'
  const u = ['B', 'KB', 'MB', 'GB', 'TB']
  let i = 0; let v = b
  while (v >= 1024 && i < u.length - 1) { v /= 1024; i++ }
  return v.toFixed(v >= 100 || i === 0 ? 0 : 1) + ' ' + u[i]
}

// Generische Default-Namen (C4D-Objekttypen, DE + EN) -> "unbenannt".
const DEFAULT_TOKENS = new Set([
  'null', 'cube', 'sphere', 'plane', 'cone', 'cylinder', 'torus', 'disc', 'tube',
  'pyramid', 'platonic', 'figure', 'polygon', 'object', 'spline', 'light', 'camera',
  'floor', 'sky', 'background', 'foreground', 'environment', 'text', 'instance',
  'circle', 'rectangle', 'arc', 'helix', 'star', 'flower', 'cogwheel', 'profile',
  'formula', 'n-side', 'nside', 'vectorizer', 'landscape', 'relief', 'cloner', 'matrix',
  // Deutsch
  'wuerfel', 'würfel', 'kugel', 'ebene', 'kegel', 'zylinder', 'licht', 'kamera',
  'objekt', 'boden', 'himmel', 'nullobjekt', 'null-objekt', 'text-spline', 'instanz',
  'kreis', 'rechteck', 'stern', 'landschaft',
])
function baseName(name) { return (name || '').replace(/[._\s]*\d+$/, '').trim().toLowerCase() }
function isDefaultName(name, type) {
  const b = baseName(name)
  if (!b) return true
  if (DEFAULT_TOKENS.has(b)) return true
  const t = (type || '').toLowerCase()
  if (t && (b === t || b.startsWith(t))) return true
  return false
}

// Alle Hygiene-Metriken aus report.nodes ableiten (rein clientseitig).
function computeHygiene(nodes, totalPolys) {
  const defaults = []; const emptyGroups = []; const rootClutter = []; const outliers = []
  const byName = {}; const depth = {}
  const thr = Math.max(50000, totalPolys * 0.05)   // Ausreisser: allein >5% der Szene
  for (const n of nodes) {
    depth[n.depth] = (depth[n.depth] || 0) + 1;
    (byName[n.name] = byName[n.name] || []).push(n)
    if (isDefaultName(n.name, n.type)) defaults.push(n)
    if (n.category === 'null' && !n.children) emptyGroups.push(n)
    if (n.depth === 0 && n.category !== 'null') rootClutter.push(n)
    if (n.polygons > thr) outliers.push(n)
  }
  const dupes = Object.entries(byName).filter(([, a]) => a.length > 1)
    .map(([name, a]) => ({ name, count: a.length, guid: a[0].guid }))
    .sort((x, y) => y.count - x.count)
  outliers.sort((a, b) => b.polygons - a.polygons)
  // Pareto: wie viele Objekte machen 80% der Polygone aus?
  const sorted = nodes.filter((n) => n.polygons > 0).map((n) => n.polygons).sort((a, b) => b - a)
  let cum = 0; let p80 = 0
  for (const v of sorted) { cum += v; p80++; if (cum >= totalPolys * 0.8) break }
  const top10 = sorted.slice(0, 10).reduce((s, v) => s + v, 0)
  const conform = nodes.length - defaults.length - (nodes.length - Object.keys(byName).length)
  return {
    defaults, emptyGroups, rootClutter, outliers, dupes, depth,
    namingScore: nodes.length ? Math.round(Math.max(0, conform) / nodes.length * 100) : 100,
    dupTotal: dupes.reduce((s, d) => s + d.count, 0),
    p80, geoObjs: sorted.length,
    top10pct: totalPolys ? Math.round(top10 / totalPolys * 100) : 0,
  }
}

// Feste Kategorie-Farben -> konsistent ueber alle Charts hinweg.
const CATCOLOR = {
  light: '#fbbf24', camera: '#38bdf8', mesh: '#34d399',
  spline: '#b07bff', null: '#8b8b93', other: '#64748b',
}
const catColor = (k) => CATCOLOR[k] || '#64748b'

// Horizontale Balkenliste. rows: [{label, value, color?, sub?, onClick?}]
function BarList({ rows, format = humanNum, empty }) {
  const max = Math.max(1, ...rows.map((r) => r.value))
  if (!rows.length) return <div className="wb-empty">{empty || 'No data.'}</div>
  return (
    <div className="barlist">
      {rows.map((r, i) => {
        const clickable = typeof r.onClick === 'function'
        return (
          <div className={'bar-row' + (clickable ? ' clickable' : '')} key={i}
            onClick={clickable ? r.onClick : undefined}
            title={clickable ? 'Select & frame in viewport' : r.label}>
            <div className="bar-label">{r.label}{r.sub && <span className="bar-sub">{r.sub}</span>}</div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: (r.value / max * 100) + '%', background: r.color || 'var(--accent)' }} />
            </div>
            <div className="bar-value">{format(r.value)}</div>
          </div>
        )
      })}
    </div>
  )
}

// Kompakte klickbare Liste (Cleanup-Targets). items: [{guid,name,category?,meta?}]
function FocusList({ items, onFocus, empty, max = 8 }) {
  if (!items.length) return <div className="fl-empty">{empty || 'None 🎉'}</div>
  return (
    <div className="focuslist">
      {items.slice(0, max).map((n, i) => (
        <button key={n.guid ?? i} className="fl-row" onClick={() => onFocus?.(n.guid, n.name)}
          title="Select & frame in viewport">
          <span className="fl-dot" style={{ background: catColor(n.category || 'other') }} />
          <span className="fl-name">{n.name}</span>
          {n.meta && <span className="fl-meta">{n.meta}</span>}
        </button>
      ))}
      {items.length > max && <div className="fl-more">+{items.length - max} more</div>}
    </div>
  )
}

// Liste ungenutzter Materialien mit inline-Loeschbestaetigung (kein window.confirm
// -> im eingebetteten QtWebEngine unzuverlaessig).
function UnusedMaterials({ names, onDelete, max = 20 }) {
  const [confirm, setConfirm] = useState(null)
  if (!names.length) return <div className="fl-empty">Every material is in use 🎉</div>
  return (
    <div className="focuslist">
      {names.slice(0, max).map((nm, i) => (
        <div className="fl-row static mat-row" key={i}>
          <span className="fl-dot" style={{ background: 'var(--dim2)' }} />
          <span className="fl-name">{nm}</span>
          {confirm === nm ? (
            <span className="mat-confirm">
              delete?
              <button className="mat-yes" title="Confirm delete"
                onClick={() => { onDelete(nm); setConfirm(null) }}>✓</button>
              <button className="mat-no" title="Cancel" onClick={() => setConfirm(null)}>✕</button>
            </span>
          ) : (
            <button className="mat-x" title="Delete this material (undoable)"
              onClick={() => setConfirm(nm)}>×</button>
          )}
        </div>
      ))}
      {names.length > max && <div className="fl-more">+{names.length - max} more</div>}
    </div>
  )
}

// SVG-Donut mit Legende. data: {key: value}
function Donut({ data, colorFn = catColor, format = humanNum }) {
  const entries = Object.entries(data || {}).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1])
  const total = entries.reduce((s, [, v]) => s + v, 0)
  if (!total) return <div className="wb-empty">No data.</div>
  const R = 52; const SW = 20; const C = 2 * Math.PI * R
  let off = 0
  return (
    <div className="donut">
      <svg viewBox="0 0 130 130" className="donut-svg">
        <g transform="translate(65,65) rotate(-90)">
          <circle r={R} fill="none" stroke="var(--panel2)" strokeWidth={SW} />
          {entries.map(([k, v]) => {
            const len = v / total * C
            const seg = <circle key={k} r={R} fill="none" stroke={colorFn(k)} strokeWidth={SW}
              strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-off} />
            off += len
            return seg
          })}
        </g>
        <text x="65" y="61" className="donut-total">{humanNum(total)}</text>
        <text x="65" y="78" className="donut-cap">total</text>
      </svg>
      <div className="legend">
        {entries.map(([k, v]) => (
          <div className="legend-row" key={k}>
            <span className="legend-dot" style={{ background: colorFn(k) }} />
            <span className="legend-key">{k}</span>
            <span className="legend-val">{format(v)} <span className="dim">· {Math.round(v / total * 100)}%</span></span>
          </div>
        ))}
      </div>
    </div>
  )
}

// Compliance-Ring (SVG), 0..100
function Ring({ pct, tone }) {
  const R = 26; const SW = 7; const C = 2 * Math.PI * R
  const col = tone === 'good' ? 'var(--apply)' : tone === 'mid' ? 'var(--warn)' : 'var(--err)'
  return (
    <svg viewBox="0 0 64 64" className="ring">
      <circle cx="32" cy="32" r={R} fill="none" stroke="var(--panel2)" strokeWidth={SW} />
      <circle cx="32" cy="32" r={R} fill="none" stroke={col} strokeWidth={SW} strokeLinecap="round"
        strokeDasharray={`${pct / 100 * C} ${C}`} transform="rotate(-90 32 32)" />
      <text x="32" y="37" className="ring-text">{pct}%</text>
    </svg>
  )
}

// Icons
const IconScene = () => (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7"
    strokeLinecap="round" strokeLinejoin="round"><path d="M12 2 3 7l9 5 9-5-9-5Z" /><path d="m3 12 9 5 9-5" /><path d="m3 17 9 5 9-5" /></svg>
)
const IconTrash = () => (
  <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round"><path d="M3 6h18" /><path d="M8 6V4a1 1 0 0 1 1-1h6a1 1 0 0 1 1 1v2" /><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" /><path d="M10 11v6" /><path d="M14 11v6" /></svg>
)
const IconSelection = () => (
  <svg viewBox="0 0 24 24" width="17" height="17" fill="none" stroke="currentColor" strokeWidth="1.7"
    strokeLinecap="round" strokeLinejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2" /><path d="M17 3h2a2 2 0 0 1 2 2v2" /><path d="M21 17v2a2 2 0 0 1-2 2h-2" /><path d="M7 21H5a2 2 0 0 1-2-2v-2" /><rect x="8" y="8" width="8" height="8" rx="1" fill="currentColor" stroke="none" opacity=".85" /></svg>
)

function ScopeToggle({ scope, setScope }) {
  return (
    <div className="scope-toggle" role="group" aria-label="Scope">
      <button className={!scope ? 'on' : ''} onClick={() => setScope(false)}
        title="Operate on every object in the scene">
        <IconScene /><span>Whole scene<small>all objects</small></span>
      </button>
      <button className={scope ? 'on' : ''} onClick={() => setScope(true)}
        title="Operate only on the active selection and its children">
        <IconSelection /><span>Selection<small>active + children</small></span>
      </button>
    </div>
  )
}

// ---------------------------------------------------------------------------

export default function App() {
  const [tab, setTab] = useState('overview')
  const [scope, setScope] = useState(false)        // false = whole scene, true = selection

  const [casing, setCasing] = useState('PascalCase')
  const [language, setLanguage] = useState('en')
  const [numberPad, setNumberPad] = useState(2)
  const [safe, setSafe] = useState(true)
  const [tidy, setTidy] = useState(true)           // nur lose Objekte einsammeln

  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState('Ready.')
  const [error, setError] = useState('')

  const [report, setReport] = useState(null)
  const [detectInfo, setDetectInfo] = useState(null)
  const [naming, setNaming] = useState(null)
  const [structure, setStructure] = useState(null)
  const [layers, setLayers] = useState(null)
  const [translation, setTranslation] = useState(null)
  const [accepted, setAccepted] = useState(() => new Set())  // guids fuers Rename
  const [rules, setRules] = useState(null)
  const [previewing, setPreviewing] = useState(false)
  const [exported, setExported] = useState('')
  const [history, setHistory] = useState([])
  const [presets, setPresets] = useState([])
  const [activePreset, setActivePreset] = useState(null)

  const settings = useCallback(() => ({
    casing,
    language: language === 'none' ? null : language,
    number_pad: numberPad,
    selection: scope,
    safe,
    tidy,
  }), [casing, language, numberPad, scope, safe, tidy])

  async function run(label, fn) {
    setBusy(true); setError(''); setStatus(label + ' …')
    try {
      const r = await fn()
      setStatus(label + ' ✓')
      return r
    } catch (e) {
      setError(String(e.message || e)); setStatus(label + ' ✗')
    } finally {
      setBusy(false)
    }
  }

  const doAnalyze = useCallback(() => run('Analysis', async () => {
    const r = await call('analyze'); setReport(r.report)
    call('history').then((h) => setHistory(h.history || [])).catch(() => {})
  }), [])

  const doDetect = () => run('Detect', async () => {
    const r = await call('detect'); const d = r.detect
    setCasing(d.style); setLanguage(d.language || 'en'); setNumberPad(d.number_pad)
    setDetectInfo(d)
    setStatus(`Detected: ${d.style} / ${d.language} / pad ${d.number_pad} (${Math.round(d.confidence * 100)}%)`)
  })

  const doExportJson = () => run('Export JSON', async () => {
    const r = await call('export'); setReport(r.report)
    setExported(r.export_path ? `JSON → ${r.export_path}` : '(not written)')
  })
  const doExportCsv = () => run('Export CSV', async () => {
    const r = await call('export_csv'); setReport(r.report)
    setExported(r.csv_path ? `CSV (${r.csv_rows} rows) → ${r.csv_path}` : '(not written)')
  })

  const doFocus = useCallback((guid, name) => {
    setStatus(`Focusing ${name || ''}…`)
    call('focus', { guid })
      .then((r) => setStatus(r.ok ? `Focused ${name || ''} ✓` : 'Object not found'))
      .catch((e) => { setError(String(e.message || e)); setStatus('Focus ✗') })
  }, [])

  const doDeleteMaterial = useCallback((name) => {
    setStatus(`Deleting ${name}…`)
    call('delete_material', { name })
      .then((r) => {
        setStatus(r.deleted ? `Deleted material “${name}” ✓ (undoable)` : `“${name}” is in use — kept`)
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Delete ✗') })
  }, [doAnalyze])

  const doDeleteAllUnused = useCallback((count) => {
    setStatus(`Deleting ${count} unused material${count === 1 ? '' : 's'}…`)
    call('delete_unused_materials')
      .then((r) => {
        setStatus(`Deleted ${r.deleted} unused material${r.deleted === 1 ? '' : 's'} ✓ (undoable)`)
        doAnalyze()
      })
      .catch((e) => { setError(String(e.message || e)); setStatus('Delete ✗') })
  }, [doAnalyze])

  const applyNaming = () => run('Apply naming', async () => {
    const r = await call('apply_naming', { settings: settings() })
    setNaming(r); doAnalyze()
  })
  const applyStructure = () => run('Apply structure', async () => {
    const r = await call('apply_structure', { settings: settings() })
    setStructure(r); doAnalyze()
  })
  const applyLayers = () => run('Apply layers', async () => {
    const r = await call('apply_layers', { settings: settings() })
    setLayers(r)
  })
  const applyTranslate = () => run('Apply translations', async () => {
    const guids = Array.from(accepted)
    const r = await call('apply_translate', { settings: settings(), guids })
    setStatus(`Translated ${r.applied} names ✓ (undoable)`)
    doAnalyze()
    // Vorschau neu laden -> die eben umbenannten fallen raus
    const p = await call('plan_translate', { settings: settings() })
    setTranslation(p); setAccepted(new Set((p.diff || []).map((d) => d.guid)))
  })

  // Auto-Analyse beim ersten Laden.
  useEffect(() => { doAnalyze() }, [doAnalyze])

  // Analyse-Historie + Presets laden, sobald der Misc-Tab aktiv wird.
  useEffect(() => {
    if (tab !== 'misc') return
    call('history').then((r) => setHistory(r.history || [])).catch(() => {})
    call('presets').then((r) => { setPresets(r.presets || []); setActivePreset(r.active || null) }).catch(() => {})
  }, [tab, report])

  const applyPreset = (id) => run('Apply preset', async () => {
    const r = await call('apply_preset', { id })
    setActivePreset(r.applied || id)
    setRules(null)  // Rules-Tab neu laden lassen
    setStatus(`Preset “${r.applied || id}” applied (${r.groups} groups) — open Rules to see it.`)
  })

  // Live-Preview: Naming automatisch neu berechnen (debounced), sobald die
  // Konvention oder der Scope sich aendern und der Tab aktiv ist.
  useEffect(() => {
    if (tab !== 'naming') return
    let cancel = false
    setPreviewing(true)
    const t = setTimeout(async () => {
      try {
        const r = await call('plan_naming', { settings: settings() })
        if (!cancel) { setNaming(r); setError('') }
      } catch (e) {
        if (!cancel) setError(String(e.message || e))
      } finally {
        if (!cancel) setPreviewing(false)
      }
    }, 350)
    return () => { cancel = true; clearTimeout(t) }
  }, [tab, casing, language, numberPad, scope, settings])

  // Live-Preview: Structure.
  useEffect(() => {
    if (tab !== 'structure') return
    let cancel = false
    setPreviewing(true)
    const t = setTimeout(async () => {
      try {
        const [r, rl] = await Promise.all([
          call('plan_structure', { settings: settings() }),
          rules ? Promise.resolve(null) : call('rules'),
        ])
        if (!cancel) { setStructure(r); if (rl) setRules(rl); setError('') }
      } catch (e) {
        if (!cancel) setError(String(e.message || e))
      } finally {
        if (!cancel) setPreviewing(false)
      }
    }, 350)
    return () => { cancel = true; clearTimeout(t) }
  }, [tab, safe, scope, settings, rules])

  // Live-Preview: Translate. Standard: alle Vorschlaege angehakt.
  useEffect(() => {
    if (tab !== 'translate') return
    let cancel = false
    setPreviewing(true)
    const t = setTimeout(async () => {
      try {
        const r = await call('plan_translate', { settings: settings() })
        if (!cancel) {
          setTranslation(r)
          setAccepted(new Set((r.diff || []).map((d) => d.guid)))
          setError('')
        }
      } catch (e) {
        if (!cancel) setError(String(e.message || e))
      } finally {
        if (!cancel) setPreviewing(false)
      }
    }, 300)
    return () => { cancel = true; clearTimeout(t) }
  }, [tab, scope, settings])

  // Live-Preview: Layers.
  useEffect(() => {
    if (tab !== 'layers') return
    let cancel = false
    setPreviewing(true)
    const t = setTimeout(async () => {
      try {
        const r = await call('plan_layers', { settings: settings() })
        if (!cancel) { setLayers(r); setError('') }
      } catch (e) {
        if (!cancel) setError(String(e.message || e))
      } finally {
        if (!cancel) setPreviewing(false)
      }
    }, 300)
    return () => { cancel = true; clearTimeout(t) }
  }, [tab, scope, settings])

  const compliance = report ? Math.round(report.structure_compliance * 100) : null

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand"><span className="brand-mark">◆</span> Scene Organizer</div>

        {report && (
          <div className="scene-meta">
            <span className="scene-name">{report.file || '(scene)'}</span>
            <span className="sep">·</span>{report.object_count} objects
            <span className="sep">·</span>
            <span className={'compliance ' + (compliance >= 80 ? 'good' : compliance >= 50 ? 'mid' : 'low')}>
              {compliance}% structured
            </span>
            {report.analyzed_at && (
              <><span className="sep">·</span>
              <span className="dim" title={'Analyzed ' + report.analyzed_at}>
                {report.analyzed_at.slice(11, 16)}
              </span></>
            )}
          </div>
        )}

        <div className="topbar-right">
          <ScopeToggle scope={scope} setScope={setScope} />
          <span className={'dot ' + (busy || previewing ? 'busy' : error ? 'err' : 'ok')} />
          <span className="status" title={error || status}>{error ? 'error' : status}</span>
        </div>
      </header>

      <nav className="tabs">
        {TABS.map(([id, label]) => (
          <button key={id} className={'tab' + (tab === id ? ' on' : '')} onClick={() => setTab(id)}>
            {label}
            {id === 'naming' && naming?.count > 0 && <span className="badge">{naming.count}</span>}
            {id === 'structure' && structure?.count > 0 && <span className="badge">{structure.count}</span>}
          </button>
        ))}
      </nav>

      {error && tab !== 'rules' && <div className="error">{error}</div>}

      {tab === 'overview' && (
        <Overview
          report={report} detectInfo={detectInfo} compliance={compliance}
          busy={busy} onAnalyze={doAnalyze} onDetect={doDetect} onFocus={doFocus}
          onBrowseAll={() => setTab('assets')} onDeleteMaterial={doDeleteMaterial}
          onDeleteAllUnused={doDeleteAllUnused} history={history}
        />
      )}

      {tab === 'assets' && (
        report
          ? <AssetBrowser nodes={report.nodes || []} onFocus={doFocus} />
          : <div className="empty-state"><p>No scene analyzed yet.</p>
              <button onClick={doAnalyze} disabled={busy}>Analyze scene</button></div>
      )}

      {tab === 'misc' && (
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
                  <button className="sm" onClick={() => applyPreset(p.id)} disabled={busy}>Apply</button>
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
              <button onClick={doExportJson} disabled={busy}>Export as JSON</button>
              <button onClick={doExportCsv} disabled={busy}>Export as CSV</button>
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
      )}

      {tab === 'naming' && (
        <div className="workbench">
          <aside className="wb-side">
            <h3>Convention</h3>
            <label>Casing
              <select value={casing} onChange={(e) => setCasing(e.target.value)}>
                {CASINGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            <label>Language
              <select value={language} onChange={(e) => setLanguage(e.target.value)}>
                {LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </label>
            <label>Numbering <b>{numberPad === 0 ? 'no padding' : numberPad + '-digit'}</b>
              <input type="range" min="0" max="4" value={numberPad}
                onChange={(e) => setNumberPad(Number(e.target.value))} />
            </label>
            <div className="example">e.g. <code>{exampleName(casing, numberPad)}</code></div>
            <button className="ghost" onClick={doDetect} disabled={busy}>Detect from scene</button>
          </aside>

          <Workbench
            title="Rename preview" count={naming?.count ?? 0} loading={previewing}
            empty="Every name already matches this convention."
            applyLabel="Apply naming" onApply={applyNaming} busy={busy}
            note={naming?.applied != null ? `${naming.applied} applied (undoable).` : null}
          >
            <table className="diff"><tbody>
              {(naming?.diff || []).slice(0, 300).map((d, i) => (
                <tr key={i}><td className="dim">{d.old}</td><td className="arrow">→</td><td>{d.new}</td></tr>
              ))}
            </tbody></table>
          </Workbench>
        </div>
      )}

      {tab === 'translate' && (() => {
        const rows = translation?.diff || []
        const allOn = rows.length > 0 && rows.every((d) => accepted.has(d.guid))
        const toggle = (guid) => setAccepted((s) => {
          const n = new Set(s); n.has(guid) ? n.delete(guid) : n.add(guid); return n
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
              applyLabel="Rename selected" onApply={applyTranslate} busy={busy}
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
      })()}

      {tab === 'structure' && (
        <div className="workbench">
          <aside className="wb-side">
            <h3>Options</h3>
            <label className="check">
              <input type="checkbox" checked={tidy} onChange={(e) => setTidy(e.target.checked)} />
              Tidy mode
            </label>
            <p className="hint-sm">
              Only collects <b>loose</b> objects into their group. Objects already
              inside a (even nested) group are left untouched — your hierarchy is
              never flattened. Turn off for aggressive flat regrouping.
            </p>
            <label className="check">
              <input type="checkbox" checked={safe} onChange={(e) => setSafe(e.target.checked)} />
              Safety filter
            </label>
            <p className="hint-sm">Protects generator children (Cloner, Boole, Sweep …) from being moved.</p>
            {!tidy && <p className="wb-note" style={{ padding: '8px 0' }}>⚠ Aggressive mode can pull objects out of existing groups and flatten spatial nesting.</p>}

            <h3>Target groups</h3>
            {rules?.groups?.length
              ? <ul className="grouplist">
                  {rules.groups.map((g) => <li key={g.name}><b>{g.name}</b><span>{g.priority}</span></li>)}
                </ul>
              : <p className="hint-sm">No rules yet.</p>}
            <button className="ghost" onClick={() => setTab('rules')}>Edit rules →</button>
          </aside>

          <Workbench
            title="Regroup preview" count={structure?.count ?? 0} loading={previewing}
            empty="Everything is already in the right place."
            applyLabel="Apply structure" onApply={applyStructure} busy={busy}
            note={
              structure?.applied != null ? `${structure.applied} moved (undoable).`
                : structure?.skipped > 0 ? `${structure.skipped} protected by the safety filter.` : null
            }
          >
            <table className="diff"><tbody>
              {(structure?.diff || []).slice(0, 300).map((d, i) => (
                <tr key={i}>
                  <td>{d.name}</td><td className="dim">{d.from || '(root)'}</td>
                  <td className="arrow">→</td><td>{d.to}</td>
                </tr>
              ))}
            </tbody></table>
          </Workbench>
        </div>
      )}

      {tab === 'layers' && (
        <div className="workbench">
          <aside className="wb-side">
            <h3>Layer tagging</h3>
            <p className="hint-sm">
              Assigns objects to C4D <b>layers</b> by type — the right axis for
              “toggle/render everything of one kind”. This never moves objects, so
              your spatial null hierarchy stays exactly as is.
            </p>
            <h3>Scheme</h3>
            <ul className="grouplist">
              <li><b>Lights</b><span>all lights</span></li>
              <li><b>Cameras</b><span>all cameras</span></li>
              <li><b>Proxies</b><span>instances</span></li>
            </ul>
            {layers?.by_layer && (
              <>
                <h3>This scene</h3>
                <ul className="grouplist">
                  {Object.entries(layers.by_layer).map(([k, v]) => (
                    <li key={k}><b>{k}</b><span>{v}</span></li>
                  ))}
                </ul>
              </>
            )}
          </aside>

          <Workbench
            title="Layer assignment preview" count={layers?.count ?? 0} loading={previewing}
            empty="No taggable objects (lights / cameras / instances) found."
            applyLabel="Apply layers" onApply={applyLayers} busy={busy}
            note={layers?.applied != null ? `${layers.applied} objects tagged (undoable).` : null}
          >
            <table className="diff"><tbody>
              {(layers?.diff || []).slice(0, 300).map((d, i) => (
                <tr key={i}><td>{d.name}</td><td className="arrow">→</td><td className="dim">layer: {d.layer}</td></tr>
              ))}
            </tbody></table>
          </Workbench>
        </div>
      )}

      {tab === 'rules' && <RuleGraph />}
    </div>
  )
}

// ---------------------------------------------------------------------------

// Durchsuchbarer, facettierter, sortierbarer Asset-Browser mit Batching.
function AssetBrowser({ nodes, onFocus }) {
  const [query, setQuery] = useState('')
  const [cats, setCats] = useState(() => new Set())   // aktive Kategorie-Facetten
  const [onlyGeo, setOnlyGeo] = useState(true)
  const [sortKey, setSortKey] = useState('polygons')
  const [sortDir, setSortDir] = useState('desc')
  const [limit, setLimit] = useState(40)

  const toggleCat = (c) => setCats((s) => {
    const n = new Set(s); n.has(c) ? n.delete(c) : n.add(c); return n
  })
  const setSort = (k) => {
    if (k === sortKey) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    else { setSortKey(k); setSortDir(k === 'name' ? 'asc' : 'desc') }
  }

  // Facetten-Zaehlung: nach Suche + onlyGeo, aber VOR Kategorie-Filter.
  const q = query.trim().toLowerCase()
  const preFiltered = React.useMemo(() => nodes.filter((n) =>
    (!q || n.name.toLowerCase().includes(q) || n.type.toLowerCase().includes(q)) &&
    (!onlyGeo || n.polygons > 0)
  ), [nodes, q, onlyGeo])

  const catCounts = React.useMemo(() => {
    const m = {}
    preFiltered.forEach((n) => { m[n.category] = (m[n.category] || 0) + 1 })
    return m
  }, [preFiltered])

  const filtered = React.useMemo(() => {
    const rows = cats.size ? preFiltered.filter((n) => cats.has(n.category)) : preFiltered
    const dir = sortDir === 'asc' ? 1 : -1
    const sorted = [...rows].sort((a, b) => {
      if (sortKey === 'name') return dir * a.name.localeCompare(b.name)
      return dir * ((a[sortKey] || 0) - (b[sortKey] || 0))
    })
    return sorted
  }, [preFiltered, cats, sortKey, sortDir])

  // Batch bei Filter-/Sortwechsel zuruecksetzen.
  useEffect(() => { setLimit(40) }, [q, onlyGeo, sortKey, sortDir, cats])

  const shown = filtered.slice(0, limit)
  const th = (k, label, cls) => (
    <th className={(cls || '') + (sortKey === k ? ' sorted' : '')} onClick={() => setSort(k)}>
      {label}{sortKey === k && <span className="caret">{sortDir === 'desc' ? '▾' : '▴'}</span>}
    </th>
  )

  return (
    <div className="assets">
      <div className="asset-controls">
        <input className="search" placeholder="Search name or type…" value={query}
          onChange={(e) => setQuery(e.target.value)} />
        <label className="check inline">
          <input type="checkbox" checked={onlyGeo} onChange={(e) => setOnlyGeo(e.target.checked)} />
          only geometry
        </label>
        <label className="sortsel">Sort
          <select value={sortKey} onChange={(e) => setSort(e.target.value)}>
            {SORTS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
        </label>
      </div>

      <div className="facets">
        {CAT_ORDER.filter((c) => catCounts[c]).map((c) => (
          <button key={c} className={'facet' + (cats.has(c) ? ' on' : '')} onClick={() => toggleCat(c)}
            style={cats.has(c) ? { borderColor: catColor(c), color: catColor(c) } : undefined}>
            <span className="facet-dot" style={{ background: catColor(c) }} />
            {c}<b>{catCounts[c]}</b>
          </button>
        ))}
        {cats.size > 0 && <button className="facet clear" onClick={() => setCats(new Set())}>clear</button>}
      </div>

      <div className="asset-count">
        showing {Math.min(limit, filtered.length)} of {filtered.length}
        {filtered.length !== nodes.length && <span className="dim"> · {nodes.length} total</span>}
      </div>

      <div className="asset-table-wrap">
        <table className="asset-table">
          <thead><tr>
            <th className="l">Name</th>
            <th>Type</th>
            {th('polygons', 'Polygons', 'r')}
            {th('points', 'Points', 'r')}
            {th('children', 'Children', 'r')}
          </tr></thead>
          <tbody>
            {shown.map((n) => (
              <tr key={n.guid} className="asset-row" onClick={() => onFocus?.(n.guid, n.name)}
                title="Select & frame in viewport">
                <td className="l">
                  <span className="cat-dot" style={{ background: catColor(n.category) }} />
                  {n.name}
                </td>
                <td className="dim">{n.type}</td>
                <td className="r">{humanNum(n.polygons)}</td>
                <td className="r">{humanNum(n.points)}</td>
                <td className="r dim">{n.children || ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {!filtered.length && <div className="wb-empty">No objects match.</div>}
      </div>

      {limit < filtered.length && (
        <div className="asset-more">
          <button className="ghost" onClick={() => setLimit((l) => l + 60)}>
            Load more ({filtered.length - limit} left)
          </button>
        </div>
      )}
    </div>
  )
}

// Kompakte, klickbare Objekt-Tabelle (gleicher Stil wie der Assets-Tab).
function AssetTable({ rows, onFocus, empty }) {
  if (!rows.length) return <div className="fl-empty">{empty || 'None.'}</div>
  return (
    <div className="asset-table-wrap flat">
      <table className="asset-table"><tbody>
        {rows.map((n, i) => (
          <tr key={n.guid ?? i} className="asset-row" onClick={() => onFocus?.(n.guid, n.name)}
            title="Select & frame in viewport">
            <td className="l">
              {n.category && <span className="cat-dot" style={{ background: catColor(n.category) }} />}
              {n.name}
            </td>
            <td className="dim">{n.type}</td>
            <td className="r">{humanNum(n.polygons)}</td>
          </tr>
        ))}
      </tbody></table>
    </div>
  )
}

// Cleanup-Accordion: kompakte Liste von Problem-Gruppen, eine offen.
function Cleanup({ buckets, onFocus }) {
  const [open, setOpen] = useState(() => (buckets.find((b) => b.items.length) || {}).key || null)
  return (
    <div className="cleanup">
      {buckets.map((b) => {
        const isOpen = open === b.key
        return (
          <div className={'cl-bucket' + (isOpen ? ' open' : '')} key={b.key}>
            <button className="cl-head" onClick={() => setOpen(isOpen ? null : b.key)}>
              <span className="cl-caret">{isOpen ? '▾' : '▸'}</span>
              <span className="cl-label">{b.label}</span>
              <span className={'cl-count' + (b.items.length ? ' warn' : '')}>{b.items.length}</span>
            </button>
            {isOpen && (b.items.length
              ? <div className="cl-items">
                  {b.items.slice(0, 40).map((it, i) => (
                    <button key={i} className="cl-item" onClick={() => onFocus?.(it.guid, it.name)}
                      title="Select & frame in viewport">
                      <span className="fl-name">{it.name}</span>
                      {it.meta && <span className="fl-meta">{it.meta}</span>}
                    </button>
                  ))}
                  {b.items.length > 40 && <div className="fl-more">+{b.items.length - 40} more</div>}
                </div>
              : <div className="cl-clean">Clean 🎉</div>)}
          </div>
        )
      })}
    </div>
  )
}

function Overview({ report, detectInfo, compliance, busy, onAnalyze, onDetect, onFocus, onBrowseAll, onDeleteMaterial, onDeleteAllUnused, history }) {
  // ALLE Hooks VOR jedem early return -> sonst Rules-of-Hooks-Verletzung
  // ("Rendered more hooks than during the previous render") = Blackscreen.
  const [bulkConfirm, setBulkConfirm] = useState(false)
  const hyg = React.useMemo(
    () => computeHygiene(report?.nodes || [], report?.total_polys || 0),
    [report])
  if (!report) {
    return (
      <div className="empty-state">
        <p>No scene loaded yet.</p>
        <button onClick={onAnalyze} disabled={busy}>Analyze scene</button>
      </div>
    )
  }
  const tone = compliance >= 80 ? 'good' : compliance >= 50 ? 'mid' : 'low'
  const misplaced = report.misplaced?.length || 0
  const nameTone = hyg.namingScore >= 80 ? 'good' : hyg.namingScore >= 50 ? 'mid' : 'low'
  const buckets = [
    { key: 'default', label: 'Default names', items: hyg.defaults.map((n) => ({ guid: n.guid, name: n.name, meta: n.type })) },
    { key: 'dupes', label: 'Duplicate names', items: hyg.dupes.map((d) => ({ guid: d.guid, name: d.name, meta: '×' + d.count })) },
    { key: 'empty', label: 'Empty groups', items: hyg.emptyGroups.map((n) => ({ guid: n.guid, name: n.name })) },
    { key: 'root', label: 'Root clutter', items: hyg.rootClutter.map((n) => ({ guid: n.guid, name: n.name, meta: n.type })) },
  ]
  const mat = report.materials
  // Trends aus der Analyse-Historie (nur diese Datei, chronologisch).
  const fh = (history || []).filter((h) => h.file === report.file).sort((a, b) => a.ts - b.ts)
  const seriesOf = (key, mul = 1) => fh.map((h) => (h[key] == null ? null : h[key] * mul)).filter((v) => v != null)
  const deltaOf = (arr) => {
    if (arr.length < 2) return null
    const p = arr[arr.length - 2]; const c = arr[arr.length - 1]
    return { pct: p ? Math.round((c - p) / p * 100) : 0, dir: Math.sign(c - p) }
  }
  const sObj = seriesOf('objects'); const sPoly = seriesOf('polys')
  const sSize = seriesOf('size'); const sComp = seriesOf('compliance', 100)
  return (
    <div className="overview">
      <div className="ov-topbar">
        <button className="ghost sm" onClick={onAnalyze} disabled={busy}>↻ Refresh analysis</button>
      </div>

      <div className="tiles">
        <Tile value={humanNum(report.object_count)} label="Objects" spark={sObj} delta={deltaOf(sObj)} />
        <Tile value={humanNum(report.total_polys)} label="Polygons" spark={sPoly} delta={deltaOf(sPoly)} />
        <Tile value={humanBytes(report.file_size)} label="Project size" spark={sSize} delta={deltaOf(sSize)} />
        <Tile value={compliance + '%'} label="Structured" tone={tone} spark={sComp} delta={deltaOf(sComp)} />
      </div>

      <div className="substats">
        <span><b>{humanNum(report.total_points)}</b> points</span>
        <span><b>{report.max_depth}</b> max depth</span>
        <span><b>{Object.keys(report.types || {}).length}</b> distinct types</span>
        <span className={misplaced ? 'warn' : ''}><b>{misplaced}</b> misplaced</span>
      </div>

      {/* Composition-Strip: Szenen-Makeup auf einen Blick */}
      <Strip data={report.categories} colorFn={(k) => catColor(k)} />

      {/* Hero: Poly-Treemap */}
      <section className="card">
        <div className="card-head">
          <h3>Geometry map — polygons by object</h3>
          <span className="dim" style={{ fontSize: 11 }}>click a tile to select &amp; frame</span>
        </div>
        <Treemap nodes={report.nodes || []} onFocus={onFocus} />
      </section>

      {/* Row 1: health + naming consistency */}
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head">
            <h3>Scene health</h3>
            <button className="ghost sm" onClick={onDetect} disabled={busy}>Detect format</button>
          </div>
          <div className="rings">
            <div className="ring-item"><Ring pct={hyg.namingScore} tone={nameTone} /><span>Naming</span></div>
            <div className="ring-item"><Ring pct={compliance} tone={tone} /><span>Structure</span></div>
          </div>
          <table className="mini"><tbody>
            <tr><td>Misplaced</td><td className={misplaced ? 'warn' : ''}>{misplaced}</td></tr>
            <tr><td>Default names</td><td className={hyg.defaults.length ? 'warn' : ''}>{hyg.defaults.length}</td></tr>
            <tr><td>Duplicate names</td><td className={hyg.dupTotal ? 'warn' : ''}>{hyg.dupTotal}</td></tr>
            <tr><td>Empty groups</td><td className={hyg.emptyGroups.length ? 'warn' : ''}>{hyg.emptyGroups.length}</td></tr>
          </tbody></table>
          {detectInfo && <p className="mini-note dim">detected: {detectInfo.style} / {String(detectInfo.language)} / pad {detectInfo.number_pad} · {Math.round(detectInfo.confidence * 100)}%</p>}
        </section>

        <section className="card">
          <div className="card-head"><h3>Naming consistency</h3></div>
          <div className="chipgroup-label">Casing</div>
          <Strip data={report.casing} />
          <div className="chipgroup-label" style={{ marginTop: 14 }}>Language</div>
          <Strip data={report.language} legendMax={3} />
        </section>
      </div>

      {/* Row 2: cleanup + materials */}
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head"><h3>Cleanup</h3></div>
          <Cleanup buckets={buckets} onFocus={onFocus} />
        </section>

        <section className="card">
          <div className="card-head">
            <h3>Materials</h3>
            {mat?.unused?.length > 0 && (
              bulkConfirm ? (
                <span className="mat-confirm">
                  delete {mat.unused.length}?
                  <button className="mat-yes" title="Confirm delete all unused"
                    onClick={() => { onDeleteAllUnused(mat.unused.length); setBulkConfirm(false) }}>✓</button>
                  <button className="mat-no" title="Cancel" onClick={() => setBulkConfirm(false)}>✕</button>
                </span>
              ) : (
                <button className="trash-btn" disabled={busy}
                  title={`Delete all ${mat.unused.length} unused materials (undoable)`}
                  onClick={() => setBulkConfirm(true)}>
                  <IconTrash /><span className="trash-count">{mat.unused.length}</span>
                </button>
              )
            )}
          </div>
          {mat ? (
            <>
              <div className="substats" style={{ marginBottom: 12 }}>
                <span><b>{mat.total}</b> total</span>
                <span className={mat.unused?.length ? 'warn' : ''}><b>{mat.unused?.length || 0}</b> unused</span>
                <span className={mat.missing_textures ? 'warn' : ''}><b>{mat.missing_textures || 0}</b> missing tex</span>
              </div>
              <div className="chipgroup-label">Unused materials</div>
              <UnusedMaterials names={mat.unused || []} onDelete={onDeleteMaterial} />
              {mat.missing?.length > 0 && (
                <>
                  <div className="chipgroup-label" style={{ marginTop: 12 }}>Missing textures</div>
                  <div className="focuslist">
                    {mat.missing.slice(0, 10).map((t, i) => (
                      <div className="fl-row static" key={i}>
                        <span className="fl-dot" style={{ background: 'var(--err)' }} />
                        <span className="fl-name">{t.material}</span>
                        <span className="fl-meta dim">{t.file}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          ) : <div className="fl-empty">No material data.</div>}
        </section>
      </div>

      {/* Row 3: heaviest assets (half width) + concentration */}
      <div className="ov-cols2">
        <section className="card">
          <div className="card-head">
            <h3>Heaviest assets</h3>
            <button className="ghost sm" onClick={onBrowseAll}>Browse all →</button>
          </div>
          <AssetTable rows={(report.largest || []).slice(0, 8)} onFocus={onFocus}
            empty="No geometry found in the scene." />
        </section>

        <section className="card">
          <div className="card-head"><h3>Polygon concentration</h3></div>
          <table className="mini"><tbody>
            <tr><td>Total polygons</td><td>{humanNum(report.total_polys)}</td></tr>
            <tr><td>Top 10 objects</td><td>{hyg.top10pct}%</td></tr>
            <tr><td>Objects for 80%</td><td>{hyg.p80}</td></tr>
            <tr><td>Heavy outliers (&gt;5%)</td><td className={hyg.outliers.length ? 'warn' : ''}>{hyg.outliers.length}</td></tr>
          </tbody></table>
          {hyg.outliers.length > 0 && (
            <AssetTable rows={hyg.outliers.slice(0, 5)} onFocus={onFocus} />
          )}
        </section>
      </div>
    </div>
  )
}
