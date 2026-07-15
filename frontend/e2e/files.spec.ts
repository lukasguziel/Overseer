// E2E coverage for the "Files" area (external references: Alembic/sim caches,
// IES, volume caches …). Every interactive element is exercised and asserted
// on BOTH sides: the API op + payload via the mock call log, and a visible UI
// reaction. Follows the shell.spec.ts pattern — mockApi() fresh per test,
// goto('/'), navigate to the tab, act, assert.
import { test, expect, type Page } from '@playwright/test'
import { mockApi, type ApiLog } from './mock'

// Boot the app and open the Files tab; resolves once the tab's sidebar is up.
async function openFiles(page: Page): Promise<void> {
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Files' }).first().click()
  await expect(page.locator('.wb-side')).toBeVisible()
}

// A minimal files scan carrying one relocatable Alembic path — the only shape
// that enables the "Make relative" action (the shared fixture has none).
const RELOC_SCAN = {
  ok: true,
  doc_path: 'D:/3D/PROJECTS/PENTHOUSE',
  accepted: [],
  entries: [
    {
      kind: 'alembic', file: 'curtain_sim.abc',
      path: 'D:/3D/PROJECTS/PENTHOUSE/caches/curtain_sim.abc',
      resolved: 'D:/3D/PROJECTS/PENTHOUSE/caches/curtain_sim.abc',
      exists: true, missing: false, absolute: true, relocatable: true,
      rel_target: 'caches/curtain_sim.abc', bytes: 4 * 1024 * 1024,
      owner: 'Curtain_left', guid: 5,
    },
  ],
  summary: {
    total: 1, by_kind: { alembic: 1 }, missing_count: 0,
    absolute_count: 1, relocatable_count: 1, total_bytes: 4 * 1024 * 1024,
  },
}

const EMPTY_SCAN = {
  ok: true, doc_path: 'D:/3D/PROJECTS/PENTHOUSE', accepted: [], entries: [],
  summary: {
    total: 0, by_kind: {}, missing_count: 0, absolute_count: 0,
    relocatable_count: 0, total_bytes: 0,
  },
}

const missingCount = (page: Page) => page.locator('.head-count.hc-todo')
const referencedCard = (page: Page) =>
  page.locator('.card').filter({ hasText: 'Referenced files' })
const missingCard = (page: Page) =>
  page.locator('.card').filter({ hasText: 'Missing files' })
const modal = (page: Page) => page.locator('.confirm-box')

test('renders the scan summary, both file lists and a disabled Make relative', async ({ page }) => {
  const api = await mockApi(page)
  await openFiles(page)

  // (b) UI: sidebar sub-stats reflect the fixture (5 files, 3.5 GB, 2 missing).
  const stats = page.locator('.substats')
  await expect(stats).toContainText('5')
  await expect(stats).toContainText('3.5 GB')
  await expect(stats).toContainText('2 missing')

  // Both cards render with the right counts (2 missing, 3 referenced).
  await expect(missingCount(page)).toHaveText('2 missing')
  await expect(referencedCard(page).locator('.head-count')).toHaveText('3 files')

  // The shared fixture has no relocatable Alembic path, so the action is off.
  const makeRel = page.getByRole('button', { name: 'Make relative (0)' })
  await expect(makeRel).toBeDisabled()

  // (a) API: the area's data op fired.
  expect(api.count('files_scan')).toBeGreaterThan(0)
})

test('kind chips narrow both lists', async ({ page }) => {
  await mockApi(page)
  await openFiles(page)

  // Alembic: 2 present (curtain, blanket) + 1 missing (plant).
  await page.locator('.chip-btn', { hasText: 'Alembic' }).click()
  await expect(missingCount(page)).toHaveText('1 missing')
  await expect(referencedCard(page).locator('.head-count')).toHaveText('2 files')

  // IES: one present entry, none missing → the whole Missing card disappears.
  await page.locator('.chip-btn', { hasText: 'IES' }).click()
  await expect(missingCard(page)).toHaveCount(0)
  await expect(referencedCard(page).locator('.head-count')).toHaveText('1 files')

  // Clicking the active chip again clears the filter (back to everything).
  await page.locator('.chip-btn.on', { hasText: 'IES' }).click()
  await expect(referencedCard(page).locator('.head-count')).toHaveText('3 files')
})

