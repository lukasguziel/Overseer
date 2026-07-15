// E2E coverage for the Sims area: the sims_scan summary, the per-row and batch
// "disable" actions (incl. the confirm modal), row-click focus, the per-kind
// "Select in C4D" action, plus the empty and failing scan states. Every test
// mocks /api/* fresh and asserts BOTH the fired op + payload (call log) and a
// visible UI reaction. Nothing reaches a real Cinema 4D server.
import { test, expect } from '@playwright/test'
import { mockApi } from './mock'
import type { Page } from '@playwright/test'

// Boot the app and switch to the Sims tab (the scan fires on activation).
async function openSims(page: Page): Promise<void> {
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Sims' }).first().click()
}

test('boots the Sims scan and renders the simulation summary', async ({ page }) => {
  const api = await mockApi(page)
  await openSims(page)

  // (a) the scan op fired …
  await expect.poll(() => api.count('sims_scan')).toBeGreaterThan(0)
  // (b) … and its summary rendered: 6 participants, per-kind chips, the
  // active-on-hidden warning stat.
  const substats = page.locator('.substats')
  await expect(substats).toContainText('6')
  await expect(substats).toContainText('participants')
  await expect(substats).toContainText('3 cloth')
  await expect(substats).toContainText('1 dynamics')
  await expect(substats).toContainText('2 collider')
  await expect(substats).toContainText('active on hidden')

  // The three finding cards render from the fixture findings.
  await expect(page.locator('section.card', { hasText: 'Active on hidden objects' })).toBeVisible()
  await expect(page.locator('section.card', { hasText: 'Unbaked simulations' })).toBeVisible()
  await expect(page.locator('section.card', { hasText: 'All simulation participants' })).toBeVisible()
})

test('a per-row ✓ disables one simulation', async ({ page }) => {
  const api = await mockApi(page, {
    sims_set_enabled: { ok: true, applied: 1 },
  })
  await openSims(page)

  const card = page.locator('section.card', { hasText: 'Active on hidden objects' })
  await card.locator('.rn-ok').click()

  // (a) the op fired with the per-kind toggle payload …
  await expect.poll(() => api.count('sims_set_enabled')).toBe(1)
  expect(api.find('sims_set_enabled')?.body).toMatchObject({ kind: 'dynamics', enabled: false })
  expect((api.find('sims_set_enabled')?.body.guids as number[]).length).toBe(1)
  // … and the scan was reloaded afterwards.
  await expect.poll(() => api.count('sims_scan')).toBeGreaterThan(1)

  // (b) the note reports the outcome.
  await expect(page.locator('.wb-note')).toContainText('OldSet_backup: 1 disabled')
})

test('the batch Disable button opens the confirm modal; Cancel closes it without a call', async ({ page }) => {
  const api = await mockApi(page)
  await openSims(page)

  const card = page.locator('section.card', { hasText: 'Active on hidden objects' })
  await card.getByRole('button', { name: 'Disable 1' }).click()

  // Modal opens — no API call yet.
  const modal = page.locator('.confirm-box')
  await expect(modal).toBeVisible()
  await expect(modal.locator('.confirm-title')).toHaveText('Disable simulations')
  await expect(modal.locator('.confirm-msg'))
    .toContainText('Disable 1 simulation running on hidden objects?')
  expect(api.count('sims_set_enabled')).toBe(0)

  // Cancel closes the modal and still fires nothing.
  await modal.getByRole('button', { name: 'Cancel' }).click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('sims_set_enabled')).toBe(0)
})

test('confirming the modal disables the batch', async ({ page }) => {
  const api = await mockApi(page, {
    sims_set_enabled: { ok: true, applied: 1 },
  })
  await openSims(page)

  const card = page.locator('section.card', { hasText: 'Active on hidden objects' })
  await card.getByRole('button', { name: 'Disable 1' }).click()

  const modal = page.locator('.confirm-box')
  await modal.getByRole('button', { name: '✓ Disable 1' }).click()

  // (a) the op fired for the hidden-active group …
  await expect.poll(() => api.count('sims_set_enabled')).toBe(1)
  expect(api.find('sims_set_enabled')?.body).toMatchObject({ kind: 'dynamics', enabled: false })
  // (b) the modal closed and the note reports the batch outcome.
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  await expect(page.locator('.wb-note')).toContainText('Active on hidden: 1 disabled')
})

test('clicking a row focuses the object in Cinema 4D', async ({ page }) => {
  const api = await mockApi(page)
  await openSims(page)

  // The unbaked card holds exactly one row (Curtain_right).
  const card = page.locator('section.card', { hasText: 'Unbaked simulations' })
  await card.locator('.sg-body').click()

  // (a) focus fired with a numeric guid …
  await expect.poll(() => api.count('focus')).toBe(1)
  expect(typeof api.find('focus')?.body.guid).toBe('number')
  // (b) … and the status toast names the focused object.
  await expect(page.locator('.statusbar-text')).toContainText('Curtain_right')
})

test('Select in C4D selects a kind group', async ({ page }) => {
  const api = await mockApi(page, {
    sims_select: { ok: true, selected: 3 },
  })
  await openSims(page)

  const participants = page.locator('section.card', { hasText: 'All simulation participants' })
  await participants.locator('.sim-group', { hasText: 'cloth' })
    .getByRole('button', { name: 'Select in C4D' }).click()

  // (a) the select op fired for the cloth kind …
  await expect.poll(() => api.count('sims_select')).toBe(1)
  expect(api.find('sims_select')?.body).toMatchObject({ kind: 'cloth' })
  // (b) … and the note reports the selection count.
  await expect(page.locator('.wb-note')).toContainText('Selected 3 cloth objects in Cinema 4D')
})

test('an empty scene shows the no-sims note', async ({ page }) => {
  await mockApi(page, {
    sims_scan: {
      ok: true, hits: [],
      findings: { active_hidden: [], unbaked: [], disabled_leftovers: [] },
      summary: { total: 0, by_kind: {}, active_hidden: 0, unbaked: 0, disabled: 0 },
    },
  })
  await openSims(page)

  await expect(page.locator('.empty-note')).toContainText('No simulation setups found in this scene.')
  await expect(page.locator('.substats')).toHaveCount(0)
})

test('a failing scan shows the error state and Retry re-runs it', async ({ page }) => {
  const api = await mockApi(page, {
    sims_scan: { error: 'scan blew up' },
  })
  await openSims(page)

  // (b) the error placeholder renders with the message + a Retry button.
  const empty = page.locator('.empty-state')
  await expect(empty).toContainText('Sims scan failed: scan blew up')
  await expect.poll(() => api.count('sims_scan')).toBe(1)

  // (a) Retry re-fires the scan op.
  await empty.getByRole('button', { name: 'Retry' }).click()
  await expect.poll(() => api.count('sims_scan')).toBe(2)
})
