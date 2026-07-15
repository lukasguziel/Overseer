// E2E coverage of the Materials tab: the unused-materials worklist
// (MaterialsTab) and the Textures area (TexturesSection) with its filters,
// per-row decisions and the three modals (Collect / Shrink / Confirm).
// Every test mocks /api/* fresh, boots on the Overview, then opens Materials.
// For each interaction we assert BOTH the fired op + payload (via the mock
// call log) and a visible UI reaction (status text, modal, list content).
import { test, expect, type Page } from '@playwright/test'
import { mockApi, type ApiLog } from './mock'
// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore - plain-JS fixture module without type declarations
import * as fx from './fixtures.mjs'

// A 1x1 transparent PNG, so an overridden preview op yields a real <img>.
const PNG = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='

// Deep-clone the shared fixture report so a test can hand back a mutated scene
// from a stateful analyze override without touching fixtures.mjs.
function cloneReport(): any {
  return structuredClone(fx.report)
}
// Report with the given materials removed from the unused worklist — models
// the re-analysis a delete triggers.
function reportWithoutMaterials(removed: string[]): any {
  const r = cloneReport()
  r.materials.unused = r.materials.unused.filter((n: string) => !removed.includes(n))
  r.materials.deletable_count = r.materials.unused.length
  return r
}
// Report with the given texture paths flagged accepted-as-missing — models the
// re-analysis an accept triggers (accepted rows drop out of the worklist).
function reportWithTexAccepted(paths: string[]): any {
  const r = cloneReport()
  for (const arr of [r.textures.absolute, r.textures.relative]) {
    for (const e of arr) if (paths.includes(e.path)) e.accepted = true
  }
  r.textures.accepted_all = paths
  return r
}

async function openMaterials(page: Page): Promise<void> {
  await page.goto('/')
  await expect(page.locator('.scene-name')).toBeVisible()
  await page.locator('nav.tabs button.tab', { hasText: 'Materials' }).first().click()
  await expect(page.locator('.wb-preview-head h3', { hasText: 'Unused materials' })).toBeVisible()
}

// The map-count in the Textures area header (distinct from the materials one).
const mapsCount = (page: Page) =>
  page.locator('.wb-preview-head', { hasText: 'Maps' }).locator('.head-count')
const status = (page: Page) => page.locator('.statusbar-text')
const texRow = (page: Page, text: string) =>
  page.locator('.dg-tr.dg-click', { hasText: text })

// ---- Materials worklist ----------------------------------------------------

test('renders the material stats and the four unused rows', async ({ page }) => {
  await mockApi(page)
  await openMaterials(page)
  const substats = page.locator('.substats').first()
  await expect(substats).toContainText('84')       // total
  await expect(substats).toContainText('4')        // unused / deletable
  await expect(substats).toContainText('missing tex')
  for (const nm of ['Old_Wood_Oak', 'Brass_v1', 'Test_Red', 'Fabric_Sample_02']) {
    await expect(page.locator('.sg-row', { hasText: nm })).toBeVisible()
  }
})

test('clicking a material row focuses it in Cinema 4D', async ({ page }) => {
  const api = await mockApi(page, {
    focus_material: { ok: true, object: 'Sofa_Body_Hi' },
  })
  await openMaterials(page)
  await page.locator('.sg-row', { hasText: 'Old_Wood_Oak' }).locator('.sg-body').click()
  await expect.poll(() => api.find('focus_material')?.body).toMatchObject({ name: 'Old_Wood_Oak' })
  await expect(status(page)).toContainText('Selected')
})

test('the per-row trash button deletes one material', async ({ page }) => {
  const deleted: string[] = []
  const api = await mockApi(page, {
    delete_material: (b) => { deleted.push(String(b.name)); return { ok: true, deleted: true } },
    analyze: () => ({ ok: true, report: reportWithoutMaterials(deleted) }),
  })
  await openMaterials(page)
  await page.locator('.sg-row', { hasText: 'Old_Wood_Oak' }).locator('.rn-ok').click()
  await expect.poll(() => api.find('delete_material')?.body)
    .toMatchObject({ name: 'Old_Wood_Oak', include_hidden: false })
  // Re-analysis drops the deleted material from the worklist.
  await expect(page.locator('.sg-row', { hasText: 'Old_Wood_Oak' })).toHaveCount(0)
  await expect(page.locator('.wb-preview-head', { hasText: 'Unused materials' })
    .locator('.head-count')).toContainText('3 changes')
})

