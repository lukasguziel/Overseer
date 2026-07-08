// Sample data for README screenshots: a plausible 1.2 GB interior scene with
// 40M polygons, German object names, unused materials and heavy textures.
// Everything the web UI requests from /api/* is answered from this module —
// no Cinema 4D involved. Keep numbers internally consistent when editing.

const GB = 1024 * 1024 * 1024
const MB = 1024 * 1024

// ---- scene tree (preorder; depth/children must stay consistent) -----------
let guid = 0
const nodes = []
function add(name, type, category, depth, opts = {}) {
  nodes.push({
    guid: guid++, name, type, category, depth,
    children: 0, polygons: opts.polys || 0, points: opts.points || 0,
    visible: opts.visible !== false, layer: opts.layer ?? null,
  })
  return nodes[nodes.length - 1]
}
function group(name, depth, fill) {
  const g = add(name, 'Null', 'null', depth)
  const before = nodes.length
  fill(depth + 1)
  g.children = nodes.length - before
  return g
}

group('Wohnzimmer', 0, (d) => {
  group('Sofa_Gruppe', d, (d2) => {
    add('Sofa_Korpus_Hi', 'Polygon', 'mesh', d2, { polys: 4218330, points: 2110040 })
    add('Sofa_Kissen_links', 'Polygon', 'mesh', d2, { polys: 1284002, points: 644120 })
    add('Sofa_Kissen_rechts', 'Polygon', 'mesh', d2, { polys: 1281776, points: 642950 })
    add('Decke_Wolle', 'Cloth Surface', 'mesh', d2, { polys: 388211, points: 196700 })
  })
  add('Couchtisch', 'Polygon', 'mesh', d, { polys: 902114, points: 455230 })
  add('Teppich', 'Polygon', 'mesh', d, { polys: 2110450, points: 1055600 })
  for (let i = 1; i <= 4; i++) {
    add('Stuhl', 'Polygon', 'mesh', d, { polys: 611240 + i * 1000, points: 305100 })
  }
  add('Regal_Wand', 'Polygon', 'mesh', d, { polys: 340020, points: 171200 })
  add('Vorhang_links', 'Cloth Surface', 'mesh', d, { polys: 1893340, points: 948000 })
  add('Vorhang_rechts', 'Cloth Surface', 'mesh', d, { polys: 1878020, points: 940100 })
})

group('Kueche', 0, (d) => {
  add('kuechenzeile_unten', 'Polygon', 'mesh', d, { polys: 3182240, points: 1590050 })
  add('kuechenzeile_oben', 'Polygon', 'mesh', d, { polys: 2544190, points: 1274400 })
  add('arbeitsplatte', 'Polygon', 'mesh', d, { polys: 122400, points: 61800 })
  add('spuele', 'Polygon', 'mesh', d, { polys: 488210, points: 244600 })
  add('Wasserhahn', 'Polygon', 'mesh', d, { polys: 902330, points: 452100 })
  group('Geschirr', d, (d2) => {
    for (let i = 1; i <= 6; i++) {
      add(`Teller.${i}`, 'Polygon', 'mesh', d2, { polys: 96420, points: 48400 })
    }
    add('Tasse', 'Polygon', 'mesh', d2, { polys: 84210, points: 42300 })
    add('Tasse', 'Polygon', 'mesh', d2, { polys: 84210, points: 42300 })
  })
})

group('Schlafzimmer', 0, (d) => {
  add('Bett_Rahmen', 'Polygon', 'mesh', d, { polys: 1422410, points: 712300 })
  add('Matratze', 'Polygon', 'mesh', d, { polys: 688240, points: 344800 })
  add('kissen_01', 'Polygon', 'mesh', d, { polys: 494200, points: 247600 })
  add('kissen_2', 'Polygon', 'mesh', d, { polys: 492180, points: 246500 })
  add('Kleiderschrank', 'Polygon', 'mesh', d, { polys: 1922440, points: 962000 })
  add('Nachttisch_links', 'Polygon', 'mesh', d, { polys: 311240, points: 156100 })
  add('Nachttisch_rechts', 'Polygon', 'mesh', d, { polys: 309980, points: 155400 })
})

