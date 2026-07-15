// E2E coverage for the Tags area (frontend/src/tabs/TagsTab.tsx). Every
// interactive element gets one assertion on the API call log (op + payload)
// and one on the visible reaction. All /api/* is mocked (e2e/mock.ts) — no
// Cinema 4D, no live server. Follows the shell.spec.ts pattern: fresh
// mockApi() + goto('/') per test.
import { test, expect, type Page } from '@playwright/test'
import { mockApi } from './mock'

// Boot the app, wait for the fake scene, then switch to the Tags tab.
async function openTags(page: Page): Promise<void> {
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Tags' }).first().click()
}

// A fully empty (but ok) scan — drives every empty-state branch.
const EMPTY_TAGS = {
  ok: true,
  types: [],
  findings: {
    missing_phong: [],
    duplicate_material_tags: [],
    phong_angles: { distribution: [], dominant_angle: null },
  },
  summary: { total_tags: 0, tag_types: 0, missing_phong: 0, duplicate_material_tags: 0 },
}

test('renders the summary, distribution and tag-type list from the scan', async ({ page }) => {
  const api = await mockApi(page)
  await openTags(page)

  // The scan drives the summary numbers.
  await expect(page.locator('.substats')).toContainText('3266 tags')
  await expect(page.locator('.substats')).toContainText('6 types')
  await expect(page.locator('.substats')).toContainText('3 missing phong')
  await expect(page.locator('.substats')).toContainText('2 duplicate material tags')
  expect(api.count('tags_scan')).toBeGreaterThan(0)

  // Phong-angle distribution: the dominant bucket (40°) is flagged.
  await expect(page.locator('.card-head', { hasText: 'Phong angles' })).toContainText('dominant 40°')
  await expect(page.locator('.tags-angle.dominant')).toHaveText('40°')

  // All six tag types are listed.
  await expect(page.locator('.card-head', { hasText: 'All tag types' }).locator('.head-count'))
    .toHaveText('6 types')
  await expect(page.locator('.tags-type')).toHaveCount(6)
})

test('Select in C4D fires tags_select with the type id and reports the count', async ({ page }) => {
  const api = await mockApi(page, {
    // Echo a plausible selected count per underlying request.
    tags_select: (b) => ({ ok: true, selected: b.type_ids ? 63 : 1176 }),
  })
  await openTags(page)

  // A plain tag type sends { type_id }.
  const phong = page.locator('.tags-type', { hasText: 'Phong' })
  await phong.getByRole('button', { name: 'Select in C4D' }).click()
  await expect(page.locator('.statusbar-text')).toContainText('Selected 1176 objects in Cinema 4D')
  await expect.poll(() => api.count('tags_select')).toBe(1)
  expect(api.find('tags_select')?.body).toEqual({ type_id: 5612 })

  // The merged "Selection" entry sends every underlying { type_ids }.
  const selection = page.locator('.tags-type', { hasText: 'Selection' })
  await selection.getByRole('button', { name: 'Select in C4D' }).click()
  await expect(page.locator('.statusbar-text')).toContainText('Selected 63 objects in Cinema 4D')
  await expect.poll(() => api.count('tags_select')).toBe(2)
  expect(api.all('tags_select')[1].body).toEqual({ type_ids: [5673, 5674, 5701] })
})

test('a tag type expands to its objects; a row focuses it, multi-tag chips show kinds', async ({ page }) => {
  const api = await mockApi(page)
  await openTags(page)

  // Expand the Phong type -> its object rows appear (12 in the fixture).
  const phong = page.locator('.tags-type', { hasText: 'Phong' })
  await phong.locator('.tags-type-toggle').click()
  await expect(phong.locator('.tags-obj-row')).toHaveCount(12)

  // Clicking an object row focuses & frames it in C4D.
  const firstRow = phong.locator('.tags-obj-row').first()
  const name = (await firstRow.locator('.tags-obj-name').textContent())?.trim() || ''
  expect(name).not.toBe('')
  await firstRow.click()
  await expect(page.locator('.statusbar-text')).toContainText(`Focused ${name}`)
  await expect.poll(() => api.count('focus')).toBeGreaterThan(0)
  expect(typeof api.find('focus')?.body.guid).toBe('number')

  // Collapsing hides the rows again.
  await phong.locator('.tags-type-toggle').click()
  await expect(phong.locator('.tags-obj-row')).toHaveCount(0)

  // The merged Selection entry renders a multi-tag object with kind badges.
  const selection = page.locator('.tags-type', { hasText: 'Selection' })
  await selection.locator('.tags-type-toggle').click()
  const coffee = selection.locator('.tags-obj-row', { hasText: 'CoffeeTable' })
  await expect(coffee.locator('.tags-obj-count')).toHaveText('×2')
  await expect(coffee).toContainText('TopFaces')
  await expect(coffee).toContainText('poly')
  await expect(coffee).toContainText('Bevel_Loop')
  await expect(coffee).toContainText('edge')
})