test('the grey check accepts one material as-is', async ({ page }) => {
  const api = await mockApi(page)
  await openMaterials(page)
  await page.locator('.sg-row', { hasText: 'Brass_v1' }).locator('.rn-keep').click()
  await expect.poll(() => {
    const c = api.find('set_keeps')
    return c ? { section: c.body.section, has: (c.body.keys as string[]).includes('Brass_v1') } : undefined
  }).toMatchObject({ section: 'materials', has: true })
  await expect(status(page)).toContainText('Accepted')
  await expect(status(page)).toContainText('Brass_v1')
})

test('Delete all: cancel fires nothing, confirm deletes every unused material', async ({ page }) => {
  let deleted = false
  const api = await mockApi(page, {
    delete_unused_materials: (b) => {
      expect(b.include_hidden).toBe(false)
      deleted = true
      return { ok: true, deleted: 4 }
    },
    analyze: () => ({ ok: true, report: deleted ? reportWithoutMaterials(fx.report.materials.unused) : cloneReport() }),
  })
  await openMaterials(page)

  // Open then cancel — the confirm modal disappears and no op fires.
  await page.getByRole('button', { name: 'Delete all', exact: true }).click()
  await expect(page.locator('.confirm-title', { hasText: 'Delete all' })).toBeVisible()
  await page.locator('.confirm-box .ghost').click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('delete_unused_materials')).toBe(0)

  // Open then confirm — the worklist empties.
  await page.getByRole('button', { name: 'Delete all', exact: true }).click()
  await page.locator('.confirm-box .apply').click()
  await expect.poll(() => api.count('delete_unused_materials')).toBe(1)
  await expect(page.locator('.wb-preview-head', { hasText: 'Unused materials' })
    .locator('.head-count')).toContainText('nothing to change')
})

test('Keep all as-is: confirm accepts every unused material', async ({ page }) => {
  const api = await mockApi(page)
  await openMaterials(page)
  await page.getByRole('button', { name: 'Keep all as-is', exact: true }).click()
  await expect(page.locator('.confirm-title', { hasText: 'Keep all as-is' })).toBeVisible()
  // Cancel first: nothing persisted.
  await page.locator('.confirm-box .ghost').click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('set_keeps')).toBe(0)
  // Now confirm: all four unused names go to the materials keep list (the
  // already-accepted Chrome_Spare rides along, so the payload holds five).
  await page.getByRole('button', { name: 'Keep all as-is', exact: true }).click()
  await page.locator('.confirm-box .apply').click()
  await expect.poll(() => {
    const c = api.find('set_keeps')
    if (!c) return undefined
    const keys = c.body.keys as string[]
    return {
      section: c.body.section,
      all: ['Old_Wood_Oak', 'Brass_v1', 'Test_Red', 'Fabric_Sample_02'].every((n) => keys.includes(n)),
    }
  }).toMatchObject({ section: 'materials', all: true })
  await expect(status(page)).toContainText('Accepted 4 items as-is')
})

// ---- Textures: list, filters, focus ---------------------------------------

test('the textures list shows every referenced map', async ({ page }) => {
  const api = await mockApi(page)
  await openMaterials(page)
  await expect(mapsCount(page)).toContainText('7 maps')
  await expect(texRow(page, 'parquet_diffuse_8k.jpg')).toBeVisible()
  await expect(texRow(page, 'linen_normal_4k.png')).toBeVisible()  // the missing one
  // Row click selects the material in C4D.
  await texRow(page, 'concrete_diffuse_8k.jpg').locator('.dg-cell-file .dg-cut').click()
  await expect.poll(() => api.find('focus_material')?.body).toMatchObject({ name: 'Concrete_Wall' })
})

