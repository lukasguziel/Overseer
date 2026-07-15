// E2E coverage for the "Layers" area of the Overseer web UI. Every test wires
// a fresh mockApi() (so nothing reaches a real Cinema 4D server), boots the app
// and drives one area interaction — asserting BOTH the API op + payload via the
// call log AND a visible UI reaction (modal state, row content, status toast).
import { test, expect } from '@playwright/test'
import { mockApi } from './mock'
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore - plain-JS fixture module without type declarations
import { report as fxReport } from './fixtures.mjs'

// guid of a fixture node by name — lets the assertions pin the exact object a
// click acted on without hard-coding preorder indices.
const guidOf = (name: string): number =>
  (fxReport.nodes as { name: string; guid: number }[]).find((n) => n.name === name)!.guid

async function openLayers(page: import('@playwright/test').Page): Promise<void> {
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Layers' }).first().click()
  await expect(page.locator('.layers-tab')).toBeVisible()
}

test('layers tab renders the overview and the no-layer worklist', async ({ page }) => {
  await mockApi(page)
  await openLayers(page)
  // Layer overview: 3 layers, 1 of them empty (Proxies).
  const head = page.locator('.ly-overview .head-count')
  await expect(head).toContainText('3 layers')
  await expect(head).toContainText('1 empty')
  // The three fixture layers show up in the tree.
  await expect(page.locator('.ly-name', { hasText: 'Lights' })).toBeVisible()
  await expect(page.locator('.ly-name', { hasText: 'Cameras' })).toBeVisible()
  await expect(page.locator('.ly-name', { hasText: 'Proxies' })).toBeVisible()
  // No-layer worklist has rows (loose objects + null groups without a layer).
  await expect(page.locator('.wb-preview-head h3', { hasText: 'No layer' })).toBeVisible()
  await expect(page.locator('.rename-list .rename-row').first()).toBeVisible()
})

test('delete-empty-layers modal confirms and fires delete_empty_layers', async ({ page }) => {
  const api = await mockApi(page, { delete_empty_layers: { ok: true, deleted: 1 } })
  await openLayers(page)
  await page.getByRole('button', { name: 'Delete 1 empty' }).click()
  // Danger confirm modal opens.
  const modal = page.locator('.confirm-box')
  await expect(modal).toBeVisible()
  await expect(modal.locator('.confirm-title')).toHaveText('Delete empty layers')
  await modal.getByRole('button', { name: '✕ Delete 1' }).click()
  await expect.poll(() => api.count('delete_empty_layers')).toBe(1)
  // Empty keep list -> the op is sent with an empty body (nothing to preserve).
  expect(api.find('delete_empty_layers')?.body).toEqual({})
  await expect(page.locator('.confirm-box')).toHaveCount(0)
})

test('delete-empty-layers modal cancels without a call', async ({ page }) => {
  const api = await mockApi(page)
  await openLayers(page)
  await page.getByRole('button', { name: 'Delete 1 empty' }).click()
  await expect(page.locator('.confirm-box')).toBeVisible()
  await page.locator('.confirm-box').getByRole('button', { name: 'Cancel' }).click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('delete_empty_layers')).toBe(0)
})

test('deleting a single empty layer from the tree fires delete_layer', async ({ page }) => {
  const api = await mockApi(page, { delete_layer: { ok: true, deleted: true } })
  await openLayers(page)
  // The empty Proxies layer carries the inline trash button.
  await page.getByTitle('Delete this empty layer (undoable)').click()
  await expect.poll(() => api.count('delete_layer')).toBe(1)
  expect(api.find('delete_layer')?.body).toMatchObject({ name: 'Proxies' })
  await expect(page.locator('.statusbar-text')).toContainText('deleted')
})

