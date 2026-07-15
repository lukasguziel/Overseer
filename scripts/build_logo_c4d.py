"""Rebuild the Overseer logo (src/so_logo.png) from cube primitives.

Run inside Cinema 4D: Extensions > Script Manager > load this file > Execute.
Scale: 1 px = 1 cm, measured from the 128x128 PNG. The logo plane is XY,
blocks protrude toward the viewer (-Z). One undo step.

Materials are flat-color placeholders (Overseer_* names) so the parts are
distinguishable — replace them with real shaders as you like.
"""

import c4d

# (name, width, height, center_x, center_y)  -- measured pixel boxes,
# origin already shifted to the logo center, Y up.
BLOCKS = [
    ("Block_Orange",   98.0, 40.0,   1.0,  27.0, "orange"),
    ("Block_Green_Sq", 23.0, 23.0, -36.5, -10.0, "green"),
    ("Block_Slate",    69.0, 23.0,  15.5, -10.0, "slate"),
    ("Bar_Green_1",     8.0, 23.0, -44.0, -38.0, "green"),
    ("Bar_Green_2",    23.0, 23.0, -21.5, -38.0, "green"),
    ("Bar_Green_3",    23.0, 23.0,   8.5, -38.0, "green"),
    ("Bar_Green_4",     8.0, 23.0,  31.0, -38.0, "green"),
    ("Bar_Green_5",     8.0, 23.0,  46.0, -38.0, "green"),
]

COLORS = {
    "plate":  (46, 46, 46),
    "orange": (231, 100, 35),
    "green":  (52, 211, 153),
    "slate":  (100, 116, 139),
}

PLATE_SIZE = 124.0
PLATE_DEPTH = 12.0
PLATE_FILLET = 12.0
BLOCK_DEPTH = 8.0
BLOCK_Z = -7.0          # embedded 3 cm into the plate, protruding 5 cm
FILLET_SUBDIV = 5


def _make_material(doc, name, rgb):
    mat = c4d.BaseMaterial(c4d.Mmaterial)
    mat.SetName(name)
    mat[c4d.MATERIAL_COLOR_COLOR] = c4d.Vector(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)
    mat[c4d.MATERIAL_USE_REFLECTION] = False
    doc.InsertMaterial(mat)
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, mat)
    return mat


def _make_cube(name, w, h, d, fillet):
    cube = c4d.BaseObject(c4d.Ocube)
    cube.SetName(name)
    cube[c4d.PRIM_CUBE_LEN] = c4d.Vector(w, h, d)
    cube[c4d.PRIM_CUBE_DOFILLET] = True
    cube[c4d.PRIM_CUBE_FRAD] = min(fillet, w / 2.0, h / 2.0, d / 2.0)
    cube[c4d.PRIM_CUBE_SUBF] = FILLET_SUBDIV
    return cube


def _assign(doc, obj, mat):
    tag = obj.MakeTag(c4d.Ttexture)
    tag[c4d.TEXTURETAG_MATERIAL] = mat
    tag[c4d.TEXTURETAG_PROJECTION] = c4d.TEXTURETAG_PROJECTION_UVW
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, tag)


def main():
    doc = c4d.documents.GetActiveDocument()
    doc.StartUndo()

    mats = {key: _make_material(doc, "Overseer_" + key.capitalize(), rgb)
            for key, rgb in COLORS.items()}

    root = c4d.BaseObject(c4d.Onull)
    root.SetName("Overseer_Logo")
    doc.InsertObject(root)
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, root)

    plate = _make_cube("Plate", PLATE_SIZE, PLATE_SIZE, PLATE_DEPTH, PLATE_FILLET)
    plate.InsertUnder(root)
    doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, plate)
    _assign(doc, plate, mats["plate"])

    for name, w, h, cx, cy, color in BLOCKS:
        # thin 8 cm bars get pill-shaped ends, wider blocks a 4 cm radius
        fillet = 4.0
        cube = _make_cube(name, w, h, BLOCK_DEPTH, fillet)
        cube.SetAbsPos(c4d.Vector(cx, cy, BLOCK_Z))
        cube.InsertUnder(root)
        doc.AddUndo(c4d.UNDOTYPE_NEWOBJ, cube)
        _assign(doc, cube, mats[color])

    doc.EndUndo()
    c4d.EventAdd()


if __name__ == "__main__":
    main()