test('the search box narrows the texture list', async ({ page }) => {
  await mockApi(page)
  await openMaterials(page)
  await page.locator('input.search').fill('concrete')
  await expect(mapsCount(page)).toContainText('1 map')
  await expect(texRow(page, 'concrete_diffuse_8k.jpg')).toBeVisible()
  await expect(texRow(page, 'parquet_diffuse_8k.jpg')).toHaveCount(0)
  // A miss shows the search-specific empty note.
  await page.locator('input.search').fill('zzz-nothing')
  await expect(page.locator('.empty-note', { hasText: 'No textures match the search' })).toBeVisible()
})

test('the path-status chips filter the texture list', async ({ page }) => {
  await mockApi(page)
  await openMaterials(page)
  const absChip = page.locator('.chip-btn', { hasText: 'Absolute' })
  await expect(absChip).toContainText('2')
  await absChip.click()
  await expect(mapsCount(page)).toContainText('2 maps')
  await expect(texRow(page, 'parquet_diffuse_8k.jpg')).toBeVisible()
  await expect(texRow(page, 'concrete_diffuse_8k.jpg')).toHaveCount(0)   // relative, filtered out
  // Toggling the active chip clears the filter.
  await absChip.click()
  await expect(mapsCount(page)).toContainText('7 maps')
  // Missing chip narrows to the one broken reference.
  await page.locator('.chip-btn', { hasText: 'Missing' }).click()
  await expect(mapsCount(page)).toContainText('1 map')
  await expect(texRow(page, 'linen_normal_4k.png')).toBeVisible()
})

test('the resolution chips filter the texture list', async ({ page }) => {
  await mockApi(page)
  await openMaterials(page)
  const chip8k = page.locator('.chip-btn', { hasText: /^8K/ })
  await expect(chip8k).toContainText('2')
  await chip8k.click()
  await expect(mapsCount(page)).toContainText('2 maps')
  await expect(texRow(page, 'parquet_diffuse_8k.jpg')).toBeVisible()
  await expect(texRow(page, 'concrete_diffuse_8k.jpg')).toBeVisible()
  await expect(texRow(page, 'brass_rough_2k.png')).toHaveCount(0)
})

// ---- Textures: header actions (folder-scoped) ------------------------------

test('Copy & relink: the folder modal collects out-of-project maps', async ({ page }) => {
  const api = await mockApi(page, {
    collect_textures: { ok: true, copied: 1, relinked: 4, skipped: 0, diag: [] },
  })
  await openMaterials(page)
  // Open then cancel.
  await page.getByRole('button', { name: 'Copy & relink 1' }).click()
  await expect(page.locator('.confirm-title', { hasText: 'Copy textures into the project' })).toBeVisible()
  await page.locator('.confirm-box .ghost').click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('collect_textures')).toBe(0)
  // Open, change the subfolder, confirm.
  await page.getByRole('button', { name: 'Copy & relink 1' }).click()
  await page.locator('.confirm-box .nl-input').fill('maps')
  await page.locator('.confirm-box .act').click()
  await expect.poll(() => api.find('collect_textures')?.body).toMatchObject({ subdir: 'maps' })
  // The follow-up re-analysis owns the status line; the visible reaction here
  // is the modal closing.
  await expect(page.locator('.confirm-box')).toHaveCount(0)
})

test('Relink missing: pick a folder, then confirm the search', async ({ page }) => {
  const api = await mockApi(page, {
    pick_folder: { ok: true, path: 'D:/BACKUP/textures' },
    relink_textures: { ok: true, relinked: 2, not_found: 0, skipped: 0 },
  })
  await openMaterials(page)
  await page.getByRole('button', { name: 'Relink 2 missing' }).click()
  await expect.poll(() => api.count('pick_folder')).toBe(1)
  const modal = page.locator('.confirm-title', { hasText: 'Relink missing textures' })
  await expect(modal).toBeVisible()
  // Cancel leaves the scene untouched.
  await page.locator('.confirm-box .ghost').click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('relink_textures')).toBe(0)
  // Re-open (fresh pick) and confirm.
  await page.getByRole('button', { name: 'Relink 2 missing' }).click()
  await page.locator('.confirm-box .apply').click()
  await expect.poll(() => api.find('relink_textures')?.body).toMatchObject({ folder: 'D:/BACKUP/textures' })
})