test('the search box filters file / path / owner', async ({ page }) => {
  await mockApi(page)
  await openFiles(page)
  const search = page.locator('input.search')

  // "plant" hits only the missing plant cache → 1 missing, no referenced match.
  await search.fill('plant')
  await expect(missingCount(page)).toHaveText('1 missing')
  await expect(referencedCard(page)).toContainText('No external files match the search.')

  // "curtain" hits a present cache → missing card gone, 1 referenced file.
  await search.fill('curtain')
  await expect(missingCard(page)).toHaveCount(0)
  await expect(referencedCard(page).locator('.head-count')).toHaveText('1 files')

  // Clearing restores the full lists.
  await search.fill('')
  await expect(referencedCard(page).locator('.head-count')).toHaveText('3 files')
})

test('clicking a referenced row focuses its object in C4D', async ({ page }) => {
  const api = await mockApi(page, { focus: { ok: true } })
  await openFiles(page)

  await referencedCard(page).locator('.dg-tr', { hasText: 'curtain_sim_v04.abc' }).click()

  // (a) API: focus fired with the row's guid.
  await expect.poll(() => api.find('focus')).toBeTruthy()
  expect(typeof api.find('focus')?.body.guid).toBe('number')
  // (b) UI: the transient status names the focused owner.
  await expect(page.locator('.statusbar-text')).toContainText('Focused')
})

test('per-row grey check accepts a single missing file as-is', async ({ page }) => {
  const api = await mockApi(page, { set_keeps: { ok: true } })
  await openFiles(page)

  // First missing row is the plant cache; its grey ✓ accepts it as missing.
  await missingCard(page).locator('.rn-keep').first().click()

  // (a) API: set_keeps for the files section, adding the plant path to the
  // already-accepted list from the fixture.
  await expect.poll(() => api.find('set_keeps')).toBeTruthy()
  const body = api.find('set_keeps')!.body as { section: string; keys: string[] }
  expect(body.section).toBe('files')
  expect(body.keys).toContain('Q:/SCANS/plants/plant_scan_hero.abc')
  expect(body.keys).toContain('Q:/OLD_LIB/city_bg.abc')
  // (b) UI: the sidebar note confirms the accept.
  await expect(page.locator('.example')).toContainText('plant_scan_hero.abc')
  await expect(page.locator('.example')).toContainText('as missing')
})

test('per-row folder icon picks a replacement file', async ({ page }) => {
  const api = await mockApi(page, { files_pick_path: { ok: true, picked: 'D:/NEW/plant.abc' } })
  await openFiles(page)

  await missingCard(page).locator('.rn-ok').first().click()

  // (a) API: files_pick_path for the row's stored path.
  await expect.poll(() => api.find('files_pick_path')).toBeTruthy()
  expect(api.find('files_pick_path')?.body).toMatchObject({
    path: 'Q:/SCANS/plants/plant_scan_hero.abc',
  })
  // (b) UI: the note reports the new reference.
  await expect(page.locator('.example')).toContainText('D:/NEW/plant.abc')
})

test('a cancelled file picker is reported without a rewrite', async ({ page }) => {
  const api = await mockApi(page, { files_pick_path: { ok: true, cancelled: true } })
  await openFiles(page)

  await missingCard(page).locator('.rn-ok').first().click()

  await expect.poll(() => api.find('files_pick_path')).toBeTruthy()
  await expect(page.locator('.example')).toContainText('File picker cancelled.')
})

test('Select in C4D selects every object with a missing file', async ({ page }) => {
  const api = await mockApi(page, { files_select: { ok: true, selected: 1 } })
  await openFiles(page)

  await page.getByRole('button', { name: 'Select in C4D' }).click()

  // (a) API: files_select with the guids of missing-file owners (the plant;
  // the ownerless smoke cache has no guid and is left out).
  await expect.poll(() => api.find('files_select')).toBeTruthy()
  const guids = api.find('files_select')!.body.guids as number[]
  expect(Array.isArray(guids)).toBe(true)
  expect(guids).toHaveLength(1)
  // (b) UI: the note confirms the selection.
  await expect(page.locator('.example')).toContainText('Selected 1 object')
})

test('Accept all — cancel does nothing, confirm accepts every missing file', async ({ page }) => {
  const api = await mockApi(page, { set_keeps: { ok: true } })
  await openFiles(page)

  // Open, then cancel: no keep is written.
  await page.getByRole('button', { name: 'Accept 2' }).click()
  await expect(modal(page)).toContainText('Accept all as missing')
  await modal(page).locator('button.ghost').click()
  await expect(modal(page)).toHaveCount(0)
  expect(api.count('set_keeps')).toBe(0)

  // Reopen and confirm: both missing paths (plus the pre-accepted one) persist.
  await page.getByRole('button', { name: 'Accept 2' }).click()
  await modal(page).locator('button.apply').click()
  await expect(modal(page)).toHaveCount(0)

  await expect.poll(() => api.find('set_keeps')).toBeTruthy()
  const body = api.find('set_keeps')!.body as { section: string; keys: string[] }
  expect(body.section).toBe('files')
  expect(body.keys).toEqual(expect.arrayContaining([
    'Q:/OLD_LIB/city_bg.abc',
    'Q:/SCANS/plants/plant_scan_hero.abc',
    'C:/Users/artist/Desktop/fireplace_smoke.vdb',
  ]))
})

