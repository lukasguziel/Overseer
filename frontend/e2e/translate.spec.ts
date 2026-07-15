// E2E coverage for the Translate tab. Every interactive element the area
// offers is exercised against a fully mocked /api/* (e2e/mock.ts): the two
// sidebar selects (target language + engine), the per-row apply / keep / focus
// buttons, the "Apply all" and "Keep all as-is" batch modals (open / cancel /
// confirm), the Accepted-as-is panel restore, the area History revert, plus an
// empty/negative render. Each test asserts BOTH the API op + payload (via the
// mock call log) and a visible UI reaction. Pattern follows shell.spec.ts.
import { test, expect } from '@playwright/test'
import type { Page } from '@playwright/test'
import { mockApi } from './mock'

// A detected-language block shaped like the real plan_translate response.
const DETECTED = {
  counts: { en: 1288, unknown: 421, de: 138 },
  total: 1847, dominant: 'en', en: 1288, de: 138, unknown: 421,
}

// Build a plan_translate response from a diff list.
function trPlan(diff: unknown[], extra: Record<string, unknown> = {}) {
  return {
    ok: true, count: diff.length, kept: [], target: 'fr', engine: 'google',
    detected: DETECTED, diff, ...extra,
  }
}

const ROW_A = { guid: 101, old: 'Chair', new: 'Chaise', words: [['chair', 'chaise']], lang: 'en' }
const ROW_B = { guid: 102, old: 'Rug', new: 'Tapis', words: [['rug', 'tapis']], lang: 'en' }
const ROW_C = { guid: 103, old: 'Wardrobe', new: 'Armoire', words: [['wardrobe', 'armoire']], lang: 'en' }

// Boot the app, wait for the report, then open the Translate tab.
async function openTranslate(page: Page) {
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Translate' }).first().click()
}

test('boots the Translate tab: plan preview + detected languages render', async ({ page }) => {
  const api = await mockApi(page)
  await openTranslate(page)

  // The tab plans the translation on open.
  await expect.poll(() => api.count('plan_translate')).toBeGreaterThan(0)

  // Preview panel: title + the fixture's 8 changes + rows.
  await expect(page.locator('.wb-preview-head h3')).toHaveText('Translation preview')
  await expect(page.locator('.head-count')).toContainText('8 changes')
  await expect(page.locator('.rename-list .sg-row')).toHaveCount(8)
  await expect(page.locator('.sg-row', { hasText: 'Chaise' })).toContainText('Chair')

  // Detected panel: dominant language highlighted + summary sentence.
  const dominant = page.locator('.grouplist li.lang-dom')
  await expect(dominant).toContainText('English')
  await expect(dominant).toContainText('1288')
  await expect(page.locator('.wb-side')).toContainText('across 1847 names')
})

test('target language select re-plans with the chosen target', async ({ page }) => {
  // German target returns an empty plan so the target choice drives a visible
  // change; English (boot) keeps the full 8-row fixture.
  const api = await mockApi(page, {
    plan_translate: (body) =>
      body.target === 'de' ? trPlan([], { target: 'de' })
        : trPlan([ROW_A, ROW_B, ROW_C].concat(
          Array.from({ length: 5 }, (_, i) => ({ guid: 200 + i, old: `X${i}`, new: `Y${i}`, words: [], lang: 'en' })))),
  })
  await openTranslate(page)
  await expect(page.locator('.rename-list .sg-row')).toHaveCount(8)

  const target = page.locator('label', { hasText: 'Target language' }).locator('select')
  await target.selectOption('de')

  // Payload carries the new target...
  await expect.poll(() => api.all('plan_translate').some((c) => c.body.target === 'de')).toBe(true)
  // ...and the empty result renders the target-specific empty note.
  await expect(page.locator('.wb-scroll')).toContainText('Every name is already German')
  await expect(page.locator('.head-count')).toContainText('nothing to change')
})

