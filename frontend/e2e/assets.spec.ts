// E2E coverage for the "Assets" area (frontend/src/tabs/AssetsTab.tsx): the
// searchable/faceted/sortable object browser plus the multi-select batch
// actions (assign to layer / move to group). Every interaction asserts BOTH
// the API op + payload (via the mock call log) and a visible UI reaction.
import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mockApi } from './mock'
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore - plain-JS fixture module without type declarations
import * as fx from './fixtures.mjs'

type Responder = Record<string, unknown> | ((body: Record<string, unknown>) => Record<string, unknown>)

// Boot the app, wait for the report to land, then open the Assets tab.
async function openAssets(page: Page, overrides: Record<string, Responder> = {}) {
  const api = await mockApi(page, overrides)
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Assets' }).first().click()
  await expect(page.locator('.workbench.assets')).toBeVisible()
  return api
}

const rows = (page: Page) => page.locator('tr.asset-row')

test('opens with the object list, head-count and pager', async ({ page }) => {
  await openAssets(page)
  // Default view: only-geometry on, sorted by polygons desc → 46 mesh objects,
  // paged at 25/page.
  await expect(page.locator('.wb-preview-head .head-count')).toContainText('46 objects')
  await expect(rows(page)).toHaveCount(25)
  await expect(page.locator('.pager-info')).toContainText('1–25 of 46')
  // Highest-poly mesh sorts to the top of the first page.
  await expect(rows(page).first()).toContainText('Sofa_Body_Hi')
})

test('search narrows the list by name', async ({ page }) => {
  await openAssets(page)
  await page.locator('input.search').fill('sofa')
  await expect(rows(page)).toHaveCount(3)
  await expect(page.locator('.head-count')).toContainText('3 objects')
  await expect(rows(page).first()).toContainText('Sofa_Body_Hi')
  // A term that only matches non-geometry stays empty while "Only geometry" is on.
  await page.locator('input.search').fill('nonsense-xyz')
  await expect(page.locator('.empty-note')).toHaveText('No objects match.')
  await expect(rows(page)).toHaveCount(0)
})

test('"Only geometry" toggle reveals non-geometry objects', async ({ page }) => {
  await openAssets(page)
  // Cameras carry no polygons, so with geometry-only on a "Cam_" search is empty.
  await page.locator('input.search').fill('Cam_')
  await expect(page.locator('.empty-note')).toHaveText('No objects match.')
  // Turn off the geometry filter → the three cameras appear.
  await page.locator('label.check', { hasText: 'Only geometry' }).locator('input').uncheck()
  await expect(rows(page)).toHaveCount(3)
  await expect(page.locator('.head-count')).toContainText('3 objects')
})

test('"No layer" toggle drops objects that already sit on a layer', async ({ page }) => {
  await openAssets(page)
  await page.locator('label.check', { hasText: 'Only geometry' }).locator('input').uncheck()
  await page.locator('input.search').fill('Cam_')
  await expect(rows(page)).toHaveCount(3) // Cam_Hero, Cam_Detail_Kitchen, Cam_Wide
  // Cam_Hero / Cam_Detail_Kitchen sit on the "Cameras" layer; only Cam_Wide is loose.
  await page.locator('label.check', { hasText: 'No layer' }).locator('input').check()
  await expect(rows(page)).toHaveCount(1)
  await expect(rows(page).first()).toContainText('Cam_Wide')
})

test('column-header and sidebar sorting flip the order', async ({ page }) => {
  await openAssets(page)
  // Default sort column is Polygons, descending.
  await expect(page.locator('th.sorted')).toContainText('Polygons')
  await expect(page.locator('th.sorted .caret')).toHaveText('▾')
  // Click the Polygons header → ascending, lowest-poly mesh floats to the top.
  await page.locator('th', { hasText: 'Polygons' }).click()
  await expect(page.locator('th.sorted .caret')).toHaveText('▴')
  // The sidebar direction button flips it back to descending.
  await page.locator('button.sortdir').click()
  await expect(page.locator('th.sorted .caret')).toHaveText('▾')
  // Switching the sort key via the select moves the "sorted" marker off the
  // numeric columns (Name is not a sortable header).
  await page.locator('.sortsel select').selectOption('name')
  await expect(page.locator('th.sorted')).toHaveCount(0)
})

test('category facet filters the list and clears again', async ({ page }) => {
  await openAssets(page)
  // Reveal every category by dropping the geometry-only filter.
  await page.locator('label.check', { hasText: 'Only geometry' }).locator('input').uncheck()
  const before = await rows(page).count()
  await page.locator('.facets button.facet', { hasText: 'camera' }).click()
  await expect(page.locator('.head-count')).toContainText('3 objects') // 3 cameras
  await expect(rows(page)).toHaveCount(3)
  // The Category "Clear" button restores the full list.
  await page.locator('.section-head', { hasText: 'Category' }).locator('button', { hasText: 'Clear' }).click()
  await expect(rows(page)).not.toHaveCount(3)
  expect(await rows(page).count()).toBeGreaterThan(before - 1)
})

