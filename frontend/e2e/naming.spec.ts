// E2E coverage for the "Naming" area (tabs/NamingTab.tsx). Every interactive
// element is exercised and each interaction asserts BOTH the API op + payload
// (via the mock call log) AND a visible UI reaction. Nothing reaches a real
// server — mockApi() answers every /api/* from the shared fixtures, with
// per-op overrides where a test needs different data.
import { test, expect } from '@playwright/test'
import { mockApi, type ApiLog } from './mock'

// Boot the app and switch to the Naming tab. The nav is enabled once the boot
// analysis rendered (the scene name appears), then the rename workbench mounts.
async function openNaming(page: import('@playwright/test').Page) {
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Naming' }).first().click()
  await expect(page.locator('.wb-preview')).toBeVisible()
}

// Body of the most recent call to `op` (settings changes re-plan repeatedly, so
// the interesting payload is always the latest one).
const lastBody = (api: ApiLog, op: string) => api.all(op).at(-1)?.body as any

// The Casing / Numbering / Duplicates rule sections, addressed by their title.
const ruleSection = (page: import('@playwright/test').Page, title: string) =>
  page.locator('.rule-section').filter({ hasText: title })

test('renders the rename preview and its rule chips from the plan', async ({ page }) => {
  await mockApi(page)
  await openNaming(page)

  // 9 diff rows from fixtures.planNaming — all fit on one page.
  await expect(page.locator('.rename-list .rename-row')).toHaveCount(9)
  await expect(page.locator('.wb-preview-head .head-count')).toContainText('9 changes')
  // A concrete rename is rendered old → new.
  const row = page.locator('.rename-row', { hasText: 'kitchen_cabinets_lower' })
  await expect(row.locator('.rn-new')).toContainText('KitchenCabinetsLower')
  // Single-rule rows show the rule tag inline.
  await expect(page.locator('.rename-row', { hasText: 'Plate.1' })
    .locator('.rule-tag')).toContainText('numbering')
})

test('a multi-rule row expands its collapsed rule count (client-side only)', async ({ page }) => {
  await mockApi(page)
  await openNaming(page)

  // pillow_01 carries casing + numbering → collapsed behind a "2 rules" chip.
  const row = page.locator('.rename-row', { hasText: 'pillow_01' })
  const count = row.locator('.rule-count')
  await expect(count).toContainText('2 rules')
  await count.click()
  await expect(row.locator('.rule-tag.rt-casing')).toBeVisible()
  await expect(row.locator('.rule-tag.rt-numbering')).toBeVisible()
})

test('choosing a casing style re-plans with that casing', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const select = ruleSection(page, 'Casing').locator('select')
  await expect(select).toHaveValue('PascalCase')   // scene's dominant casing
  await select.selectOption('camelCase')

  // The preview re-plans with the new setting…
  await expect.poll(() => lastBody(api, 'plan_naming')?.settings?.casing).toBe('camelCase')
  // …and the control reflects the choice.
  await expect(select).toHaveValue('camelCase')
})

test('turning the casing rule off collapses its controls and re-plans', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const section = ruleSection(page, 'Casing')
  const toggle = section.locator('input[type=checkbox]').first()
  await expect(toggle).toBeChecked()
  await section.locator('.rule-switch').click()

  await expect(toggle).not.toBeChecked()
  // Controls collapse to the single "off" line, the style select is gone.
  await expect(section.locator('select')).toHaveCount(0)
  await expect(section.getByText('Casing and separators kept as-is.')).toBeVisible()
  await expect.poll(() => lastBody(api, 'plan_naming')?.settings?.apply_casing).toBe(false)
})

test('the numbering pad buttons re-plan with the chosen pad', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const section = ruleSection(page, 'Numbering')
  await expect(section.locator('.pad-field')).toContainText('2-digit')
  const three = section.locator('.pad-btn', { hasText: '3' })
  await three.click()

  await expect(three).toHaveClass(/on/)
  await expect(section.locator('.pad-field')).toContainText('3-digit')
  await expect.poll(() => lastBody(api, 'plan_naming')?.settings?.number_pad).toBe(3)
})

test('keep-separators toggle re-plans and unlocks keep-special-characters', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const specials = page.locator('label.check', { hasText: 'Keep special characters' })
    .locator('input')
  // While separators are kept, the specials switch is forced on and disabled.
  await expect(specials).toBeDisabled()

  await page.locator('label.check', { hasText: 'Keep separators' }).click()

  await expect(specials).toBeEnabled()
  // The example hint switches to the "specials survive" wording.
  await expect(ruleSection(page, 'Casing')).toContainText('Brackets')
  await expect.poll(() => lastBody(api, 'plan_naming')?.settings?.keep_separators).toBe(false)
})

