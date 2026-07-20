// The one mock layer every e2e spec goes through: mockApi(page) intercepts
// ALL /api/* requests inside the browser (nothing ever reaches a real
// Cinema 4D server, even for ops this table does not know) and answers them
// from the fake scene in fixtures.mjs. It returns a call log so a test can
// assert that a click fired the right op with the right payload.
//
//   const api = await mockApi(page, { collect_textures: { ok: true, copied: 1, relinked: 4, skipped: 0, diag: [] } })
//   await page.goto('/')
//   ...click...
//   expect(api.find('collect_textures')?.body).toMatchObject({ subdir: 'tex' })
//
// Overrides are per-op: a plain value replaces the default response, a
// function receives the request body and returns the response (stateful
// mocks). Specs put their area-specific fake data HERE via overrides —
// never by editing fixtures.mjs, which all areas share.
import type { Page } from '@playwright/test'
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore - plain-JS fixture module without type declarations
import * as fx from './fixtures.mjs'

export interface ApiCall {
  op: string
  body: Record<string, unknown>
}

export interface ApiLog {
  calls: ApiCall[]
  find: (op: string) => ApiCall | undefined
  all: (op: string) => ApiCall[]
  count: (op: string) => number
  clear: () => void
}

type Responder = Record<string, unknown> | ((body: Record<string, unknown>) => Record<string, unknown>)

// Mirror of the readme skill's mock_server.mjs API table: everything the UI
// requests on boot plus the per-tab scans. Ops not listed here fall back to
// a generic { ok: true } so unknown clicks never hang the UI.
const DEFAULTS: Record<string, Responder> = {
  analyze: () => ({ ok: true, report: fx.report }),
  export: () => ({ ok: true, report: fx.report, export_path: 'D:/3D/PROJECTS/PENTHOUSE/scene_report.json' }),
  history: () => fx.history,
  changes: () => fx.changes,
  detect: () => fx.detect,
  progress: () => ({ active: false, phase: '', current: 0, total: 0, detail: '' }),
  dirty: () => ({ ok: true, dirty: fx.report.dirty, name: fx.report.doc_name, sel: 0, sel_count: 0, sel_names: [] }),
  plan_naming: () => fx.planNaming,
  plan_translate: () => fx.planTranslate,
  plan_layers: () => fx.planLayers,
  config: () => ({ ok: true, config: {}, defaults: {} }),
  tags_scan: () => fx.tagsScan,
  gens_scan: () => fx.gensScan,
  files_scan: () => fx.filesScan,
  sims_scan: () => fx.simsScan,
  type_icons: () => ({ ok: true, icons: {} }),
  material_previews: () => ({ ok: true, previews: {} }),
  texture_previews: () => ({ ok: true, previews: {} }),
  texture_owners: () => ({ ok: true, materials: ['Parquet_Oak', 'Floor_Trim'] }),
  ui_settings_get: () => ({ ok: true, found: false, ui: {} }),
  ui_settings_set: () => ({ ok: true }),
  ui_global_get: () => ({ ok: true, ui: {} }),
  ui_global_set: () => ({ ok: true }),
}

const GENERIC = { ok: true, applied: 0, count: 0 }

export async function mockApi(
  page: Page,
  overrides: Record<string, Responder> = {},
): Promise<ApiLog> {
  const calls: ApiCall[] = []
  await page.route('**/api/**', async (route) => {
    const url = new URL(route.request().url())
    const op = url.pathname.replace(/^.*\/api\//, '')
    let body: Record<string, unknown> = {}
    try { body = route.request().postDataJSON() ?? {} } catch { body = {} }
    // The permanent /api/progress heartbeat would drown the log — keep the
    // log to the calls a test actually asserts on.
    if (op !== 'progress') calls.push({ op, body })
    const responder = overrides[op] ?? DEFAULTS[op] ?? GENERIC
    const data = typeof responder === 'function' ? responder(body) : responder
    await route.fulfill({ json: data })
  })
  return {
    calls,
    find: (op) => calls.find((c) => c.op === op),
    all: (op) => calls.filter((c) => c.op === op),
    count: (op) => calls.filter((c) => c.op === op).length,
    clear: () => { calls.length = 0 },
  }
}

// Boot the app on the given tab and wait until the report rendered (the tab
// nav is enabled once the boot analysis is in). Most specs start with this.
export async function openTab(page: Page, label: string): Promise<void> {
  await page.goto('/')
  const tab = page.locator('nav.tabs button', { hasText: label })
  await tab.click()
}