test('Clear missing: the danger modal blanks dead references', async ({ page }) => {
  const api = await mockApi(page, {
    clear_missing_textures: { ok: true, cleared: 2, skipped: 0 },
  })
  await openMaterials(page)
  await page.getByRole('button', { name: 'Clear 2 missing' }).click()
  await expect(page.locator('.confirm-title', { hasText: 'Clear missing references' })).toBeVisible()
  // Cancel first.
  await page.locator('.confirm-box .ghost').click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('clear_missing_textures')).toBe(0)
  // Confirm.
  await page.getByRole('button', { name: 'Clear 2 missing' }).click()
  await page.locator('.confirm-box .apply').click()
  await expect.poll(() => api.count('clear_missing_textures')).toBe(1)
})

test('Accept missing: the header button keeps every missing map', async ({ page }) => {
  let accepted: string[] = []
  const api = await mockApi(page, {
    set_keeps: (b) => { if (b.section === 'textures') accepted = b.keys as string[]; return { ok: true } },
    analyze: () => ({ ok: true, report: reportWithTexAccepted(accepted) }),
  })
  await openMaterials(page)
  await expect(texRow(page, 'linen_normal_4k.png')).toBeVisible()
  await page.getByRole('button', { name: 'Accept 2 missing' }).click()
  await expect.poll(() => {
    const c = api.find('set_keeps')
    return c ? { section: c.body.section, has: (c.body.keys as string[]).includes('E:/OLD/linen_normal_4k.png') } : undefined
  }).toMatchObject({ section: 'textures', has: true })
  // Re-analysis moves the accepted map out of the worklist.
  await expect(texRow(page, 'linen_normal_4k.png')).toHaveCount(0)
})

// ---- Textures: per-row decisions -------------------------------------------

test('a present map can be shrunk through the Shrink modal', async ({ page }) => {
  const api = await mockApi(page, {
    texture_resize: { ok: true, resized: 1, skipped: 0, results: [] },
  })
  await openMaterials(page)
  const row = texRow(page, 'concrete_diffuse_8k.jpg')
  await row.locator('button[title^="Shrink this map"]').click()
  await expect(page.locator('.confirm-title', { hasText: 'Shrink texture' })).toBeVisible()
  // Cancel path.
  await page.locator('.confirm-box .ghost').click()
  await expect(page.locator('.confirm-box')).toHaveCount(0)
  expect(api.count('texture_resize')).toBe(0)
  // Re-open, pick 25%, confirm.
  await row.locator('button[title^="Shrink this map"]').click()
  await page.locator('.shrink-size', { hasText: '25%' }).click()
  await page.locator('.confirm-box', { hasText: 'Shrink texture' }).getByRole('button', { name: /Shrink to/ }).click()
  await expect.poll(() => api.find('texture_resize')?.body)
    .toMatchObject({ paths: ['tex/concrete_diffuse_8k.jpg'], percent: 25 })
  // The Shrink dialog closes once the resize is dispatched.
  await expect(page.locator('.confirm-box')).toHaveCount(0)
})

test('an out-of-project map is copied in via the per-row Collect modal', async ({ page }) => {
  const api = await mockApi(page, {
    texture_owners: { ok: true, materials: ['Parquet_Oak', 'Floor_Trim'] },
    collect_textures: { ok: true, copied: 1, relinked: 2, skipped: 0, diag: [] },
  })
  await openMaterials(page)
  const row = texRow(page, 'parquet_diffuse_8k.jpg')
  await row.locator('button[title^="Copy this file into the project"]').click()
  await expect.poll(() => api.find('texture_owners')?.body)
    .toMatchObject({ path: 'C:/Users/artist/Downloads/parquet_diffuse_8k.jpg' })
  const modal = page.locator('.confirm-box', { hasText: 'Copy this texture into the project' })
  await expect(modal).toBeVisible()
  await expect(modal).toContainText('Parquet_Oak, Floor_Trim')   // relink blast radius
  await modal.locator('.act').click()
  await expect.poll(() => api.find('collect_textures')?.body)
    .toMatchObject({ subdir: 'tex', paths: ['C:/Users/artist/Downloads/parquet_diffuse_8k.jpg'] })
  // The re-analysis takes over the status line; the modal closing is the
  // reliable visible reaction.
  await expect(page.locator('.confirm-box')).toHaveCount(0)
})

