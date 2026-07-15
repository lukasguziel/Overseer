// E2E coverage for the Generators area. Every interactive element is exercised
// against the fully mocked /api/* layer (e2e/mock.ts): action buttons, the
// per-type "Select in C4D" button, the mixed-parameter value chips, the
// outliers toggle + per-row focus/apply, the int/choice "change all" controls,
// the confirm modal (open / cancel / confirm), the Viewport-cost PerfCard
// (measure + bar select + error), and the empty scan state. Each test asserts
// BOTH the API op + payload (via the call log) and a visible UI reaction.
import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mockApi } from './mock'

// perf_scan is not part of the shared fixtures (it is measured on demand), so
// the PerfCard tests supply their own fake result via an override.
const perfScan = {
  entries: [
    { guid: 5001, name: 'Sofa_Body_Hi', type: 'Subdivision Surface',
      ms: 42.5, jitter_ms: 2.1, runs: 3, share: 0.55, level: 'heavy', polygons: 4218330 },
    { guid: 5002, name: 'plant_large', type: 'Instance',
      ms: 7.8, jitter_ms: 0.4, runs: 3, share: 0.1, level: 'mid', polygons: 3411240 },
  ],
  baseline_ms: 1.0,
  summary: {
    total: 287, measured: 2, total_ms: 50.3, heavy: 1,
    slowest: 'Sofa_Body_Hi', slowest_ms: 42.5, slowest_share: 0.55,
    scene_ms: 40.0, overlap: 1.0,
  },
}

// Boot the app and land on the Generators tab with the default fixture data
// rendered (three generator-type cards).
async function openGenerators(page: Page): Promise<void> {
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Generators' }).first().click()
}

// A mixed-parameter block located by its exact label.
function param(page: Page, label: string) {
  return page.locator('.gens-param').filter({
    has: page.getByText(label, { exact: true }),
  })
}

test('boots into Generators with sidebar stats and per-type cards', async ({ page }) => {
  await mockApi(page)
  await openGenerators(page)

  // Sidebar summary (from gensScan.summary: 287 / 3 types / 3 mixed).
  const side = page.locator('.gens-side-stats')
  await expect(side).toContainText('287')
  await expect(side).toContainText('3 types')
  await expect(side).toContainText('3 mixed settings')

  // One card per audited type.
  await expect(page.locator('.gens-type')).toHaveCount(3)
  await expect(page.locator('.gens-type-title', { hasText: 'Subdivision Surface' })).toBeVisible()
  await expect(page.locator('.gens-type-title', { hasText: 'Instance' })).toBeVisible()

  // The all-uniform Extrude card advertises that no setting is mixed.
  const extrude = page.locator('.gens-type').filter({ hasText: 'Extrude' })
  await expect(extrude.locator('.gens-uniform')).toHaveText(/all settings uniform/)

  // The SDS card lists its uniform "algo" param in the quiet row (C4D label).
  const sds = page.locator('.gens-type').filter({ hasText: 'Subdivision Surface' })
  await expect(sds.locator('.gens-uniform-row')).toContainText('Catmull-Clark (N-Gons)')
})

test('"Select in C4D" fires gens_select for the whole type', async ({ page }) => {
  const api = await mockApi(page)
  await openGenerators(page)

  const sds = page.locator('.gens-type').filter({ hasText: 'Subdivision Surface' })
  await sds.locator('.gens-selall').click()

  await expect.poll(() => api.count('gens_select')).toBeGreaterThan(0)
  // The type-level select carries no param_key / value.
  expect(api.find('gens_select')?.body).toEqual({ type_key: 'sds' })
})

test('a current-value chip selects the objects with that value', async ({ page }) => {
  const api = await mockApi(page)
  await openGenerators(page)

  // editor_sub distribution: 2×41 (dominant), 1×17, 4×6. Click the "×17" chip.
  const editor = param(page, 'Editor subdivisions')
  await editor.locator('.gens-chip', { hasText: '×17' }).click()

  await expect.poll(() => api.count('gens_select')).toBeGreaterThan(0)
  expect(api.find('gens_select')?.body).toEqual({
    type_key: 'sds', param_key: 'editor_sub', value: 1,
  })
})

test('the differing toggle shows and hides the outliers list', async ({ page }) => {
  await mockApi(page)
  await openGenerators(page)

  const editor = param(page, 'Editor subdivisions')
  const outliers = editor.locator('.gens-outliers')
  await expect(outliers).toHaveCount(0)

  const toggle = editor.locator('.gens-toggle')
  await expect(toggle).toHaveText(/show the 3 differing/)
  await toggle.click()
  await expect(outliers).toBeVisible()
  // First outlier row from the fixture is Sofa_Body_Hi (had 4 → 2).
  await expect(outliers.locator('.rn-old').first()).toHaveText('Sofa_Body_Hi')

  await expect(toggle).toHaveText(/hide the 3 differing/)
  await toggle.click()
  await expect(outliers).toHaveCount(0)
})