test('adding a single missing Phong tag from its row fires tags_add_phong with the guid', async ({ page }) => {
  const api = await mockApi(page, {
    tags_add_phong: { ok: true, applied: 1, angle_deg: 40 },
  })
  await openTags(page)

  const missing = page.locator('.card', { hasText: 'Missing phong tags' })
  const firstRow = missing.locator('.sg-row').first()
  await firstRow.locator('.rn-ok').click()

  await expect.poll(() => api.count('tags_add_phong')).toBe(1)
  const body = api.find('tags_add_phong')?.body as { guids?: number[] }
  expect(Array.isArray(body.guids)).toBe(true)
  expect(body.guids).toHaveLength(1)
  await expect(page.locator('.wb-note')).toContainText('Added 1 Phong tag ✓ (undoable)')
})

test('the row body focuses the object without applying anything', async ({ page }) => {
  const api = await mockApi(page)
  await openTags(page)

  const missing = page.locator('.card', { hasText: 'Missing phong tags' })
  const firstRow = missing.locator('.sg-row').first()
  const name = (await firstRow.locator('.rn-old').textContent())?.trim() || ''
  await firstRow.locator('.sg-body').click()

  await expect(page.locator('.statusbar-text')).toContainText(`Focused ${name}`)
  await expect.poll(() => api.count('focus')).toBeGreaterThan(0)
  expect(api.count('tags_add_phong')).toBe(0)
})

test('batch "Add all Phong tags" confirms once then fires tags_add_phong', async ({ page }) => {
  const api = await mockApi(page, {
    tags_add_phong: { ok: true, applied: 3, angle_deg: 40 },
  })
  await openTags(page)

  const missing = page.locator('.card', { hasText: 'Missing phong tags' })
  await missing.getByRole('button', { name: 'Add all Phong tags', exact: true }).click()

  // ONE confirm: the Workbench "process N items" guard — no second,
  // tab-specific modal behind it.
  const wbModal = page.locator('.confirm-box', { hasText: 'process 3 items' })
  await expect(wbModal).toBeVisible()
  await wbModal.locator('.apply').click()

  await expect.poll(() => api.count('tags_add_phong')).toBe(1)
  expect(api.find('tags_add_phong')?.body).toEqual({})
  await expect(page.locator('.wb-note')).toContainText('Added 3 Phong tags at 40° ✓ (undoable)')
  await expect(page.locator('.confirm-box')).toHaveCount(0)
})

test('cancelling the batch confirm makes no API call', async ({ page }) => {
  const api = await mockApi(page)
  await openTags(page)

  const dup = page.locator('.card', { hasText: 'Duplicate material tags' })
  await dup.getByRole('button', { name: 'Delete all duplicates', exact: true }).click()

  const wbModal = page.locator('.confirm-box', { hasText: 'process 2 items' })
  await expect(wbModal).toBeVisible()
  await wbModal.locator('.ghost').click()

  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('tags_delete_duplicates')).toBe(0)
})

test('batch "Delete all duplicates" confirms once then fires tags_delete_duplicates', async ({ page }) => {
  const api = await mockApi(page, {
    tags_delete_duplicates: { ok: true, deleted: 5 },
  })
  await openTags(page)

  const dup = page.locator('.card', { hasText: 'Duplicate material tags' })
  await dup.getByRole('button', { name: 'Delete all duplicates', exact: true }).click()

  const wbModal = page.locator('.confirm-box', { hasText: 'process 2 items' })
  await expect(wbModal).toBeVisible()
  await wbModal.locator('.apply').click()

  await expect.poll(() => api.count('tags_delete_duplicates')).toBe(1)
  expect(api.find('tags_delete_duplicates')?.body).toEqual({})
  await expect(page.locator('.wb-note')).toContainText('Deleted 5 duplicate material tags ✓ (undoable)')
  await expect(page.locator('.confirm-box')).toHaveCount(0)
})