test('accepting an empty layer fires set_keeps and hides the delete button', async ({ page }) => {
  const api = await mockApi(page)
  await openLayers(page)
  await expect(page.getByRole('button', { name: 'Delete 1 empty' })).toBeVisible()
  await page.getByTitle('Accept as-is — keep this empty layer (restore below)').click()
  await expect.poll(() => api.count('set_keeps')).toBeGreaterThan(0)
  expect(api.find('set_keeps')?.body).toMatchObject({ section: 'layers', keys: ['Proxies'] })
  // Nothing empty is open any more -> the danger button disappears, and the
  // accepted-as-is panel now lists the kept layer.
  await expect(page.getByRole('button', { name: 'Delete 1 empty' })).toHaveCount(0)
  await expect(page.locator('.kept-toggle', { hasText: 'accepted item' })).toBeVisible()
})

test('expanding a layer and clicking an object focuses it in Cinema 4D', async ({ page }) => {
  const api = await mockApi(page)
  await openLayers(page)
  // Expand the Lights layer to reveal its objects.
  await page.locator('.ly-group', { hasText: 'Lights' }).locator('.ly-head').click()
  const obj = page.locator('.fl-row', { hasText: 'LGT_Key_Window' })
  await expect(obj).toBeVisible()
  await obj.click()
  await expect.poll(() => api.count('focus')).toBe(1)
  expect(api.find('focus')?.body).toMatchObject({ guid: guidOf('LGT_Key_Window') })
})

test('the color gradient editor applies via set_layer_colors', async ({ page }) => {
  const api = await mockApi(page, { set_layer_colors: { ok: true, applied: 3 } })
  await openLayers(page)
  await page.getByRole('button', { name: 'Edit gradient' }).click()
  // Editing hint + the two edit-mode buttons appear.
  await expect(page.locator('.lg-block .hint-sm')).toBeVisible()
  await page.getByRole('button', { name: 'Set gradient' }).click()
  await expect.poll(() => api.count('set_layer_colors')).toBe(1)
  const body = api.find('set_layer_colors')?.body as { colors: { name: string }[] }
  expect(body.colors).toHaveLength(3)
  // Overview order: non-empty layers first (Lights, Cameras), then empty (Proxies).
  expect(body.colors[0].name).toBe('Lights')
  expect(body.colors.map((c) => c.name)).toEqual(['Lights', 'Cameras', 'Proxies'])
  // Back out of edit mode.
  await expect(page.getByRole('button', { name: 'Edit gradient' })).toBeVisible()
})

test('cancelling the gradient editor makes no call', async ({ page }) => {
  const api = await mockApi(page)
  await openLayers(page)
  await page.getByRole('button', { name: 'Edit gradient' }).click()
  await page.locator('.lg-block').getByRole('button', { name: 'Cancel' }).click()
  await expect(page.getByRole('button', { name: 'Edit gradient' })).toBeVisible()
  expect(api.count('set_layer_colors')).toBe(0)
})

test('batch "Assign all" confirms and fires assign_layer for every object', async ({ page }) => {
  const api = await mockApi(page, { assign_layer: { ok: true, applied: 42 } })
  await openLayers(page)
  await page.getByPlaceholder('layer for ALL of these…').fill('Props')
  await page.getByRole('button', { name: 'Assign all' }).click()
  const modal = page.locator('.confirm-box')
  await expect(modal).toBeVisible()
  await expect(modal.locator('.confirm-title')).toHaveText('Assign all')
  await modal.locator('.apply').click()
  await expect.poll(() => api.count('assign_layer')).toBe(1)
  const body = api.find('assign_layer')?.body as { guids: number[]; layer: string }
  expect(body.layer).toBe('Props')
  expect(body.guids.length).toBeGreaterThan(0)
  await expect(page.locator('.confirm-box')).toHaveCount(0)
})

test('batch "Assign all" can be cancelled without a call', async ({ page }) => {
  const api = await mockApi(page)
  await openLayers(page)
  await page.getByPlaceholder('layer for ALL of these…').fill('Props')
  await page.getByRole('button', { name: 'Assign all' }).click()
  await expect(page.locator('.confirm-box')).toBeVisible()
  await page.locator('.confirm-box').getByRole('button', { name: 'Cancel' }).click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('assign_layer')).toBe(0)
})

