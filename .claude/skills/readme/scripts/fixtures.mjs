// Sample data for README screenshots: a plausible 1.2 GB interior scene with
// 40M polygons, English object names (the Translate tab demonstrates
// English -> French), unused materials and heavy textures. Everything the
// web UI requests from /api/* is answered from this module — no Cinema 4D
// involved. Keep numbers internally consistent when editing.

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

group('LivingRoom', 0, (d) => {
  group('Sofa_Set', d, (d2) => {
    add('Sofa_Body_Hi', 'Polygon', 'mesh', d2, { polys: 4218330, points: 2110040 })
    add('Sofa_Cushion_left', 'Polygon', 'mesh', d2, { polys: 1284002, points: 644120 })
    add('Sofa_Cushion_right', 'Polygon', 'mesh', d2, { polys: 1281776, points: 642950 })
    add('Blanket_Wool', 'Cloth Surface', 'mesh', d2, { polys: 388211, points: 196700 })
  })
  add('CoffeeTable', 'Polygon', 'mesh', d, { polys: 902114, points: 455230 })
  add('Rug', 'Polygon', 'mesh', d, { polys: 2110450, points: 1055600 })
  for (let i = 1; i <= 4; i++) {
    add('Chair', 'Polygon', 'mesh', d, { polys: 611240 + i * 1000, points: 305100 })
  }
  add('Shelf_Wall', 'Polygon', 'mesh', d, { polys: 340020, points: 171200 })
  add('Curtain_left', 'Cloth Surface', 'mesh', d, { polys: 1893340, points: 948000 })
  add('Curtain_right', 'Cloth Surface', 'mesh', d, { polys: 1878020, points: 940100 })
})

group('Kitchen', 0, (d) => {
  add('kitchen_cabinets_lower', 'Polygon', 'mesh', d, { polys: 3182240, points: 1590050 })
  add('kitchen_cabinets_upper', 'Polygon', 'mesh', d, { polys: 2544190, points: 1274400 })
  add('countertop', 'Polygon', 'mesh', d, { polys: 122400, points: 61800 })
  add('sink', 'Polygon', 'mesh', d, { polys: 488210, points: 244600 })
  add('Faucet', 'Polygon', 'mesh', d, { polys: 902330, points: 452100 })
  group('Dishes', d, (d2) => {
    for (let i = 1; i <= 6; i++) {
      add(`Plate.${i}`, 'Polygon', 'mesh', d2, { polys: 96420, points: 48400 })
    }
    add('Cup', 'Polygon', 'mesh', d2, { polys: 84210, points: 42300 })
    add('Cup', 'Polygon', 'mesh', d2, { polys: 84210, points: 42300 })
  })
})

group('Bedroom', 0, (d) => {
  add('Bed_Frame', 'Polygon', 'mesh', d, { polys: 1422410, points: 712300 })
  add('Mattress', 'Polygon', 'mesh', d, { polys: 688240, points: 344800 })
  add('pillow_01', 'Polygon', 'mesh', d, { polys: 494200, points: 247600 })
  add('pillow_2', 'Polygon', 'mesh', d, { polys: 492180, points: 246500 })
  add('Wardrobe', 'Polygon', 'mesh', d, { polys: 1922440, points: 962000 })
  add('Nightstand_left', 'Polygon', 'mesh', d, { polys: 311240, points: 156100 })
  add('Nightstand_right', 'Polygon', 'mesh', d, { polys: 309980, points: 155400 })
})

group('Architecture', 0, (d) => {
  add('Walls_GF', 'Polygon', 'mesh', d, { polys: 1233400, points: 618000 })
  add('floor_parquet', 'Polygon', 'mesh', d, { polys: 2988420, points: 1495000 })
  add('ceiling', 'Polygon', 'mesh', d, { polys: 424420, points: 212800 })
  add('Window_Front', 'Polygon', 'mesh', d, { polys: 866240, points: 433800 })
  add('Window_Side', 'Polygon', 'mesh', d, { polys: 864110, points: 432700 })
  add('Door_Entrance', 'Polygon', 'mesh', d, { polys: 353240, points: 177000 })
  group('Stairs', d, (d2) => {
    add('Steps', 'Polygon', 'mesh', d2, { polys: 622140, points: 311500 })
    add('railing_curve', 'Spline', 'spline', d2)
    add('handrail_profile', 'Spline', 'spline', d2)
  })
})

