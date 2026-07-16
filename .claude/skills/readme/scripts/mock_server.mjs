// Serves the built web UI (src/web) plus a mocked /api/* answered from
// fixtures.mjs — the full frontend runs against the sample scene without
// Cinema 4D. Used by shoot.mjs for README screenshots.
//
//   node .claude/skills/readme/scripts/mock_server.mjs [port]
import http from 'node:http'
import { readFile } from 'node:fs/promises'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'
import * as fx from './fixtures.mjs'

const ROOT = join(fileURLToPath(new URL('.', import.meta.url)),
  '..', '..', '..', '..', 'src', 'web')
const PORT = Number(process.argv[2] || 8899)

const MIME = {
  '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
  '.svg': 'image/svg+xml', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.woff2': 'font/woff2', '.json': 'application/json', '.ico': 'image/x-icon',
}

const API = {
  analyze: () => ({ ok: true, report: fx.report }),
  export: () => ({ ok: true, report: fx.report, export_path: 'D:/3D/PROJECTS/PENTHOUSE/scene_report.json' }),
  history: () => fx.history,
  changes: () => fx.changes,
  detect: () => fx.detect,
  progress: () => ({ active: false, phase: '', current: 0, total: 0, detail: '' }),
  dirty: () => ({ ok: true, dirty: fx.report.dirty, name: fx.report.doc_name,
    sel: 0, sel_count: 0, sel_names: [] }),
  plan_naming: () => fx.planNaming,
  plan_translate: () => fx.planTranslate,
  plan_layers: () => fx.planLayers,
  config: () => ({ ok: true, config: {}, defaults: {} }),
  // Audit areas + misc endpoints the newer tabs call.
  tags_scan: () => fx.tagsScan,
  gens_scan: () => fx.gensScan,
  files_scan: () => fx.filesScan,
  sims_scan: () => fx.simsScan,
  type_icons: () => ({ ok: true, icons: {} }),
  material_previews: () => ({ ok: true, previews: {} }),
  texture_previews: () => ({ ok: true, previews: {} }),
  ui_settings_get: () => ({ ok: true, found: false, ui: {} }),
  ui_settings_set: () => ({ ok: true }),
}

const server = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://localhost')
  if (url.pathname.startsWith('/api/')) {
    const op = url.pathname.slice(5)
    const handler = API[op] || (() => ({ ok: true, applied: 0, count: 0 }))
    const body = JSON.stringify(handler())
    res.writeHead(200, { 'Content-Type': 'application/json' })
    res.end(body)
    return
  }
  let file = normalize(url.pathname).replace(/^([/\\])+/, '')
  if (!file || file === '.') file = 'index.html'
  try {
    const data = await readFile(join(ROOT, file))
    res.writeHead(200, { 'Content-Type': MIME[extname(file)] || 'application/octet-stream' })
    res.end(data)
  } catch {
    res.writeHead(404)
    res.end('not found')
  }
})

server.listen(PORT, () => {
  console.log(`mock UI at http://127.0.0.1:${PORT}  (web root: ${ROOT})`)
})