test('an outlier row focuses in C4D and its apply opens the confirm modal', async ({ page }) => {
  const api = await mockApi(page)
  await openGenerators(page)

  const editor = param(page, 'Editor subdivisions')
  await editor.locator('.gens-toggle').click()
  const row = editor.locator('.gens-outliers .sg-row').first()

  // Row body click selects & frames the object.
  await row.locator('.sg-body').click()
  await expect.poll(() => api.count('focus')).toBeGreaterThan(0)
  expect(typeof api.find('focus')?.body.guid).toBe('number')

  // The green apply opens the confirm modal for this single object (value ->
  // the dominant 2); nothing is applied until confirmed.
  await row.locator('.rn-ok').click()
  const modal = page.locator('.confirm-box')
  await expect(modal).toBeVisible()
  await expect(modal.locator('.confirm-msg')).toContainText('Set Editor subdivisions to 2 on 1 Subdivision Surface object')
  expect(api.count('gens_apply')).toBe(0)

  await modal.locator('button.apply').click()
  await expect(modal).toHaveCount(0)
  await expect.poll(() => api.count('gens_apply')).toBe(1)
  const body = api.find('gens_apply')?.body as Record<string, unknown>
  expect(body).toMatchObject({ type_key: 'sds', param_key: 'editor_sub', value: 2 })
  expect(Array.isArray(body.guids)).toBe(true)
  expect((body.guids as unknown[]).length).toBe(1)
  // Confirming re-scans the generators.
  await expect.poll(() => api.count('gens_scan')).toBeGreaterThan(1)
})

test('"Apply to all" for an int param: change value, cancel, then confirm', async ({ page }) => {
  const api = await mockApi(page)
  await openGenerators(page)

  const editor = param(page, 'Editor subdivisions')
  await editor.locator('input.gens-num').fill('3')
  await editor.locator('button.gens-align-btn').click()

  const modal = page.locator('.confirm-box')
  await expect(modal).toBeVisible()
  await expect(modal.locator('.confirm-msg')).toContainText('Set Editor subdivisions to 3 on 64 Subdivision Surface objects')

  // Cancel: modal closes, nothing applied.
  await modal.locator('button.ghost').click()
  await expect(modal).toHaveCount(0)
  expect(api.count('gens_apply')).toBe(0)

  // Reopen and confirm.
  await editor.locator('button.gens-align-btn').click()
  await expect(modal).toBeVisible()
  await modal.locator('button.apply').click()
  await expect(modal).toHaveCount(0)

  await expect.poll(() => api.count('gens_apply')).toBe(1)
  const body = api.find('gens_apply')?.body as Record<string, unknown>
  // guids is undefined for a whole-type apply and drops out of the JSON body.
  expect(body).toEqual({ type_key: 'sds', param_key: 'editor_sub', value: 3 })
  expect('guids' in body).toBe(false)
})

test('"Apply to all" for a choice param uses the C4D label and posts the raw id', async ({ page }) => {
  const api = await mockApi(page)
  await openGenerators(page)

  // Instance / Render instance: dominant 1 ("Render Instance"); pick 0.
  const rInst = param(page, 'Render instance')
  await rInst.locator('select.gens-select').selectOption(JSON.stringify(0))
  await rInst.locator('button.gens-align-btn').click()

  const modal = page.locator('.confirm-box')
  await expect(modal).toBeVisible()
  await expect(modal.locator('.confirm-msg')).toContainText('Set Render instance to Instance on 214 Instance objects')

  await modal.locator('button.apply').click()
  await expect(modal).toHaveCount(0)
  await expect.poll(() => api.count('gens_apply')).toBe(1)
  expect(api.find('gens_apply')?.body).toEqual({
    type_key: 'instance', param_key: 'render_instance', value: 0,
  })
})

test('PerfCard measures viewport cost and a bar selects the object', async ({ page }) => {
  const api = await mockApi(page, { perf_scan: perfScan })
  await openGenerators(page)

  const perf = page.locator('section.card').filter({ hasText: 'Viewport cost' })
  await perf.getByRole('button', { name: 'Measure' }).click()

  await expect.poll(() => api.count('perf_scan')).toBe(1)
  // Summary line + slowest sentence render from the fake perf result.
  await expect(perf.locator('.substats')).toContainText('40 ms')
  await expect(perf.locator('.substats')).toContainText('287')
  await expect(perf).toContainText('1 heavy')
  await expect(perf).toContainText('Sofa_Body_Hi')

  // Clicking a bar selects that generator in the viewport.
  await perf.locator('.bar-row', { hasText: 'Sofa_Body_Hi' }).click()
  await expect.poll(() => api.count('perf_select')).toBeGreaterThan(0)
  expect(api.find('perf_select')?.body).toEqual({ guids: [5001] })

  // The button now offers a re-measure.
  await expect(perf.getByRole('button', { name: 'Measure again' })).toBeVisible()
})

test('PerfCard surfaces a measurement error', async ({ page }) => {
  await mockApi(page, { perf_scan: { ok: false, error: 'measurement failed' } })
  await openGenerators(page)

  const perf = page.locator('section.card').filter({ hasText: 'Viewport cost' })
  await perf.getByRole('button', { name: 'Measure' }).click()

  await expect(perf.locator('.error')).toContainText('Measuring failed: measurement failed')
  // It recovers: the button is enabled again for a retry.
  await expect(perf.getByRole('button', { name: 'Measure' })).toBeEnabled()
})

test('an empty generators scan shows the no-generators note and no cards', async ({ page }) => {
  await mockApi(page, {
    gens_scan: {
      ok: true, types: [],
      summary: { total_generators: 0, types_found: 0, non_uniform_params: 0 },
    },
  })
  await openGenerators(page)

  await expect(page.getByText('No audited generators in this scene', { exact: false })).toBeVisible()
  await expect(page.locator('.gens-type')).toHaveCount(0)
  // The cost audit still applies to every generator, so PerfCard stays.
  await expect(page.locator('section.card').filter({ hasText: 'Viewport cost' })).toBeVisible()
})