group('Cameras', 0, (d) => {
  add('Cam_Hero', 'Camera', 'camera', d, { layer: 'Cameras' })
  add('Cam_Detail_Kitchen', 'Camera', 'camera', d, { layer: 'Cameras' })
  add('Cam_Wide', 'Camera', 'camera', d)
})

group('Lights', 0, (d) => {
  add('LGT_Key_Window', 'Area Light', 'light', d, { layer: 'Lights' })
  add('LGT_Fill_Ceiling', 'Area Light', 'light', d, { layer: 'Lights' })
  add('LGT_Spot_Shelf', 'Spot Light', 'light', d)
  add('ceiling_lamp_dining', 'Area Light', 'light', d)
  add('floor_lamp', 'Area Light', 'light', d)
  add('HDRI_Dome', 'Sky', 'light', d)
})

// Loose objects at root: junk names, hidden helpers, splines without prefix.
add('Cube', 'Polygon', 'mesh', 0, { polys: 12, points: 8 })
add('Cube.1', 'Polygon', 'mesh', 0, { polys: 12, points: 8 })
add('Null', 'Null', 'null', 0)
add('plant_large', 'Polygon', 'mesh', 0, { polys: 3411240, points: 1706000 })
add('deco_vase', 'Polygon', 'mesh', 0, { polys: 288410, points: 144300 })
add('PictureFrame_Set', 'Polygon', 'mesh', 0, { polys: 96240, points: 48200 })
add('cable_duct', 'Spline', 'spline', 0)
add('Proxy_Tree_Outdoor', 'Instance', 'other', 0, { visible: false })
add('OldSet_backup', 'Polygon', 'mesh', 0, { polys: 1422400, points: 711000, visible: false })

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
  casing: { PascalCase: 812, Capitalized: 393, lower: 388, mixed: 254 },
  language: { en: 1288, unknown: 421, de: 138 },
  nodes,
  misplaced: Array.from({ length: 37 }, (_, i) => ({ guid: 900 + i })),
  hidden_count: 23,
  include_hidden: false,
  dirty: 4211,
  sel: 0,
  materials: {
    total: 84,
    // Visible-only scope: unused = used NOWHERE; hidden-only usage shows up
    // once "All objects" is active (only_hidden stays empty here).
    unused: ['Old_Wood_Oak', 'Brass_v1', 'Test_Red', 'Fabric_Sample_02'],
    only_hidden: [],
    accepted: ['Chrome_Spare'],
    accepted_all: ['Chrome_Spare'],
    deletable_count: 4,
    missing: [
      { material: 'Parquet_Oak', file: 'parquet_diffuse_8k.jpg' },
      { material: 'Curtain_Linen', file: 'linen_normal_4k.png' },
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
      { material: 'Parquet_Oak', used: true, file: 'parquet_diffuse_8k.jpg',
        path: 'C:/Users/artist/Downloads/parquet_diffuse_8k.jpg',
        resolved: 'C:/Users/artist/Downloads/parquet_diffuse_8k.jpg',
        absolute: true, exists: true, missing: false, relocatable: false,
        rel_target: '', bytes: 212 * MB, width: 8192, height: 8192, res_tag: '8K' },
      { material: 'Sofa_Fabric', used: true, file: 'fabric_boucle_4k.exr',
        path: 'D:/3D/PROJECTS/PENTHOUSE/tex/fabric_boucle_4k.exr',
        resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/fabric_boucle_4k.exr',
        absolute: true, exists: true, missing: false, relocatable: true,
        rel_target: 'tex/fabric_boucle_4k.exr', bytes: 96 * MB,
        width: 4096, height: 4096, res_tag: '4K' },
      { material: 'Curtain_Linen', used: true, file: 'linen_normal_4k.png',
        path: 'E:/OLD/linen_normal_4k.png', resolved: '',
        absolute: true, exists: false, missing: true, relocatable: false,
        rel_target: '', bytes: 0, width: 0, height: 0, res_tag: '' },
    ],
    relative: [
      { material: 'Concrete_Wall', used: true, file: 'concrete_diffuse_8k.jpg',
        path: 'tex/concrete_diffuse_8k.jpg',
        resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/concrete_diffuse_8k.jpg',
        absolute: false, exists: true, missing: false, relocatable: false,
        rel_target: '', bytes: 188 * MB, width: 8192, height: 8192, res_tag: '8K' },
      { material: 'Rug_Wool', used: true, file: 'rug_height_4k.tif',
        path: 'tex/rug_height_4k.tif',
        resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/rug_height_4k.tif',
        absolute: false, exists: true, missing: false, relocatable: false,
        rel_target: '', bytes: 64 * MB, width: 4096, height: 4096, res_tag: '4K' },
      { material: 'Brass_Lamp', used: true, file: 'brass_rough_2k.png',
        path: 'tex/brass_rough_2k.png',
        resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/brass_rough_2k.png',
        absolute: false, exists: true, missing: false, relocatable: false,
        rel_target: '', bytes: 9 * MB, width: 2048, height: 2048, res_tag: '2K' },
      { material: 'Deco_Vase', used: false, file: 'ceramic_glaze_2k.jpg',
        path: 'tex/ceramic_glaze_2k.jpg',
        resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/ceramic_glaze_2k.jpg',
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
    { guid: g('kitchen_cabinets_lower'), old: 'kitchen_cabinets_lower', new: 'KitchenCabinetsLower', rules: ['casing'] },
    { guid: g('kitchen_cabinets_upper'), old: 'kitchen_cabinets_upper', new: 'KitchenCabinetsUpper', rules: ['casing'] },
    { guid: g('countertop'), old: 'countertop', new: 'Countertop', rules: ['casing'] },
    { guid: g('floor_parquet'), old: 'floor_parquet', new: 'FloorParquet', rules: ['casing'] },
    { guid: g('pillow_01'), old: 'pillow_01', new: 'Pillow01', rules: ['casing', 'numbering'] },
    { guid: g('pillow_2'), old: 'pillow_2', new: 'Pillow02', rules: ['casing', 'numbering'] },
    { guid: g('Chair', 0), old: 'Chair', new: 'Chair01', rules: ['unique'] },
    { guid: g('Chair', 1), old: 'Chair', new: 'Chair02', rules: ['unique'] },
    { guid: g('Plate.1'), old: 'Plate.1', new: 'Plate01', rules: ['numbering'] },
  ],
}

export const planTranslate = {
  ok: true,
  count: 8,
  kept: ['Window_Front'],
  target: 'fr',
  engine: 'google',
  detected: { counts: { en: 1288, unknown: 421, de: 138 }, total: 1847,
    dominant: 'en', de: 138, en: 1288, unknown: 421 },
  diff: [
    { guid: g('Chair', 0), old: 'Chair', new: 'Chaise', words: [['chair', 'chaise']], lang: 'en' },
    { guid: g('CoffeeTable'), old: 'CoffeeTable', new: 'TableBasse', words: [['coffee table', 'table basse']], lang: 'en' },
    { guid: g('Rug'), old: 'Rug', new: 'Tapis', words: [['rug', 'tapis']], lang: 'en' },
    { guid: g('Wardrobe'), old: 'Wardrobe', new: 'Armoire', words: [['wardrobe', 'armoire']], lang: 'en' },
    { guid: g('Curtain_left'), old: 'Curtain_left', new: 'Rideau_gauche', words: [['curtain', 'rideau'], ['left', 'gauche']], lang: 'en' },
    { guid: g('sink'), old: 'sink', new: 'evier', words: [['sink', 'evier']], lang: 'en' },
    { guid: g('Door_Entrance'), old: 'Door_Entrance', new: 'Porte_Entree', words: [['door', 'porte'], ['entrance', 'entree']], lang: 'en' },
    { guid: g('plant_large'), old: 'plant_large', new: 'plante_grande', words: [['plant', 'plante'], ['large', 'grande']], lang: 'en' },
  ],
}

export const planLayers = {
  ok: true,
  count: 5,
  kept: [],
  by_layer: { Lights: 4, Cameras: 1 },
  diff: [
    { guid: g('LGT_Spot_Shelf'), name: 'LGT_Spot_Shelf', layer: 'Lights' },
    { guid: g('ceiling_lamp_dining'), name: 'ceiling_lamp_dining', layer: 'Lights' },
    { guid: g('floor_lamp'), name: 'floor_lamp', layer: 'Lights' },
    { guid: g('HDRI_Dome'), name: 'HDRI_Dome', layer: 'Lights' },
    { guid: g('Cam_Wide'), name: 'Cam_Wide', layer: 'Cameras' },
  ],
}

export const planStructure = {
  ok: true,
  count: 5,
  skipped: 2,
  kept: ['OldSet_backup'],
  diff: [
    { guid: g('plant_large'), name: 'plant_large', from: null, to: 'Deco' },
    { guid: g('deco_vase'), name: 'deco_vase', from: null, to: 'Deco' },
    { guid: g('PictureFrame_Set'), name: 'PictureFrame_Set', from: null, to: 'Deco' },
    { guid: g('Cam_Wide'), name: 'Cam_Wide', from: 'Cameras', to: 'Cameras' },
    { guid: g('cable_duct'), name: 'cable_duct', from: null, to: 'Utility' },
  ],
}

export const rules = {
  ok: true,
  groups: [
    { name: 'Cameras', priority: 90 },
    { name: 'Lights', priority: 85 },
    { name: 'Deco', priority: 50 },
    { name: 'Utility', priority: 40 },
  ],
}

export const presets = {
  ok: true,
  active: 'my-interior',
  presets: [
    { id: 'my-interior', name: 'My Interior Style', rules: 4,
      description: 'Personal convention learned from 3 archviz projects: PascalCase, 2-digit numbering.',
      created_at: '2026-06-30 14:12:00',
      groups: ['Cameras', 'Lights', 'Deco', 'Utility'] },
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
        { sid: 101, name: 'Chaise01', field: 'name', before: 'Chair01', after: 'Chaise01' },
        { sid: 102, name: 'Tapis', field: 'name', before: 'Rug', after: 'Tapis' },
        { sid: 103, name: 'Armoire', field: 'name', before: 'Wardrobe', after: 'Armoire' },
      ] },
    { id: '1783619000000', ts: 1783619000, at: '2026-07-08 18:43:20',
      kind: 'layers', summary: '38 assigned to layers', doc: 'penthouse_loft_final.c4d',
      revertible: true, reverted: false,
      items: [
        { sid: 201, name: 'LGT_Key_Window', field: 'layer', before: '', after: 'Lights' },
        { sid: 202, name: 'Cam_Hero', field: 'layer', before: '', after: 'Cameras' },
      ] },
    { id: '1783533000000', ts: 1783533000, at: '2026-07-07 18:50:00',
      kind: 'structure', summary: '21 moved', doc: 'penthouse_loft_final.c4d',
      revertible: true, reverted: true,
      items: [
        { sid: 301, name: 'deco_vase', field: 'parent', before: '', after: 'Deco' },
      ] },
  ],
}