test('per-row layer picker assigns one object via assign_layer', async ({ page }) => {
  const api = await mockApi(page, { assign_layer: { ok: true, applied: 1 } })
  await openLayers(page)
  const row = page.locator('.rename-row', { hasText: 'Sofa_Body_Hi' })
  await row.locator('.nl-pick').click()
  const input = row.locator('input.nl-input')
  await expect(input).toBeVisible()
  await input.fill('Furniture')
  await input.press('Enter')
  await expect.poll(() => api.count('assign_layer')).toBe(1)
  expect(api.find('assign_layer')?.body).toMatchObject({
    guids: [guidOf('Sofa_Body_Hi')], layer: 'Furniture',
  })
  // Optimistic: the assigned row drops out of the no-layer worklist.
  await expect(page.locator('.rename-row', { hasText: 'Sofa_Body_Hi' })).toHaveCount(0)
})

test('per-row accept keeps an object without a layer', async ({ page }) => {
  const api = await mockApi(page)
  await openLayers(page)
  const row = page.locator('.rename-row', { hasText: 'CoffeeTable' })
  await row.getByTitle('Accept as-is — fine without a layer (restore below)').click()
  await expect.poll(() => api.count('set_keeps')).toBeGreaterThan(0)
  const body = api.find('set_keeps')?.body as { section: string; keys: string[] }
  expect(body.section).toBe('layers')
  expect(body.keys).toContain('CoffeeTable')
  // The accepted object leaves the worklist for good.
  await expect(page.locator('.rename-row', { hasText: 'CoffeeTable' })).toHaveCount(0)
})

test('clicking a worklist row name focuses the object', async ({ page }) => {
  const api = await mockApi(page)
  await openLayers(page)
  const row = page.locator('.rename-row', { hasText: 'Faucet' })
  await row.locator('.rn-old').click()
  await expect.poll(() => api.count('focus')).toBe(1)
  expect(api.find('focus')?.body).toMatchObject({ guid: guidOf('Faucet') })
})

test('"Keep all as-is" accepts the whole worklist and empties it', async ({ page }) => {
  const api = await mockApi(page)
  await openLayers(page)
  await page.getByRole('button', { name: 'Keep all as-is' }).click()
  const modal = page.locator('.confirm-box')
  await expect(modal).toBeVisible()
  await expect(modal.locator('.confirm-title')).toHaveText('Keep all as-is')
  await modal.locator('.apply').click()
  await expect.poll(() => api.count('set_keeps')).toBeGreaterThan(0)
  const body = api.find('set_keeps')?.body as { section: string; keys: string[] }
  expect(body.section).toBe('layers')
  expect(body.keys.length).toBeGreaterThan(1)
  // Worklist collapses to its empty state.
  await expect(page.locator('.wb-scroll .empty-note', {
    hasText: 'Every object is on a layer or accepted',
  })).toBeVisible()
})