group('Architektur', 0, (d) => {
  add('Waende_EG', 'Polygon', 'mesh', d, { polys: 1233400, points: 618000 })
  add('boden_parkett', 'Polygon', 'mesh', d, { polys: 2988420, points: 1495000 })
  add('decke', 'Polygon', 'mesh', d, { polys: 424420, points: 212800 })
  add('Fenster_Front', 'Polygon', 'mesh', d, { polys: 866240, points: 433800 })
  add('Fenster_Seite', 'Polygon', 'mesh', d, { polys: 864110, points: 432700 })
  add('Tuer_Eingang', 'Polygon', 'mesh', d, { polys: 353240, points: 177000 })
  group('Treppe', d, (d2) => {
    add('Stufen', 'Polygon', 'mesh', d2, { polys: 622140, points: 311500 })
    add('gelaender_kurve', 'Spline', 'spline', d2)
    add('handlauf_profil', 'Spline', 'spline', d2)
  })
})

group('Cameras', 0, (d) => {
  add('Cam_Hero', 'Camera', 'camera', d, { layer: 'Cameras' })
  add('Cam_Detail_Kueche', 'Camera', 'camera', d, { layer: 'Cameras' })
  add('Cam_Totale', 'Camera', 'camera', d)
})

group('Lights', 0, (d) => {
  add('LGT_Key_Fenster', 'Area Light', 'light', d, { layer: 'Lights' })
  add('LGT_Fill_Decke', 'Area Light', 'light', d, { layer: 'Lights' })
  add('LGT_Spot_Regal', 'Spot Light', 'light', d)
  add('deckenlampe_esstisch', 'Area Light', 'light', d)
  add('stehlampe', 'Area Light', 'light', d)
  add('HDRI_Dome', 'Sky', 'light', d)
})

// Loose objects at root: junk names, hidden helpers, splines without prefix.
add('Cube', 'Polygon', 'mesh', 0, { polys: 12, points: 8 })
add('Cube.1', 'Polygon', 'mesh', 0, { polys: 12, points: 8 })
add('Null', 'Null', 'null', 0)
add('pflanze_gross', 'Polygon', 'mesh', 0, { polys: 3411240, points: 1706000 })
add('deko_vase', 'Polygon', 'mesh', 0, { polys: 288410, points: 144300 })
add('Bilderrahmen_Set', 'Polygon', 'mesh', 0, { polys: 96240, points: 48200 })
add('kabel_kanal', 'Spline', 'spline', 0)
add('Proxy_Baum_aussen', 'Instance', 'other', 0, { visible: false })
add('Messebau_alt', 'Polygon', 'mesh', 0, { polys: 1422400, points: 711000, visible: false })