export const detect = {
  ok: true,
  detect: { style: 'PascalCase', language: 'en', number_pad: 2, confidence: 0.83 },
}

// ---- audit areas (Tags / Generators / Files / Sims) ------------------------
export const tagsScan = {
  ok: true,
  types: [
    { type_id: 5612, label: 'Phong', count: 1176,
      objects: nodes.filter((n) => n.category === 'mesh').slice(0, 12)
        .map((n) => ({ guid: n.guid, name: n.name, tags: [{ name: 'Phong' }] })) },
    { type_id: 5671, label: 'UVW', count: 1049, objects: [] },
    { type_id: 5616, label: 'Material', count: 954, objects: [] },
    // point/polygon/edge selection tags arrive merged as ONE "Selection"
    // entry; multi-tag objects are one row with kind-badged tag chips.
    { type_id: 5673, type_ids: [5673, 5674, 5701], label: 'Selection', count: 63,
      objects: [
        { guid: g('CoffeeTable'), name: 'CoffeeTable',
          tags: [{ name: 'TopFaces', kind: 'polygon' }, { name: 'Bevel_Loop', kind: 'edge' }] },
        { guid: g('Rug'), name: 'Rug', tags: [{ name: 'Fringe', kind: 'point' }] },
        { guid: g('Cube'), name: 'Cube', tags: [{ name: 'R1', kind: 'polygon' }] },
      ] },
    { type_id: 5682, label: 'Vertex Map', count: 18, objects: [] },
    { type_id: 180000102, label: 'Dynamics Body', count: 6, objects: [] },
  ],
  findings: {
    missing_phong: [
      { guid: g('Cube'), name: 'Cube' },
      { guid: g('Cube.1'), name: 'Cube.1' },
      { guid: g('deco_vase'), name: 'deco_vase' },
    ],
    duplicate_material_tags: [
      { guid: g('CoffeeTable'), name: 'CoffeeTable', material: 'Wood_Walnut', count: 2 },
      { guid: g('Rug'), name: 'Rug', material: 'Rug_Wool', count: 3 },
    ],
    phong_angles: {
      distribution: [
        { angle_deg: 20, count: 84 }, { angle_deg: 40, count: 981 },
        { angle_deg: 60, count: 66 }, { angle_deg: 80, count: 45 },
      ],
      dominant_angle: 40,
    },
  },
  summary: { total_tags: 3266, tag_types: 6, missing_phong: 3, duplicate_material_tags: 2 },
}

