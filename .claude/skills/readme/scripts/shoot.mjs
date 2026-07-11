// Screenshots every tab of the web UI (served by mock_server.mjs) into
// docs/screenshots/. Uses the system Chrome/Edge via playwright-core —
// no browser download.
//
//   node .claude/skills/readme/scripts/mock_server.mjs 8899   (background)
//   node .claude/skills/readme/scripts/shoot.mjs [port]
import { mkdir } from 'node:fs/promises'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createRequire } from 'node:module'

const require = createRequire(
  join(fileURLToPath(new URL('.', import.meta.url)),
    '..', '..', '..', '..', 'frontend', 'package.json'))
const { chromium } = require('playwright-core')

const PORT = Number(process.argv[2] || 8899)
const OUT = join(fileURLToPath(new URL('.', import.meta.url)),
  '..', '..', '..', '..', 'docs', 'screenshots')

// [tab nav label, output file, prepare?]; Structure/Rules are parked
// ("soon") -> skipped. `prepare` runs after the tab is opened, before the
// shot — e.g. the Translate tab demonstrates English -> French, which needs
// the Google engine selected (offline only offers EN/DE targets).
const TABS = [
  ['Overview', 'overview.png'],
  ['Naming', 'naming.png'],
  ['Translate', 'translate.png', async (page) => {
    const side = page.locator('.wb-side select')
    await side.nth(1).selectOption('google')   // engine first: unlocks fr
    await side.nth(0).selectOption('fr')
    await page.waitForTimeout(800)
  }],
  ['Layers', 'layers.png'],
  ['Materials', 'materials.png'],
  ['Tags', 'tags.png'],
  ['Files', 'files.png'],
  ['Assets', 'assets.png'],
  ['Generators', 'generators.png'],
  ['Sims', 'sims.png'],
  ['Misc', 'misc.png'],
]

async function launch() {
  for (const channel of ['chrome', 'msedge']) {
    try {
      return await chromium.launch({ channel })
    } catch { /* try the next channel */ }
  }
  throw new Error('no system Chrome/Edge found (playwright-core channels)')
}

const browser = await launch()
const page = await browser.newPage({
  viewport: { width: 1440, height: 960 },
  deviceScaleFactor: 2,
})
await mkdir(OUT, { recursive: true })

await page.goto(`http://127.0.0.1:${PORT}/`, { waitUntil: 'networkidle' })
await page.waitForSelector('.tabs', { timeout: 15000 })
// First analyze + auto preview need a beat (350 ms debounce + fetch).
await page.waitForTimeout(1200)

for (const [label, file, prepare] of TABS) {
  await page.click(`.tabs button:has-text("${label}")`)
  // Park the cursor off the nav, else the tab's progress tooltip hovers open
  // and covers the header in the shot.
  await page.mouse.move(1400, 940)
  await page.waitForTimeout(1200)
  if (prepare) await prepare(page)
  await page.mouse.move(1400, 940)
  await page.waitForTimeout(400)
  // Hide the transient status toast so shots stay deterministic.
  await page.addStyleTag({ content: '.statusbar { display: none !important; }' })
  await page.screenshot({ path: join(OUT, file) })
  console.log('shot', file)
}

await browser.close()
console.log('done ->', OUT)