// ---- report ----------------------------------------------------------------
export const report = {
  file: 'penthouse_loft_final.c4d',
  doc_name: 'penthouse_loft_final.c4d',
  object_count: 1847,
  max_depth: 7,
  total_polys: 40312774,
  total_points: 20481930,
  file_size: Math.round(1.2 * GB),
  structure_compliance: 0.62,
  analyzed_at: '2026-07-08 19:42:00',
  types: {
    Polygon: 1204, Null: 216, 'Area Light': 31, 'Spot Light': 7, Camera: 6,
    Spline: 74, Instance: 214, 'Cloth Surface': 41, Sky: 1, Other: 53,
  },
  categories: { mesh: 1245, null: 216, light: 39, camera: 6, spline: 74, other: 267 },
  casing: { PascalCase: 612, Capitalized: 493, lower: 388, mixed: 354 },
  language: { de: 812, en: 566, unknown: 469 },
  nodes,
  misplaced: Array.from({ length: 37 }, (_, i) => ({ guid: 900 + i })),
  hidden_count: 23,
  include_hidden: false,
  dirty: 4211,
  sel: 0,
  materials: {
    total: 84,
    unused: ['Alt_Holz_Eiche', 'Messing_v1', 'Test_Rot', 'Stoff_Probe_02', 'Beton_alt'],
    only_hidden: ['Beton_alt'],
    accepted: ['Chrom_Reserve'],
    accepted_all: ['Chrom_Reserve'],
    deletable_count: 4,
    missing: [
      { material: 'Parkett_Eiche', file: 'parkett_diffuse_8k.jpg' },
      { material: 'Vorhang_Leinen', file: 'leinen_normal_4k.png' },
    ],
    missing_textures: 2,
  },
  textures: {
    doc_path: 'D:/3D/PROJECTS/PENTHOUSE',
    total: 96,
    absolute_count: 3,
    relative_count: 93,
    missing_count: 2,
    relocatable_count: 2,
    total_bytes: Math.round(6.4 * GB),
    absolute: [
      { material: 'Parkett_Eiche', used: true, file: 'parkett_diffuse_8k.jpg',
        path: 'C:/Users/artist/Downloads/parkett_diffuse_8k.jpg',
        resolved: 'C:/Users/artist/Downloads/parkett_diffuse_8k.jpg',
        absolute: true, exists: true, missing: false, relocatable: false,
        rel_target: '', bytes: 212 * MB, width: 8192, height: 8192, res_tag: '8K' },
      { material: 'Sofa_Stoff', used: true, file: 'stoff_boucle_4k.exr',
        path: 'D:/3D/PROJECTS/PENTHOUSE/tex/stoff_boucle_4k.exr',
        resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/stoff_boucle_4k.exr',
        absolute: true, exists: true, missing: false, relocatable: true,
        rel_target: 'tex/stoff_boucle_4k.exr', bytes: 96 * MB,
        width: 4096, height: 4096, res_tag: '4K' },
      { material: 'Vorhang_Leinen', used: true, file: 'leinen_normal_4k.png',
        path: 'E:/ALT/leinen_normal_4k.png', resolved: '',
        absolute: true, exists: false, missing: true, relocatable: false,
        rel_target: '', bytes: 0, width: 0, height: 0, res_tag: '' },
    ],
    relative: [
      { material: 'Beton_Wand', used: true, file: 'beton_diffuse_8k.jpg',
        path: 'tex/beton_diffuse_8k.jpg',
        resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/beton_diffuse_8k.jpg',
        absolute: false, exists: true, missing: false, relocatable: false,
        rel_target: '', bytes: 188 * MB, width: 8192, height: 8192, res_tag: '8K' },
      { material: 'Teppich_Wolle', used: true, file: 'teppich_height_4k.tif',
        path: 'tex/teppich_height_4k.tif',
        resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/teppich_height_4k.tif',
        absolute: false, exists: true, missing: false, relocatable: false,
        rel_target: '', bytes: 64 * MB, width: 4096, height: 4096, res_tag: '4K' },
      { material: 'Messing_Lampe', used: true, file: 'messing_rough_2k.png',
        path: 'tex/messing_rough_2k.png',
        resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/messing_rough_2k.png',
        absolute: false, exists: true, missing: false, relocatable: false,
        rel_target: '', bytes: 9 * MB, width: 2048, height: 2048, res_tag: '2K' },
      { material: 'Deko_Vase', used: false, file: 'keramik_glaze_2k.jpg',
        path: 'tex/keramik_glaze_2k.jpg',
        resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/keramik_glaze_2k.jpg',
        absolute: false, exists: true, missing: false, relocatable: false,
        rel_target: '', bytes: 6 * MB, width: 2048, height: 2048, res_tag: '2K' },
    ],
  },
  layers_report: {
    layers: [
      { name: 'Lights', color: [0.98, 0.76, 0.2], solo: false, view: true,
        render: true, locked: false, objects: 2, polys: 0, empty: false },
      { name: 'Cameras', color: [0.35, 0.7, 0.98], solo: false, view: true,
        render: true, locked: false, objects: 2, polys: 0, empty: false },
      { name: 'Proxies', color: [0.6, 0.6, 0.62], solo: false, view: false,
        render: true, locked: false, objects: 0, polys: 0, empty: true },
    ],
    no_layer: nodes.length - 4,
    total_layers: 3,
    empty_layers: 1,
  },
}