export const gensScan = {
  ok: true,
  types: [
    { key: 'sds', label: 'Subdivision Surface', type_id: 1007455, count: 64,
      params: [
        { key: 'editor_sub', label: 'Editor subdivisions', kind: 'int', choices: {},
          values: [], uniform: false, dominant: 2,
          distribution: [{ value: 2, count: 41 }, { value: 1, count: 17 }, { value: 4, count: 6 }],
          outliers: [
            { guid: g('Sofa_Body_Hi'), name: 'Sofa_Body_Hi', value: 4 },
            { guid: g('Mattress'), name: 'Mattress', value: 4 },
            { guid: g('plant_large'), name: 'plant_large', value: 1 },
          ] },
        { key: 'render_sub', label: 'Render subdivisions', kind: 'int', choices: {},
          values: [], uniform: false, dominant: 3,
          distribution: [{ value: 3, count: 52 }, { value: 5, count: 12 }],
          outliers: [
            { guid: g('Sofa_Body_Hi'), name: 'Sofa_Body_Hi', value: 5 },
            { guid: g('Blanket_Wool'), name: 'Blanket_Wool', value: 5 },
          ] },
        { key: 'algo', label: 'Subdivision algorithm', kind: 'choice',
          choices: { 2102: 'Catmull-Clark (N-Gons)' },
          values: [], uniform: true, dominant: 2102,
          distribution: [{ value: 2102, count: 64 }], outliers: [] },
      ] },
    { key: 'instance', label: 'Instance', type_id: 5126, count: 214,
      params: [
        { key: 'render_instance', label: 'Render instance', kind: 'choice',
          choices: { 0: 'Instance', 1: 'Render Instance', 2: 'Multi-Instance' },
          values: [], uniform: false, dominant: 1,
          distribution: [{ value: 1, count: 196 }, { value: 0, count: 18 }],
          outliers: [
            { guid: g('Proxy_Tree_Outdoor'), name: 'Proxy_Tree_Outdoor', value: 0 },
          ] },
      ] },
    { key: 'extrude', label: 'Extrude', type_id: 5116, count: 9,
      params: [
        { key: 'subdivision', label: 'Subdivisions', kind: 'int', choices: {},
          values: [], uniform: true, dominant: 1,
          distribution: [{ value: 1, count: 9 }], outliers: [] },
      ] },
  ],
  summary: { total_generators: 287, types_found: 3, non_uniform_params: 3 },
}