test('turning duplicates off re-plans and states nothing is renumbered', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const section = ruleSection(page, 'Duplicates')
  await section.locator('.rule-switch').click()

  await expect(section.getByText('Duplicate names are left alone.')).toBeVisible()
  await expect.poll(() => lastBody(api, 'plan_naming')?.settings?.dedupe).toBe(false)
})

test('a per-row ✓ renames just that object with its guid', async ({ page }) => {
  const api = await mockApi(page, { apply_naming: { ok: true, applied: 1 } })
  await openNaming(page)

  const row = page.locator('.rename-list .rename-row').first()
  await expect(row).toContainText('kitchen_cabinets_lower')
  await row.locator('.rn-ok').click()

  // Fired apply_naming for a single object (guids present, length 1).
  await expect.poll(() => api.count('apply_naming')).toBeGreaterThan(0)
  const body = lastBody(api, 'apply_naming')
  expect(Array.isArray(body.guids)).toBeTruthy()
  expect(body.guids).toHaveLength(1)
  expect(body.settings).toBeTruthy()
  // Visible outcome in the status toast.
  await expect(page.locator('.statusbar-text')).toContainText('Renamed')
})

test('a per-row grey ✓ accepts that name as-is (set_keeps)', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const row = page.locator('.rename-list .rename-row').first()
  await row.locator('.rn-keep').click()

  await expect.poll(() => api.count('set_keeps')).toBeGreaterThan(0)
  const body = lastBody(api, 'set_keeps')
  expect(body.section).toBe('naming')
  expect(body.keys).toContain('kitchen_cabinets_lower')
  await expect(page.locator('.statusbar-text')).toContainText('Accepted')
})

test('clicking a preview row body focuses the object in C4D', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  await page.locator('.rename-list .rename-row .sg-body').first().click()

  await expect.poll(() => api.count('focus')).toBeGreaterThan(0)
  expect(typeof lastBody(api, 'focus').guid).toBe('number')
  await expect(page.locator('.statusbar-text')).toContainText('Focus')
})

test('the "Apply all" modal cancels cleanly and confirms into apply_naming', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const applyAll = page.locator('.wb-preview-head').getByRole('button', { name: 'Apply all' })
  await applyAll.click()
  const modal = page.locator('.confirm-overlay')
  await expect(modal).toBeVisible()
  await expect(page.locator('.confirm-title')).toHaveText('Apply all')

  // Cancel: modal closes, nothing applied.
  await modal.locator('.ghost').click()
  await expect(modal).toBeHidden()
  expect(api.count('apply_naming')).toBe(0)

  // Reopen and confirm: a batch apply (settings, no guids).
  await applyAll.click()
  await page.locator('.confirm-overlay .apply').click()
  await expect(page.locator('.confirm-overlay')).toBeHidden()
  await expect.poll(() => api.count('apply_naming')).toBeGreaterThan(0)
  const body = lastBody(api, 'apply_naming')
  expect(body.settings).toBeTruthy()
  expect(body.guids).toBeUndefined()
})

test('the "Keep all as-is" modal accepts the whole plan (set_keeps)', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  await page.locator('.wb-preview-head').getByRole('button', { name: 'Keep all as-is' }).click()
  const modal = page.locator('.confirm-overlay')
  await expect(modal).toBeVisible()
  await expect(modal.locator('.apply')).toContainText('Accept 9 items')
  await modal.locator('.apply').click()

  await expect(modal).toBeHidden()
  await expect.poll(() => api.count('set_keeps')).toBeGreaterThan(0)
  const body = lastBody(api, 'set_keeps')
  expect(body.section).toBe('naming')
  // Every previewed old name is now accepted.
  expect(body.keys).toContain('kitchen_cabinets_lower')
  await expect(page.locator('.statusbar-text')).toContainText('Accepted 9 items as-is')
})

test('the name-cleanup buckets list default and duplicate names', async ({ page }) => {
  await mockApi(page)
  await openNaming(page)

  const defaults = page.locator('section.card', { hasText: 'Default names' })
  await expect(defaults.locator('.cl-item')).toHaveCount(3)   // Cube, Cube.1, Null
  await expect(defaults).toContainText('Cube')

  const dupes = page.locator('section.card', { hasText: 'Duplicate names' })
  // Chair (×4) and Cup (×2) are the sibling clashes.
  await expect(dupes.locator('.cl-item')).toHaveCount(2)
  await expect(dupes).toContainText('×4')
})

test('a cleanup row focuses its object', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const defaults = page.locator('section.card', { hasText: 'Default names' })
  await defaults.locator('.cl-focus').first().click()

  await expect.poll(() => api.count('focus')).toBeGreaterThan(0)
  expect(typeof lastBody(api, 'focus').guid).toBe('number')
})