// ---- plans -----------------------------------------------------------------
const byName = (name) => nodes.filter((n) => n.name === name)
const g = (name, i = 0) => byName(name)[i]?.guid ?? 0

export const planNaming = {
  ok: true,
  count: 9,
  kept: ['HDRI_Dome'],
  diff: [
    { guid: g('kuechenzeile_unten'), old: 'kuechenzeile_unten', new: 'KuechenzeileUnten', rules: ['casing'] },
    { guid: g('kuechenzeile_oben'), old: 'kuechenzeile_oben', new: 'KuechenzeileOben', rules: ['casing'] },
    { guid: g('arbeitsplatte'), old: 'arbeitsplatte', new: 'Arbeitsplatte', rules: ['casing'] },
    { guid: g('boden_parkett'), old: 'boden_parkett', new: 'BodenParkett', rules: ['casing'] },
    { guid: g('kissen_01'), old: 'kissen_01', new: 'Kissen01', rules: ['casing', 'numbering'] },
    { guid: g('kissen_2'), old: 'kissen_2', new: 'Kissen02', rules: ['casing', 'numbering'] },
    { guid: g('Stuhl', 0), old: 'Stuhl', new: 'Stuhl01', rules: ['unique'] },
    { guid: g('Stuhl', 1), old: 'Stuhl', new: 'Stuhl02', rules: ['unique'] },
    { guid: g('Teller.1'), old: 'Teller.1', new: 'Teller01', rules: ['numbering'] },
  ],
}

export const planTranslate = {
  ok: true,
  count: 8,
  kept: ['Fenster_Front'],
  target: 'en',
  engine: 'offline',
  detected: { counts: { de: 812, en: 566, unknown: 469 }, total: 1847,
    dominant: 'de', de: 812, en: 566, unknown: 469 },
  diff: [
    { guid: g('Stuhl', 0), old: 'Stuhl', new: 'Chair', words: [['stuhl', 'chair']], lang: 'de' },
    { guid: g('Couchtisch'), old: 'Couchtisch', new: 'CoffeeTable', words: [['couchtisch', 'coffee table']], lang: 'de' },
    { guid: g('Teppich'), old: 'Teppich', new: 'Carpet', words: [['teppich', 'carpet']], lang: 'de' },
    { guid: g('Kleiderschrank'), old: 'Kleiderschrank', new: 'Wardrobe', words: [['kleiderschrank', 'wardrobe']], lang: 'de' },
    { guid: g('Waende_EG'), old: 'Waende_EG', new: 'Walls_EG', words: [['waende', 'walls']], lang: 'de' },
    { guid: g('spuele'), old: 'spuele', new: 'sink', words: [['spuele', 'sink']], lang: 'de' },
    { guid: g('Tuer_Eingang'), old: 'Tuer_Eingang', new: 'Door_Entrance', words: [['tuer', 'door'], ['eingang', 'entrance']], lang: 'de' },
    { guid: g('pflanze_gross'), old: 'pflanze_gross', new: 'plant_big', words: [['pflanze', 'plant'], ['gross', 'big']], lang: 'de' },
  ],
}

export const planLayers = {
  ok: true,
  count: 5,
  kept: [],
  by_layer: { Lights: 4, Cameras: 1 },
  diff: [
    { guid: g('LGT_Spot_Regal'), name: 'LGT_Spot_Regal', layer: 'Lights' },
    { guid: g('deckenlampe_esstisch'), name: 'deckenlampe_esstisch', layer: 'Lights' },
    { guid: g('stehlampe'), name: 'stehlampe', layer: 'Lights' },
    { guid: g('HDRI_Dome'), name: 'HDRI_Dome', layer: 'Lights' },
    { guid: g('Cam_Totale'), name: 'Cam_Totale', layer: 'Cameras' },
  ],
}