export const filesScan = {
  ok: true,
  doc_path: 'D:/3D/PROJECTS/PENTHOUSE',
  accepted: ['Q:/OLD_LIB/city_bg.abc'],
  entries: [
    { kind: 'alembic', file: 'curtain_sim_v04.abc', path: 'caches/curtain_sim_v04.abc',
      resolved: 'D:/3D/PROJECTS/PENTHOUSE/caches/curtain_sim_v04.abc',
      exists: true, missing: false, absolute: false, relocatable: false,
      rel_target: '', bytes: 2.4 * GB, owner: 'Curtain_left', guid: g('Curtain_left') },
    // Absolute path INSIDE the project folder — shows the "→ rel" row action
    // and arms the "Make 1 relative" batch button in the list header.
    { kind: 'alembic', file: 'blanket_sim_v02.abc', path: 'D:/3D/PROJECTS/PENTHOUSE/caches/blanket_sim_v02.abc',
      resolved: 'D:/3D/PROJECTS/PENTHOUSE/caches/blanket_sim_v02.abc',
      exists: true, missing: false, absolute: true, relocatable: true,
      rel_target: 'caches/blanket_sim_v02.abc', bytes: 1.1 * GB, owner: 'Blanket_Wool', guid: g('Blanket_Wool') },
    { kind: 'alembic', file: 'plant_scan_hero.abc', path: 'Q:/SCANS/plants/plant_scan_hero.abc',
      resolved: '', exists: false, missing: true, absolute: true, relocatable: false,
      rel_target: '', bytes: 0, owner: 'plant_large', guid: g('plant_large') },
    { kind: 'ies', file: 'spot_narrow_25deg.ies', path: 'tex/ies/spot_narrow_25deg.ies',
      resolved: 'D:/3D/PROJECTS/PENTHOUSE/tex/ies/spot_narrow_25deg.ies',
      exists: true, missing: false, absolute: false, relocatable: false,
      rel_target: '', bytes: 0.2 * MB, owner: 'LGT_Spot_Shelf', guid: g('LGT_Spot_Shelf') },
    { kind: 'cache', file: 'fireplace_smoke.vdb', path: 'C:/Users/artist/Desktop/fireplace_smoke.vdb',
      resolved: '', exists: false, missing: true, absolute: true, relocatable: false,
      rel_target: '', bytes: 0, owner: 'Fireplace_Pyro', guid: null },
  ],
  summary: {
    total: 5, by_kind: { alembic: 3, ies: 1, cache: 1 },
    missing_count: 2, absolute_count: 3, relocatable_count: 1,
    total_bytes: Math.round(3.5 * GB),
  },
}