test('Relink — picks a folder, cancel aborts, confirm relinks', async ({ page }) => {
  const api = await mockApi(page, {
    pick_folder: { ok: true, path: 'D:/SEARCH' },
    files_relink: { ok: true, relinked: 2, not_found: 0 },
  })
  await openFiles(page)

  // Click Relink → folder picker → confirm dialog. Cancel it: no relink runs.
  await page.getByRole('button', { name: 'Relink 2' }).click()
  await expect(modal(page)).toContainText('Relink missing files')
  await expect.poll(() => api.find('pick_folder')).toBeTruthy()
  await modal(page).locator('button.ghost').click()
  await expect(modal(page)).toHaveCount(0)
  expect(api.count('files_relink')).toBe(0)

  // Reopen and confirm: files_relink runs with the picked folder.
  await page.getByRole('button', { name: 'Relink 2' }).click()
  await modal(page).locator('button.apply').click()
  await expect(modal(page)).toHaveCount(0)

  await expect.poll(() => api.find('files_relink')).toBeTruthy()
  expect(api.find('files_relink')?.body).toMatchObject({ folder: 'D:/SEARCH' })
  // (b) UI: the note reports the relink outcome.
  await expect(page.locator('.example')).toContainText('Relinked 2 files')
})

test('Make relative — enabled by a relocatable path, cancel + confirm', async ({ page }) => {
  const api = await mockApi(page, {
    files_scan: RELOC_SCAN,
    files_make_relative: { ok: true, fixed: 1, skipped: 0 },
  })
  await openFiles(page)

  const makeRel = page.getByRole('button', { name: 'Make relative (1)' })
  await expect(makeRel).toBeEnabled()

  // Open then cancel: nothing is rewritten.
  await makeRel.click()
  await expect(modal(page)).toContainText('Make paths relative')
  await modal(page).locator('button.ghost').click()
  await expect(modal(page)).toHaveCount(0)
  expect(api.count('files_make_relative')).toBe(0)

  // Reopen and confirm.
  await makeRel.click()
  await modal(page).locator('button.apply').click()
  await expect(modal(page)).toHaveCount(0)

  await expect.poll(() => api.find('files_make_relative')).toBeTruthy()
  await expect(page.locator('.example')).toContainText('Rewrote 1 path')
})

test('the Accepted panel lists a kept file and restores it', async ({ page }) => {
  const api = await mockApi(page, { set_keeps: { ok: true } })
  await openFiles(page)

  // The fixture pre-accepts one file → the panel renders with a 1-item toggle.
  const toggle = page.locator('.kept-toggle')
  await expect(toggle).toContainText('1 accepted item')
  await toggle.click()

  // (b) UI: the accepted path is listed under "External files".
  const group = page.locator('.kept-group', { hasText: 'External files' })
  await expect(group).toContainText('Q:/OLD_LIB/city_bg.abc')

  // Restoring it writes an emptied files keep list.
  await group.getByRole('button', { name: 'Restore all' }).click()
  await expect.poll(() => api.find('set_keeps')).toBeTruthy()
  expect(api.find('set_keeps')?.body).toMatchObject({ section: 'files', keys: [] })
})

test('empty scan shows the "no external files" placeholder', async ({ page }) => {
  await mockApi(page, { files_scan: EMPTY_SCAN })
  await openFiles(page)

  await expect(page.locator('.substats')).toContainText('0')
  await expect(missingCard(page)).toHaveCount(0)
  await expect(referencedCard(page)).toContainText('No external files')
  await expect(page.getByRole('button', { name: 'Make relative (0)' })).toBeDisabled()
})

test('a failing scan shows the error state and retries', async ({ page }) => {
  const api = await mockApi(page, { files_scan: { error: 'scan boom' } })
  // A failing scan renders the EmptyState instead of the sidebar, so navigate
  // directly rather than via openFiles (which waits for .wb-side).
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Files' }).first().click()

  // (b) UI: the EmptyState surfaces the failure with a Retry action.
  await expect(page.locator('.empty-state')).toContainText('Files scan failed: scan boom')
  const before = api.count('files_scan')
  await page.getByRole('button', { name: 'Retry' }).click()
  // (a) API: Retry re-issues the scan.
  await expect.poll(() => api.count('files_scan')).toBeGreaterThan(before)
})
