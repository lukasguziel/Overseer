// E2E coverage for the "Misc" tab. With SHOW_MISC_SECTION off (presets +
// scene-hierarchy export are parked), the live area is:
//   - Change history card: "Clear log", expandable rows, run-level revert
//     (confirm/cancel/confirm) and per-op revert.
//   - Analysis history card: "Clear log", expandable snapshot rows.
//   - PhoneAccess card: turn LAN access on/off (netinfo) + the QR modal.
// Every interaction asserts both the fired API op/payload and a visible UI
// reaction. Each test mocks the API fresh and reloads the app.
import { test, expect, type Page } from '@playwright/test'
import { mockApi } from './mock'
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore - plain-JS fixture module without type declarations
import * as fx from './fixtures.mjs'

// Open the app and switch to the Misc tab (boot analysis must land first so
// the tab nav is live).
async function openMisc(page: Page): Promise<void> {
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Misc' }).first().click()
}

const changeCard = (page: Page) =>
  page.locator('section.card').filter({ hasText: 'Change history' })
const analysisCard = (page: Page) =>
  page.locator('section.card').filter({ hasText: 'Analysis history' })
const phoneCard = (page: Page) =>
  page.locator('section.card').filter({ hasText: 'Read the scene on your phone' })

test('renders the change and analysis history cards from the fake scene', async ({ page }) => {
  await mockApi(page)
  await openMisc(page)
  await expect(page.locator('.error')).toHaveCount(0)
  // fx.changes has 3 runs, fx.history has 3 analysis snapshots.
  await expect(changeCard(page).locator('.ch-entry')).toHaveCount(3)
  await expect(analysisCard(page).locator('.ch-entry')).toHaveCount(3)
  // Both "Clear log" buttons are present while their logs are non-empty.
  await expect(changeCard(page).getByRole('button', { name: 'Clear log' })).toBeVisible()
  await expect(analysisCard(page).getByRole('button', { name: 'Clear log' })).toBeVisible()
})

test('a change-history row expands to show the before → after diff', async ({ page }) => {
  await mockApi(page)
  await openMisc(page)
  const firstRow = changeCard(page).locator('.ch-entry').first()
  // The newest run is the "12 translated" entry (Chair01 -> Chaise01, ...).
  await expect(firstRow.locator('.ch-summary')).toContainText('12 translated')
  await firstRow.locator('.ch-toggle').click()
  await expect(firstRow.locator('table.ch-items')).toBeVisible()
  await expect(firstRow).toContainText('Chaise01')
  await expect(firstRow).toContainText('Chair01')
})

test('run-level revert: cancel fires nothing, confirm fires revert_change', async ({ page }) => {
  const api = await mockApi(page, { revert_change: { ok: true, reverted: 3 } })
  await openMisc(page)
  const firstRow = changeCard(page).locator('.ch-entry').first()

  // Open the inline confirm, then cancel it -> no API call, button restored.
  await firstRow.getByRole('button', { name: 'revert run' }).click()
  await expect(firstRow.locator('.mat-confirm')).toContainText('revert all?')
  await firstRow.locator('.mat-no').click()
  await expect(firstRow.locator('.mat-confirm')).toHaveCount(0)
  await expect(firstRow.getByRole('button', { name: 'revert run' })).toBeVisible()
  expect(api.count('revert_change')).toBe(0)

  // Confirm this time -> revert_change with just the run id (no op indices).
  const analyzeBefore = api.count('analyze')
  await firstRow.getByRole('button', { name: 'revert run' }).click()
  await firstRow.locator('.mat-yes').click()
  await expect.poll(() => api.count('revert_change')).toBe(1)
  expect(api.find('revert_change')?.body).toEqual({ id: fx.changes.changes[0].id })
  // The inline confirm closes and the revert triggers a fresh analysis.
  await expect(firstRow.locator('.mat-confirm')).toHaveCount(0)
  await expect.poll(() => api.count('analyze')).toBeGreaterThan(analyzeBefore)
})

test('per-op revert fires revert_change with the op index', async ({ page }) => {
  const api = await mockApi(page)
  await openMisc(page)
  const firstRow = changeCard(page).locator('.ch-entry').first()
  await firstRow.locator('.ch-toggle').click()
  const analyzeBefore = api.count('analyze')
  // Inside the diff table each op has its own "revert" control.
  await firstRow.locator('table.ch-items .ch-revert').first().click()
  await expect.poll(() => api.count('revert_change')).toBe(1)
  expect(api.find('revert_change')?.body).toEqual({ id: fx.changes.changes[0].id, items: [0] })
  // A per-op revert also kicks off a fresh analysis (visible downstream effect).
  await expect.poll(() => api.count('analyze')).toBeGreaterThan(analyzeBefore)
})