test('type facet filters down to a single object type', async ({ page }) => {
  await openAssets(page)
  await page.locator('label.check', { hasText: 'Only geometry' }).locator('input').uncheck()
  // The type list is collapsed by default.
  await expect(page.locator('.type-facets')).toHaveCount(0)
  await page.locator('button.facet-more', { hasText: 'Filter by type' }).click()
  await expect(page.locator('.type-facets')).toBeVisible()
  await page.locator('.type-facets button.facet', { hasText: 'Camera' }).click()
  await expect(rows(page)).toHaveCount(3)
  await expect(page.locator('.head-count')).toContainText('3 objects')
  // Toggling the button again hides the type chips.
  await page.locator('button.facet-more', { hasText: 'Hide types' }).click()
  await expect(page.locator('.type-facets')).toHaveCount(0)
})

test('clicking a row fires the focus op and reports it', async ({ page }) => {
  const api = await openAssets(page)
  await rows(page).filter({ hasText: 'Sofa_Body_Hi' }).locator('td.l').click()
  await expect.poll(() => api.count('focus')).toBe(1)
  expect(typeof api.find('focus')?.body.guid).toBe('number')
  await expect(page.locator('.statusbar-text')).toContainText('Focused Sofa_Body_Hi')
})

test('row checkbox and select-all drive the batch bar', async ({ page }) => {
  const api = await openAssets(page)
  // No batch bar until something is selected.
  await expect(page.locator('.asset-batch')).toHaveCount(0)
  await rows(page).filter({ hasText: 'Sofa_Body_Hi' }).locator('input[type=checkbox]').check()
  await expect(page.locator('.asset-batch b').first()).toHaveText('1 selected')
  // Ticking a checkbox must NOT also focus the row (the cell stops propagation).
  expect(api.count('focus')).toBe(0)
  // Select-all header box selects every visible row (25 on page 1).
  await page.locator('thead input[type=checkbox]').check()
  await expect(page.locator('.asset-batch b').first()).toHaveText('25 selected')
})

test('batch "Assign layer" posts assign_layer and clears the selection', async ({ page }) => {
  const api = await openAssets(page, { assign_layer: { ok: true, applied: 1 } })
  await rows(page).filter({ hasText: 'Sofa_Body_Hi' }).locator('input[type=checkbox]').check()
  const batch = page.locator('.asset-batch')
  await batch.locator('input[list="so-layer-names"]').fill('Lights')
  await batch.locator('button', { hasText: 'Assign layer' }).click()
  await expect.poll(() => api.find('assign_layer')?.body).toBeTruthy()
  const body = api.find('assign_layer')!.body as { guids: number[]; layer: string }
  expect(body.layer).toBe('Lights')
  expect(body.guids).toHaveLength(1)
  // Selection cleared → batch bar gone, and the status reports the outcome.
  await expect(page.locator('.asset-batch')).toHaveCount(0)
  await expect(page.locator('.statusbar-text')).toContainText('layer “Lights”')
})

test('batch "Move to group" posts move_to_group and clears the selection', async ({ page }) => {
  const api = await openAssets(page, { move_to_group: { ok: true, applied: 1 } })
  await rows(page).filter({ hasText: 'Sofa_Body_Hi' }).locator('input[type=checkbox]').check()
  const batch = page.locator('.asset-batch')
  await batch.locator('input[list="so-group-names"]').fill('Furniture')
  await batch.locator('button', { hasText: 'Move to group' }).click()
  await expect.poll(() => api.find('move_to_group')?.body).toBeTruthy()
  const body = api.find('move_to_group')!.body as { guids: number[]; group: string }
  expect(body.group).toBe('Furniture')
  expect(body.guids).toHaveLength(1)
  await expect(page.locator('.asset-batch')).toHaveCount(0)
  await expect(page.locator('.statusbar-text')).toContainText('group “Furniture”')
})

test('"Clear selection" dismisses the batch bar without a call', async ({ page }) => {
  const api = await openAssets(page)
  await rows(page).filter({ hasText: 'Sofa_Body_Hi' }).locator('input[type=checkbox]').check()
  await expect(page.locator('.asset-batch')).toBeVisible()
  await page.locator('.asset-batch button', { hasText: 'Clear selection' }).click()
  await expect(page.locator('.asset-batch')).toHaveCount(0)
  expect(api.count('assign_layer')).toBe(0)
  expect(api.count('move_to_group')).toBe(0)
})

test('the pager walks to the next page', async ({ page }) => {
  await openAssets(page)
  await expect(page.locator('.pager-info')).toContainText('1–25 of 46')
  await page.locator('button.pager-btn[title="Next page"]').click()
  await expect(page.locator('.pager-info')).toContainText('26–46 of 46')
  await expect(rows(page)).toHaveCount(21)
})

test('empty scene renders the empty-state note', async ({ page }) => {
  // Override the area's data op (analyze feeds the node list) with a scene
  // that has no objects.
  await openAssets(page, { analyze: () => ({ ok: true, report: { ...fx.report, nodes: [] } }) })
  await expect(page.locator('.wb-preview.wb-empty')).toBeVisible()
  await expect(page.locator('.empty-note')).toHaveText('No objects match.')
  await expect(rows(page)).toHaveCount(0)
  await expect(page.locator('.head-count')).toContainText('0 objects')
})