export const simsScan = {
  ok: true,
  hits: [
    { guid: g('Curtain_left'), object: 'Curtain_left', carrier: 'tag', kind: 'cloth',
      label: 'Cloth', enabled: true, cached: true, hidden: false, notes: [] },
    { guid: g('Curtain_right'), object: 'Curtain_right', carrier: 'tag', kind: 'cloth',
      label: 'Cloth', enabled: true, cached: false, hidden: false, notes: [] },
    { guid: g('Blanket_Wool'), object: 'Blanket_Wool', carrier: 'tag', kind: 'cloth',
      label: 'Cloth', enabled: true, cached: true, hidden: false, notes: [] },
    { guid: g('OldSet_backup'), object: 'OldSet_backup', carrier: 'tag', kind: 'dynamics',
      label: 'Dynamics Body', enabled: true, cached: false, hidden: true, notes: [] },
    { guid: g('Rug'), object: 'Rug', carrier: 'tag', kind: 'collider',
      label: 'Collider', enabled: false, cached: null, hidden: false, notes: [] },
    { guid: g('floor_parquet'), object: 'floor_parquet', carrier: 'tag', kind: 'collider',
      label: 'Collider', enabled: false, cached: null, hidden: false, notes: [] },
  ],
  findings: {
    active_hidden: [
      { guid: g('OldSet_backup'), object: 'OldSet_backup', kind: 'dynamics', label: 'Dynamics Body' },
    ],
    unbaked: [
      { guid: g('Curtain_right'), object: 'Curtain_right', kind: 'cloth', label: 'Cloth' },
    ],
    disabled_leftovers: [
      { guid: g('Rug'), object: 'Rug', kind: 'collider', label: 'Collider' },
      { guid: g('floor_parquet'), object: 'floor_parquet', kind: 'collider', label: 'Collider' },
    ],
  },
  summary: { total: 6, by_kind: { cloth: 3, dynamics: 1, collider: 2 },
    active_hidden: 1, unbaked: 1, disabled: 2 },
}
