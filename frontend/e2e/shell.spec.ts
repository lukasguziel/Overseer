// App shell: boot behind the preloader, tab navigation, global re-analyze.
// Also the pattern every area spec follows — mockApi() first, goto('/'),
// interact, assert the API call log + the visible reaction.
import { test, expect } from '@playwright/test'
import { mockApi } from './mock'

test('boots into the Overview with the fake scene', async ({ page }) => {
  const api = await mockApi(page)
  await page.goto('/')
  await expect(page.locator('.brand-title')).toContainText('Overseer')
  await expect(page.locator('.scene-name')).toHaveText('penthouse_loft_final.c4d')
  expect(api.count('analyze')).toBeGreaterThan(0)
})

test('every active tab opens without an error banner', async ({ page }) => {
  await mockApi(page)
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  const labels = ['Naming', 'Translate', 'Layers', 'Materials', 'Tags',
    'Files', 'Assets', 'Generators', 'Sims', 'Misc', 'Overview']
  for (const label of labels) {
    await page.locator('nav.tabs button.tab', { hasText: label }).first().click()
    await expect(page.locator('.error')).toHaveCount(0)
  }
})

test('the refresh button re-analyzes the scene', async ({ page }) => {
  const api = await mockApi(page)
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  const before = api.count('analyze')
  await page.locator('.refresh-btn').click()
  await expect.poll(() => api.count('analyze')).toBeGreaterThan(before)
})