export const planStructure = {
  ok: true,
  count: 5,
  skipped: 2,
  kept: ['Messebau_alt'],
  diff: [
    { guid: g('pflanze_gross'), name: 'pflanze_gross', from: null, to: 'Deko' },
    { guid: g('deko_vase'), name: 'deko_vase', from: null, to: 'Deko' },
    { guid: g('Bilderrahmen_Set'), name: 'Bilderrahmen_Set', from: null, to: 'Deko' },
    { guid: g('Cam_Totale'), name: 'Cam_Totale', from: 'Cameras', to: 'Cameras' },
    { guid: g('kabel_kanal'), name: 'kabel_kanal', from: null, to: 'Technik' },
  ],
}

export const rules = {
  ok: true,
  groups: [
    { name: 'Cameras', priority: 90 },
    { name: 'Lights', priority: 85 },
    { name: 'Deko', priority: 50 },
    { name: 'Technik', priority: 40 },
  ],
}

export const presets = {
  ok: true,
  active: 'lukas-interior',
  presets: [
    { id: 'lukas-interior', name: 'Lukas — Interior', rules: 4,
      description: 'Personal convention learned from 3 archviz projects: PascalCase, 2-digit numbering, DE→EN off.',
      created_at: '2026-06-30 14:12:00',
      groups: ['Cameras', 'Lights', 'Deko', 'Technik'] },
    { id: 'studio-strict', name: 'Studio Strict', rules: 7,
      description: 'Strict delivery preset: English names, LGT_/CAM_ prefixes, layers per type.',
      created_at: '2026-05-18 09:30:00',
      groups: ['Cameras', 'Lights', 'Furniture', 'Architecture'] },
  ],
}

export const history = {
  ok: true,
  history: [
    { file: 'penthouse_loft_final.c4d', at: '2026-07-06 11:02:11', ts: 1783418531,
      objects: 1795, polys: 38102331, size: Math.round(1.14 * GB), compliance: 0.55 },
    { file: 'penthouse_loft_final.c4d', at: '2026-07-07 16:44:03', ts: 1783525443,
      objects: 1831, polys: 39558214, size: Math.round(1.18 * GB), compliance: 0.58 },
    { file: 'penthouse_loft_final.c4d', at: '2026-07-08 19:42:00', ts: 1783622520,
      objects: 1847, polys: 40312774, size: Math.round(1.2 * GB), compliance: 0.62 },
  ],
}

export const changes = {
  ok: true,
  changes: [
    { id: '1783622600000', ts: 1783622600, at: '2026-07-08 19:43:20',
      kind: 'translate', summary: '12 translated', doc: 'penthouse_loft_final.c4d',
      revertible: true, reverted: false,
      items: [
        { sid: 101, name: 'Chair01', field: 'name', before: 'Stuhl01', after: 'Chair01' },
        { sid: 102, name: 'Carpet', field: 'name', before: 'Teppich', after: 'Carpet' },
        { sid: 103, name: 'Wardrobe', field: 'name', before: 'Kleiderschrank', after: 'Wardrobe' },
      ] },
    { id: '1783619000000', ts: 1783619000, at: '2026-07-08 18:43:20',
      kind: 'layers', summary: '38 assigned to layers', doc: 'penthouse_loft_final.c4d',
      revertible: true, reverted: false,
      items: [
        { sid: 201, name: 'LGT_Key_Fenster', field: 'layer', before: '', after: 'Lights' },
        { sid: 202, name: 'Cam_Hero', field: 'layer', before: '', after: 'Cameras' },
      ] },
    { id: '1783533000000', ts: 1783533000, at: '2026-07-07 18:50:00',
      kind: 'structure', summary: '21 moved', doc: 'penthouse_loft_final.c4d',
      revertible: true, reverted: true,
      items: [
        { sid: 301, name: 'deko_vase', field: 'parent', before: '', after: 'Deko' },
      ] },
  ],
}

export const detect = {
  ok: true,
  detect: { style: 'PascalCase', language: 'de', number_pad: 2, confidence: 0.83 },
}