test('engine select: switching to offline snaps a Google-only target back to en', async ({ page }) => {
  const api = await mockApi(page, { plan_translate: () => trPlan([ROW_A, ROW_B]) })
  await openTranslate(page)

  const target = page.locator('label', { hasText: 'Target language' }).locator('select')
  const engine = page.locator('label', { hasText: 'Engine' }).locator('select')

  // Google engine: the online warning is shown and any of 16 targets is pickable.
  await expect(page.locator('.wb-side')).toContainText('names are sent to Google')
  await target.selectOption('fr')
  await expect.poll(() => api.all('plan_translate').some((c) => c.body.target === 'fr')).toBe(true)

  // Switch to Offline: only EN/DE are valid, so the fr target snaps to en.
  await engine.selectOption('offline')
  await expect.poll(() =>
    api.all('plan_translate').some((c) => c.body.engine === 'offline' && c.body.target === 'en'),
  ).toBe(true)
  await expect(target).toHaveValue('en')
  await expect(page.locator('label', { hasText: 'Target language' }).locator('option')).toHaveCount(2)
  await expect(page.locator('.wb-side')).not.toContainText('names are sent to Google')
})

test('per-row apply (green check) translates one object and drops the row', async ({ page }) => {
  const applied = new Set<number>()
  const api = await mockApi(page, {
    plan_translate: () => trPlan([ROW_A, ROW_B].filter((r) => !applied.has(r.guid))),
    apply_translate: (body) => {
      const guids = (body.guids as number[]) || []
      guids.forEach((g) => applied.add(g))
      return { ok: true, applied: guids.length }
    },
  })
  await openTranslate(page)
  await expect(page.locator('.rename-list .sg-row')).toHaveCount(2)

  await page.locator('.sg-row', { hasText: 'Chaise' }).locator('.rn-ok').click()

  // Single-guid apply with the current settings/target/engine.
  await expect.poll(() => api.find('apply_translate')?.body.guids).toEqual([101])
  const body = api.find('apply_translate')!.body
  expect(body.target).toBe('en')
  expect(body.engine).toBe('google')
  expect(body).toHaveProperty('settings')

  // Row disappears; header count drops; status toast confirms.
  await expect(page.locator('.sg-row', { hasText: 'Chaise' })).toHaveCount(0)
  await expect(page.locator('.head-count')).toContainText('1 change')
  await expect(page.locator('.statusbar-text')).toContainText('Translated')
})

test('per-row keep (grey check) accepts one name as-is', async ({ page }) => {
  const api = await mockApi(page)
  await openTranslate(page)
  await expect(page.locator('.rename-list .sg-row')).toHaveCount(8)

  await page.locator('.sg-row', { hasText: 'Chaise' }).locator('.rn-keep').click()

  await expect.poll(() => api.find('set_keeps')?.body.section).toBe('translate')
  expect(api.find('set_keeps')!.body.keys).toContain('Chair')

  // Row removed optimistically + status toast.
  await expect(page.locator('.sg-row', { hasText: 'Chaise' })).toHaveCount(0)
  await expect(page.locator('.statusbar-text')).toContainText('Accepted')
})

test('clicking a row body focuses/frames the object in Cinema 4D', async ({ page }) => {
  const api = await mockApi(page)
  await openTranslate(page)

  await page.locator('.sg-row', { hasText: 'Chaise' }).locator('.sg-body').click()

  await expect.poll(() => api.count('focus')).toBeGreaterThan(0)
  expect(typeof api.find('focus')!.body.guid).toBe('number')
  await expect(page.locator('.statusbar-text')).toContainText('Focused')
})

test('"Apply all" batch: cancel does nothing, confirm translates everything', async ({ page }) => {
  let cleared = false
  const api = await mockApi(page, {
    plan_translate: () => (cleared ? trPlan([]) : trPlan([ROW_A, ROW_B, ROW_C])),
    apply_translate: (body) => { if (!body.guids) cleared = true; return { ok: true, applied: 8 } },
  })
  await openTranslate(page)
  await expect(page.locator('.head-count')).toContainText('3 changes')

  // Open the confirm modal.
  await page.locator('.wb-preview-head button', { hasText: 'Apply all' }).click()
  const modal = page.locator('.confirm-box')
  await expect(modal.locator('.confirm-title')).toHaveText('Apply all')
  await expect(modal.locator('.confirm-msg')).toContainText('process 3 items')

  // Cancel: modal closes, no apply fired.
  await modal.locator('button.ghost').click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('apply_translate')).toBe(0)

  // Reopen and confirm: batch apply (no guids) + empty result renders.
  await page.locator('.wb-preview-head button', { hasText: 'Apply all' }).click()
  await page.locator('.confirm-box button.apply').click()

  await expect.poll(() => api.count('apply_translate')).toBe(1)
  expect(api.find('apply_translate')!.body).not.toHaveProperty('guids')
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  await expect(page.locator('.wb-scroll')).toContainText('Every name is already English')
  await expect(page.locator('.statusbar-text')).toContainText('Translated 8 names')
})