test('clearing the change log empties the list and hides the button', async ({ page }) => {
  // Stateful mock: changes go empty once clear_changes has fired (doClearChanges
  // re-fetches the list afterwards).
  let cleared = false
  const api = await mockApi(page, {
    changes: () => (cleared ? { ok: true, changes: [] } : fx.changes),
    clear_changes: () => { cleared = true; return { ok: true } },
  })
  await openMisc(page)
  await expect(changeCard(page).locator('.ch-entry')).toHaveCount(3)
  await changeCard(page).getByRole('button', { name: 'Clear log' }).click()
  await expect.poll(() => api.count('clear_changes')).toBe(1)
  // Empty note replaces the list; the Clear-log button is gone.
  await expect(changeCard(page).locator('.empty-note')).toHaveText('No tool changes recorded yet.')
  await expect(changeCard(page).getByRole('button', { name: 'Clear log' })).toHaveCount(0)
})

test('an analysis-history row expands to its snapshot metrics', async ({ page }) => {
  await mockApi(page)
  await openMisc(page)
  const firstRow = analysisCard(page).locator('.ch-entry').first()
  await firstRow.locator('.ch-toggle').click()
  await expect(firstRow.locator('table.ch-items')).toBeVisible()
  await expect(firstRow).toContainText('objects')
  await expect(firstRow).toContainText('polygons')
  await expect(firstRow).toContainText('size')
})

test('clearing the analysis log empties it and reports a status', async ({ page }) => {
  const api = await mockApi(page)
  await openMisc(page)
  await expect(analysisCard(page).locator('.ch-entry')).toHaveCount(3)
  await analysisCard(page).getByRole('button', { name: 'Clear log' }).click()
  await expect.poll(() => api.count('clear_history')).toBe(1)
  await expect(page.getByText('No analyses recorded yet.')).toBeVisible()
  await expect(analysisCard(page).getByRole('button', { name: 'Clear log' })).toHaveCount(0)
  await expect(page.locator('.statusbar-text')).toContainText('Analysis log cleared')
})

test('phone access off: turning it on fires netinfo with listen_lan:true', async ({ page }) => {
  const api = await mockApi(page, {
    netinfo: { lan: false, wanted: false, restart_needed: false, ip: null, port: 8787 },
  })
  await openMisc(page)
  const card = phoneCard(page)
  const turnOn = card.getByRole('button', { name: 'Turn phone access on' })
  await expect(turnOn).toBeVisible()
  await turnOn.click()
  // First call is the mount probe ({}), the click adds the opt-in.
  await expect.poll(() => api.all('netinfo').some((c) => c.body.listen_lan === true)).toBe(true)
})

test('phone access on: the QR modal opens and closes, and it can be turned off', async ({ page }) => {
  const api = await mockApi(page, {
    netinfo: () => ({ lan: true, wanted: true, restart_needed: false, ip: '192.168.1.50', port: 8787 }),
  })
  await openMisc(page)
  const card = phoneCard(page)
  const showQr = card.getByRole('button', { name: 'Show QR code' })
  await expect(showQr).toBeVisible()

  // Open the QR modal, then close it.
  await showQr.click()
  const modal = page.locator('.qr-box')
  await expect(modal).toBeVisible()
  await expect(modal).toContainText('Open on phone')
  await modal.getByRole('button', { name: 'Close' }).click()
  await expect(page.locator('.qr-box')).toHaveCount(0)

  // Turning it back off posts listen_lan:false.
  await card.getByRole('button', { name: 'Turn phone access off' }).click()
  await expect.poll(() => api.all('netinfo').some((c) => c.body.listen_lan === false)).toBe(true)
})

test('empty state: no change and no analysis history render their empty notes', async ({ page }) => {
  await mockApi(page, {
    changes: { ok: true, changes: [] },
    history: { ok: true, history: [] },
  })
  await openMisc(page)
  await expect(changeCard(page).locator('.empty-note')).toHaveText('No tool changes recorded yet.')
  await expect(page.getByText('No analyses recorded yet.')).toBeVisible()
  // With empty logs neither "Clear log" button is offered.
  await expect(changeCard(page).getByRole('button', { name: 'Clear log' })).toHaveCount(0)
  await expect(analysisCard(page).getByRole('button', { name: 'Clear log' })).toHaveCount(0)
})