test('a relocatable absolute path is rewritten relative via the row button', async ({ page }) => {
  const api = await mockApi(page, {
    texture_repath: { ok: true, changed: 1, diag: [] },
  })
  await openMaterials(page)
  await texRow(page, 'fabric_boucle_4k.exr').locator('button.tex-chip').click()
  await expect.poll(() => api.find('texture_repath')?.body)
    .toMatchObject({ paths: ['D:/3D/PROJECTS/PENTHOUSE/tex/fabric_boucle_4k.exr'], mode: 'relative' })
  await expect(status(page)).toContainText('Rewrote 1 path to relative')
})

test('a missing map can be re-picked from the C4D file dialog', async ({ page }) => {
  const api = await mockApi(page, {
    pick_texture_path: { ok: true, picked: 'D:/3D/PROJECTS/PENTHOUSE/tex/linen_normal_4k.png' },
  })
  await openMaterials(page)
  await texRow(page, 'linen_normal_4k.png').locator('button[title^="Browse"]').click()
  await expect.poll(() => api.find('pick_texture_path')?.body)
    .toMatchObject({ path: 'E:/OLD/linen_normal_4k.png', material: 'Curtain_Linen' })
  await expect(status(page)).toContainText('Reference →')
})

test('a missing map reference can be cleared', async ({ page }) => {
  const api = await mockApi(page)
  await openMaterials(page)
  await texRow(page, 'linen_normal_4k.png').locator('button.rn-no').click()
  await expect.poll(() => api.find('set_texture_path')?.body)
    .toMatchObject({ path: 'E:/OLD/linen_normal_4k.png', new_path: '', material: 'Curtain_Linen' })
  await expect(status(page)).toContainText('Reference cleared')
})

test('a missing map can be accepted as-is from its row', async ({ page }) => {
  let accepted: string[] = []
  const api = await mockApi(page, {
    set_keeps: (b) => { if (b.section === 'textures') accepted = b.keys as string[]; return { ok: true } },
    analyze: () => ({ ok: true, report: reportWithTexAccepted(accepted) }),
  })
  await openMaterials(page)
  await texRow(page, 'linen_normal_4k.png').locator('button[title^="Accept as-is"]').click()
  await expect.poll(() => {
    const c = api.find('set_keeps')
    return c ? { section: c.body.section, has: (c.body.keys as string[]).includes('E:/OLD/linen_normal_4k.png') } : undefined
  }).toMatchObject({ section: 'textures', has: true })
  await expect(texRow(page, 'linen_normal_4k.png')).toHaveCount(0)
})

test('clicking a texture thumbnail opens the image', async ({ page }) => {
  const api = await mockApi(page, {
    // Hand back a real preview image for every requested path so the row
    // renders an openable thumbnail instead of the status dot.
    texture_previews: (b) => ({
      ok: true,
      previews: Object.fromEntries(((b.paths as string[]) || []).map((p) => [p, PNG])),
    }),
  })
  await openMaterials(page)
  const thumb = texRow(page, 'concrete_diffuse_8k.jpg').locator('.tex-thumb-wrap.openable')
  await expect(thumb).toBeVisible()
  await thumb.click()
  await expect.poll(() => api.find('open_file')?.body)
    .toMatchObject({ path: 'D:/3D/PROJECTS/PENTHOUSE/tex/concrete_diffuse_8k.jpg' })
})

// ---- Empty / error state ---------------------------------------------------

test('a failed texture scan shows the error, materials still render', async ({ page }) => {
  await mockApi(page, {
    analyze: () => {
      const r = cloneReport()
      r.textures = null
      r.textures_error = 'texture scan crashed'
      return { ok: true, report: r }
    },
  })
  await openMaterials(page)
  // The materials worklist is unaffected.
  await expect(page.locator('.sg-row', { hasText: 'Old_Wood_Oak' })).toBeVisible()
  // The textures area degrades to its empty + error rendering.
  await expect(page.locator('.empty-note', { hasText: 'No texture data' })).toBeVisible()
  await expect(page.locator('.example.warn', { hasText: 'Texture scan failed' })).toBeVisible()
  await expect(page.locator('.example.warn code', { hasText: 'texture scan crashed' })).toBeVisible()
})