test('"Keep all as-is" batch: confirm accepts every row and persists the keeps', async ({ page }) => {
  const api = await mockApi(page)
  await openTranslate(page)
  await expect(page.locator('.rename-list .sg-row')).toHaveCount(8)

  // Open + cancel first.
  await page.locator('.wb-preview-head button', { hasText: 'Keep all as-is' }).click()
  const modal = page.locator('.confirm-box')
  await expect(modal.locator('.confirm-title')).toHaveText('Keep all as-is')
  await modal.locator('button.ghost').click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('set_keeps')).toBe(0)

  // Reopen + confirm.
  await page.locator('.wb-preview-head button', { hasText: 'Keep all as-is' }).click()
  await page.locator('.confirm-box button.apply').click()

  await expect.poll(() => api.find('set_keeps')?.body.section).toBe('translate')
  const keys = api.find('set_keeps')!.body.keys as string[]
  // 8 plan rows + the pre-accepted Window_Front from the fixture's kept list.
  expect(keys).toHaveLength(9)
  expect(keys).toContain('Chair')
  expect(keys).toContain('Window_Front')

  // All rows cleared + status toast.
  await expect(page.locator('.rename-list .sg-row')).toHaveCount(0)
  await expect(page.locator('.head-count')).toContainText('nothing to change')
  await expect(page.locator('.statusbar-text')).toContainText('Accepted 8 items as-is')
})

test('Accepted-as-is panel lists a kept name and restores it', async ({ page }) => {
  // The fixture reports Window_Front as kept; mirror it in a mutable state the
  // set_keeps write drives, so the restore actually sticks after the re-plan.
  let kept: string[] = ['Window_Front']
  const api = await mockApi(page, {
    plan_translate: () => trPlan([ROW_A, ROW_B], { kept }),
    set_keeps: (body) => { if (body.section === 'translate') kept = (body.keys as string[]) || []; return { ok: true } },
  })
  await openTranslate(page)

  // Expand the panel (its toggle text distinguishes it from the History one).
  const toggle = page.locator('.kept-toggle', { hasText: 'accepted item' })
  await expect(toggle).toContainText('Translate 1')
  await toggle.click()

  const row = page.locator('.kept-row', { hasText: 'Window_Front' })
  await expect(row).toBeVisible()
  await row.getByRole('button', { name: 'Restore', exact: true }).click()

  await expect.poll(() => api.find('set_keeps')?.body.section).toBe('translate')
  expect(api.find('set_keeps')!.body.keys).toHaveLength(0)
  // With nothing kept, the whole Accepted panel disappears.
  await expect(page.locator('.kept-toggle', { hasText: 'accepted item' })).toHaveCount(0)
})

test('area History reverts a translate run', async ({ page }) => {
  const api = await mockApi(page, { revert_change: { ok: true, reverted: 3 } })
  await openTranslate(page)

  // Expand the area history (its toggle counts "changes", not "accepted items").
  await page.locator('.kept-toggle', { hasText: 'change' }).click()
  const entry = page.locator('.ch-entry', { hasText: '12 translated' })
  await expect(entry).toBeVisible()

  // Run-level revert has an inline confirm.
  await entry.locator('.ch-revert', { hasText: 'revert run' }).click()
  await entry.locator('.mat-yes').click()

  await expect.poll(() => api.find('revert_change')?.body.id).toBe('1783622600000')
  // Inline confirm collapses back once the revert is dispatched. (The status
  // toast is not asserted here: the follow-up re-analyze overwrites it with
  // "Analysis ✓" before it can be observed.)
  await expect(entry.locator('.mat-yes')).toHaveCount(0)
})

test('empty state: nothing left to translate + no detected language', async ({ page }) => {
  await mockApi(page, {
    plan_translate: () => ({
      ok: true, count: 0, kept: [], target: 'en', engine: 'google',
      detected: { counts: {}, total: 0, dominant: '' }, diff: [],
    }),
  })
  await openTranslate(page)

  await expect(page.locator('.head-count')).toContainText('nothing to change')
  await expect(page.locator('.rename-list .sg-row')).toHaveCount(0)
  await expect(page.locator('.wb-scroll')).toContainText('Every name is already English')
  await expect(page.locator('.wb-side')).toContainText('Run an analysis to detect the language')
})