test('ancestor suggestions drive the batch + per-row suggested assign', async ({ page }) => {
  const api = await mockApi(page, {
    plan_layer_suggestions: {
      ok: true, count: 2,
      diff: [
        { guid: guidOf('Sofa_Body_Hi'), name: 'Sofa_Body_Hi', layer: 'Lights' },
        { guid: guidOf('CoffeeTable'), name: 'CoffeeTable', layer: 'Lights' },
      ],
    },
    apply_layer_suggestions: { ok: true, applied: 2 },
    assign_layer: { ok: true, applied: 1 },
  })
  await openLayers(page)

  // --- per-row: the suggested layer's ✓ assigns exactly that layer ----------
  const row = page.locator('.rename-row', { hasText: 'Sofa_Body_Hi' })
  await expect(row.locator('.nl-pick')).toContainText('Lights')
  await row.getByTitle('Assign the suggested layer “Lights” (undoable)').click()
  await expect.poll(() => api.count('assign_layer')).toBe(1)
  expect(api.find('assign_layer')?.body).toMatchObject({
    guids: [guidOf('Sofa_Body_Hi')], layer: 'Lights',
  })

  // --- batch: "Assign N suggested" head button confirms -> apply_layer_suggestions
  await page.getByRole('button', { name: /Assign \d+ suggested/ }).click()
  const modal = page.locator('.confirm-box')
  await expect(modal).toBeVisible()
  await expect(modal.locator('.confirm-title')).toHaveText('Assign suggested layers')
  await modal.locator('.apply').click()
  await expect.poll(() => api.count('apply_layer_suggestions')).toBe(1)
  const body = api.find('apply_layer_suggestions')?.body as { guids: number[] }
  expect(body.guids.length).toBeGreaterThan(0)
  await expect(page.locator('.confirm-box')).toHaveCount(0)
})

test('mixed-layer hierarchies list focuses and accepts findings', async ({ page }) => {
  const api = await mockApi(page, {
    layer_mismatches: {
      ok: true,
      findings: [
        { guid: guidOf('Sofa_Body_Hi'), name: 'Sofa_Body_Hi', path: '/LivingRoom/Sofa_Set',
          parent: 'Sofa_Set', parent_layer: 'Cameras', child_layer: 'Lights' },
      ],
    },
  })
  await openLayers(page)
  const card = page.locator('.ly-mismatches')
  await expect(card).toBeVisible()
  await expect(card.locator('.card-head h3')).toHaveText('Mixed-layer hierarchies')

  // Row name click frames the object.
  await card.locator('.rn-old', { hasText: 'Sofa_Body_Hi' }).click()
  await expect.poll(() => api.count('focus')).toBe(1)
  expect(api.find('focus')?.body).toMatchObject({ guid: guidOf('Sofa_Body_Hi') })

  // Accepting the intentional mix persists a layers keep.
  await card.getByTitle('Accept as-is — this mix is intentional (restore below)').click()
  await expect.poll(() => api.count('set_keeps')).toBeGreaterThan(0)
  expect(api.find('set_keeps')?.body).toMatchObject({ section: 'layers', keys: ['Sofa_Body_Hi'] })
  await expect(page.locator('.kept-toggle', { hasText: 'accepted item' })).toBeVisible()
})

test('area history can revert a recorded layers run', async ({ page }) => {
  const api = await mockApi(page, { revert_change: { ok: true, reverted: 2 } })
  await openLayers(page)
  // The fixture change log carries one "layers" run — expand the area history.
  const toggle = page.locator('.kept-toggle', { hasText: 'change' })
  await expect(toggle).toBeVisible()
  await toggle.click()
  await page.getByRole('button', { name: 'revert run' }).click()
  // Inline confirm -> commit.
  await expect(page.locator('.mat-yes')).toBeVisible()
  await page.locator('.mat-yes').click()
  await expect.poll(() => api.count('revert_change')).toBe(1)
  expect(api.find('revert_change')?.body).toMatchObject({ id: '1783619000000' })
  // The inline confirm closes once the revert is dispatched.
  await expect(page.locator('.mat-yes')).toHaveCount(0)
})

test('empty scene renders the no-layers empty state', async ({ page }) => {
  const emptyReport = {
    ...fxReport,
    nodes: [],
    layers_report: { layers: [], no_layer: 0, total_layers: 0, empty_layers: 0 },
  }
  await mockApi(page, { analyze: { ok: true, report: emptyReport } })
  await openLayers(page)
  await expect(page.locator('.layertree, .empty-note', {
    hasText: 'This scene uses no layers.',
  })).toBeVisible()
  // The worklist collapses to its own empty state too.
  await expect(page.locator('.wb-scroll .empty-note', {
    hasText: 'Every object is on a layer or accepted',
  })).toBeVisible()
})