test('the inline cleanup rename cancels, then commits a rename_object', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const defaults = page.locator('section.card', { hasText: 'Default names' })
  const firstRow = defaults.locator('.cl-item').first()

  // Open the editor, then cancel — no API call, editor closed.
  await firstRow.locator('.cl-rename').click()
  const editor = defaults.locator('.cl-edit')
  await expect(editor).toBeVisible()
  await editor.locator('.rn-no').click()
  await expect(defaults.locator('.cl-edit')).toHaveCount(0)
  expect(api.count('rename_object')).toBe(0)

  // Reopen, type a new name, commit with Enter.
  await defaults.locator('.cl-item').first().locator('.cl-rename').click()
  const input = defaults.locator('.cl-edit input')
  await input.fill('SofaLeg')
  await input.press('Enter')

  await expect.poll(() => api.count('rename_object')).toBeGreaterThan(0)
  expect(lastBody(api, 'rename_object').name).toBe('SofaLeg')
  await expect(defaults.locator('.cl-edit')).toHaveCount(0)
})

test('a cleanup ✓ accepts a single default name as-is (set_keeps)', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const defaults = page.locator('section.card', { hasText: 'Default names' })
  await defaults.locator('.cl-item').first().locator('.cl-keep').click()

  await expect.poll(() => api.count('set_keeps')).toBeGreaterThan(0)
  const body = lastBody(api, 'set_keeps')
  expect(body.section).toBe('naming')
  expect(body.keys).toContain('Cube')
  await expect(page.locator('.statusbar-text')).toContainText('Accepted')
})

test('a cleanup bucket "Keep all as-is" modal cancels then accepts (set_keeps)', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  const defaults = page.locator('section.card', { hasText: 'Default names' })
  await defaults.locator('.cl-keepall').click()
  const modal = page.locator('.confirm-overlay')
  await expect(modal).toBeVisible()
  await expect(modal.locator('.apply')).toContainText('Accept 3')

  // Cancel first.
  await modal.locator('.ghost').click()
  await expect(modal).toBeHidden()
  expect(api.count('set_keeps')).toBe(0)

  // Then accept the whole bucket.
  await defaults.locator('.cl-keepall').click()
  await page.locator('.confirm-overlay .apply').click()
  await expect(page.locator('.confirm-overlay')).toBeHidden()

  await expect.poll(() => api.count('set_keeps')).toBeGreaterThan(0)
  const body = lastBody(api, 'set_keeps')
  expect(body.section).toBe('naming')
  expect(body.keys).toContain('Cube')
  expect(body.keys).toContain('Null')
})

test('the Accepted panel opens and restoring an item writes set_keeps', async ({ page }) => {
  const api = await mockApi(page)
  await openNaming(page)

  // planNaming.kept = ['HDRI_Dome'] seeds one accepted naming item.
  const toggle = page.locator('.kept-toggle')
  await expect(toggle).toContainText('1 accepted item')
  await toggle.click()

  const row = page.locator('.kept-row', { hasText: 'HDRI_Dome' })
  await expect(row).toBeVisible()
  await row.getByRole('button', { name: 'Restore', exact: true }).click()

  await expect.poll(() => api.count('set_keeps')).toBeGreaterThan(0)
  expect(lastBody(api, 'set_keeps').section).toBe('naming')
})

test('the rename preview paginates a long plan', async ({ page }) => {
  // Override the plan with 12 rows so the workbench pager appears (page size 10).
  const diff = Array.from({ length: 12 }, (_, i) => ({
    guid: 5000 + i, old: `obj_${i}`, new: `Obj${i}`, rules: ['casing'],
  }))
  await mockApi(page, { plan_naming: { ok: true, count: 12, kept: [], diff } })
  await openNaming(page)

  await expect(page.locator('.rename-list .rename-row')).toHaveCount(10)
  const pager = page.locator('.wb-preview .pager')
  await expect(pager.locator('.pager-info')).toContainText('1–10 of 12')
  await pager.locator('.pager-btn[title="Next page"]').click()
  await expect(pager.locator('.pager-info')).toContainText('11–12 of 12')
  await expect(page.locator('.rename-list .rename-row')).toHaveCount(2)
})

test('an empty rename plan shows the all-clear state', async ({ page }) => {
  await mockApi(page, { plan_naming: { ok: true, count: 0, kept: [], diff: [] } })
  await openNaming(page)

  await expect(page.locator('.wb-preview-head .head-count')).toContainText('nothing to change')
  const empty = page.locator('.wb-preview .empty-note')
  await expect(empty).toContainText('Every name already matches your rules')
  // The cleanup buckets still hold open items, so the empty state nudges down.
  await expect(empty).toContainText('cleanup area below')
})
