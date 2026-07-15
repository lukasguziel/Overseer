// E2E coverage for the Overview area (tabs/OverviewTab.tsx). Every interactive
// element is exercised: the two treemaps (geometry + textures) and their
// expand overlays, the heaviest-maps rows, the health sub-score rings, the
// card action buttons, plus one empty and one not-found negative state. Each
// test wires a fresh mockApi() and asserts BOTH the fired API op/payload and a
// visible UI reaction. Nothing reaches a real Cinema 4D server.
import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mockApi, type ApiLog } from './mock'
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore - plain-JS fixture module without type declarations
import * as fx from './fixtures.mjs'

// Boot the app behind the mock, wait until the report rendered, then land on
// the Overview explicitly (it is the boot tab, but the click keeps intent
// clear and matches the pattern the other area specs follow).
async function boot(page: Page, overrides = {}): Promise<ApiLog> {
  const api = await mockApi(page, overrides)
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Overview' }).first().click()
  await expect(page.locator('.overview')).toBeVisible()
  return api
}

const geoCard = (page: Page) =>
  page.locator('section.card', { has: page.getByRole('heading', { name: /Geometry map/ }) })
const texCard = (page: Page) =>
  page.locator('section.card', { has: page.getByRole('heading', { name: /Texture map/ }) })
const budgetCard = (page: Page) =>
  page.locator('section.card', { has: page.getByRole('heading', { name: /Texture budget/ }) })

test('renders the Overview dashboard with all cards', async ({ page }) => {
  await boot(page)
  await expect(page.locator('.scene-name')).toHaveText('penthouse_loft_final.c4d')
  for (const h of ['Geometry map — polygons by object', 'Texture map — image sizes',
    'Naming consistency', 'Materials & textures', 'Polygon concentration', 'Texture budget']) {
    await expect(page.getByRole('heading', { name: h })).toBeVisible()
  }
  // Health tile + one sub-score ring per scored area (Naming/Translate/Layers/
  // Materials/Tags/Files).
  await expect(page.locator('.health-tile')).toBeVisible()
  await expect(page.locator('button.hs')).toHaveCount(6)
  // Materials summary reads the report's material totals.
  await expect(page.locator('section.card', {
    has: page.getByRole('heading', { name: 'Materials & textures' }),
  }).locator('table.mini')).toContainText('84')
})

test('a geometry treemap tile focuses its object', async ({ page }) => {
  const api = await boot(page)
  await geoCard(page).locator('.tm-cell').first().click()
  await expect.poll(() => api.count('focus')).toBeGreaterThan(0)
  // Payload carries the clicked object's guid (a number from the scene tree).
  expect(typeof api.find('focus')?.body.guid).toBe('number')
  await expect(page.locator('.statusbar-text')).toContainText('Focus')
})

test('a texture treemap tile focuses its material', async ({ page }) => {
  // The focus_material response drives the status line — override it so the
  // rendered outcome names the framed object.
  const api = await boot(page, {
    focus_material: (body: Record<string, unknown>) => ({ ok: true, object: 'CoffeeTable', name: body.name }),
  })
  await texCard(page).locator('.tm-cell').first().click()
  await expect.poll(() => api.count('focus_material')).toBeGreaterThan(0)
  expect(typeof api.find('focus_material')?.body.name).toBe('string')
  await expect(page.locator('.statusbar-text')).toContainText('framed “CoffeeTable”')
})

test('a heaviest-maps row focuses its material', async ({ page }) => {
  const api = await boot(page)
  const row = budgetCard(page).locator('.tb-row').first()
  await expect(row).toBeVisible()
  const file = (await row.locator('.fl-name').textContent())?.trim()
  expect(file).toBeTruthy()
  await row.click()
  await expect.poll(() => api.count('focus_material')).toBeGreaterThan(0)
  expect(typeof api.find('focus_material')?.body.name).toBe('string')
  await expect(page.locator('.statusbar-text')).toContainText('Selected')
})

test('the geometry map expands to an overlay and closes via the ✕', async ({ page }) => {
  await boot(page)
  await geoCard(page).locator('.expand-btn[title="Expand"]').click()
  const overlay = page.locator('.zoom-overlay')
  await expect(overlay).toBeVisible()
  await expect(overlay.locator('.zoom-head h3')).toHaveText('Geometry map — polygons by object')
  await overlay.locator('.expand-btn[title="Close"]').click()
  await expect(overlay).toHaveCount(0)
})

test('the texture map expands to an overlay and closes via the backdrop', async ({ page }) => {
  await boot(page)
  await texCard(page).locator('.expand-btn[title="Expand"]').click()
  const overlay = page.locator('.zoom-overlay')
  await expect(overlay).toBeVisible()
  await expect(overlay.locator('.zoom-head h3')).toHaveText('Texture map — image sizes')
  // Clicking the backdrop (top-left corner, outside the centered box) closes it.
  await page.mouse.click(3, 3)
  await expect(overlay).toHaveCount(0)
})

test('the health sub-score rings navigate to their area', async ({ page }) => {
  await boot(page)
  const areas = ['Naming', 'Translate', 'Layers', 'Materials', 'Tags', 'Files']
  for (const label of areas) {
    await page.locator('button.hs', { hasText: label }).click()
    await expect(page.locator('nav.tabs button.tab.on')).toContainText(label)
    // Return to the Overview for the next sub-score.
    await page.locator('nav.tabs button.tab', { hasText: 'Overview' }).first().click()
    await expect(page.locator('.overview')).toBeVisible()
  }
})

test('the card action buttons navigate to their tab', async ({ page }) => {
  await boot(page)
  const targets: [string, string][] = [
    ['Manage', 'Materials'],
    ['Browse all', 'Assets'],
    ['Inspect', 'Materials'],
  ]
  for (const [button, tab] of targets) {
    await page.locator('button.act', { hasText: button }).click()
    await expect(page.locator('nav.tabs button.tab.on')).toContainText(tab)
    await page.locator('nav.tabs button.tab', { hasText: 'Overview' }).first().click()
    await expect(page.locator('.overview')).toBeVisible()
  }
})

test('an empty texture set renders the empty note', async ({ page }) => {
  // Drive the area's data op (analyze) with a report that references no
  // texture pixels — both texture cards must fall back to the empty note.
  await boot(page, {
    analyze: () => ({ ok: true, report: { ...fx.report, textures: { ...fx.report.textures, absolute: [], relative: [] } } }),
  })
  await expect(budgetCard(page).locator('.empty-note')).toContainText('No texture pixel data')
  await expect(texCard(page)).toContainText('No texture pixel data')
})

test('a not-found focus surfaces the miss in the status line', async ({ page }) => {
  const api = await boot(page, { focus: { ok: false } })
  await geoCard(page).locator('.tm-cell').first().click()
  await expect.poll(() => api.count('focus')).toBeGreaterThan(0)
  await expect(page.locator('.statusbar-text')).toContainText('Object not found')
})