test('deleting duplicates from a single row fires tags_delete_duplicates with the guid', async ({ page }) => {
  const api = await mockApi(page, {
    tags_delete_duplicates: { ok: true, deleted: 2 },
  })
  await openTags(page)

  const dup = page.locator('.card', { hasText: 'Duplicate material tags' })
  const firstRow = dup.locator('.sg-row').first()
  // The redundant-copy count and material render on the row.
  await expect(firstRow).toContainText('Wood_Walnut')
  await firstRow.locator('.rn-ok').click()

  await expect.poll(() => api.count('tags_delete_duplicates')).toBe(1)
  const body = api.find('tags_delete_duplicates')?.body as { guids?: number[] }
  expect(body.guids).toHaveLength(1)
  await expect(page.locator('.wb-note')).toContainText('Deleted 2 duplicate material tags ✓ (undoable)')
})

test('a phong-angle preset chip sets a uniform angle', async ({ page }) => {
  const api = await mockApi(page, {
    tags_set_phong_angle: (b) => ({ ok: true, applied: 3266, angle_deg: b.angle_deg }),
  })
  await openTags(page)

  await page.locator('.tags-angle-set .chip-btn', { hasText: '40°' }).click()

  const modal = page.locator('.confirm-box', { hasText: 'Set the phong angle to 40°' })
  await expect(modal).toBeVisible()
  await modal.locator('.apply').click()

  await expect.poll(() => api.count('tags_set_phong_angle')).toBe(1)
  expect(api.find('tags_set_phong_angle')?.body).toEqual({ angle_deg: 40 })
  await expect(page.locator('.wb-note')).toContainText('Set 3266 phong tags to 40° ✓ (undoable)')
})

test('a custom phong angle can be typed and applied; invalid input keeps Set disabled', async ({ page }) => {
  const api = await mockApi(page, {
    tags_set_phong_angle: (b) => ({ ok: true, applied: 3266, angle_deg: b.angle_deg }),
  })
  await openTags(page)

  const setBtn = page.locator('.tags-angle-set').getByRole('button', { name: 'Set', exact: true })
  const input = page.locator('.tags-angle-input')

  // Empty and out-of-range input keep the Set button disabled.
  await expect(setBtn).toBeDisabled()
  await input.fill('999')
  await expect(setBtn).toBeDisabled()

  // A valid angle enables it.
  await input.fill('55')
  await expect(setBtn).toBeEnabled()
  await setBtn.click()

  const modal = page.locator('.confirm-box', { hasText: 'Set the phong angle to 55°' })
  await expect(modal).toBeVisible()
  await modal.locator('.apply').click()

  await expect.poll(() => api.count('tags_set_phong_angle')).toBe(1)
  expect(api.find('tags_set_phong_angle')?.body).toEqual({ angle_deg: 55 })
  await expect(page.locator('.wb-note')).toContainText('Set 3266 phong tags to 55° ✓ (undoable)')
})

test('an empty scan renders every empty state', async ({ page }) => {
  await mockApi(page, { tags_scan: EMPTY_TAGS })
  await openTags(page)

  await expect(page.locator('.substats')).toContainText('0 tags')
  await expect(page.getByText('Every polygon object has a Phong tag')).toBeVisible()
  await expect(page.getByText('No duplicate material tags')).toBeVisible()
  await expect(page.getByText('No phong tags in the scene.')).toBeVisible()
  await expect(page.getByText('No tags in the scene.')).toBeVisible()
})

test('a failed scan shows the error note instead of the tab', async ({ page }) => {
  await mockApi(page, { tags_scan: { error: 'scan failed' } })
  await openTags(page)

  const note = page.locator('.empty-note', { hasText: 'Tag scan failed' })
  await expect(note).toBeVisible()
  await expect(note.locator('code')).toHaveText('scan failed')
})
