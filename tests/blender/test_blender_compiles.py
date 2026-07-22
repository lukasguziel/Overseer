from __future__ import annotations

import pathlib

SRC = pathlib.Path(__file__).resolve().parents[2] / "src" / "overseer"

AREA_MODULES = ("tags.py", "generators.py", "sims.py", "perf.py", "files.py",
                "layers.py", "materials.py")
AREA_PACKAGES = ("scene", "organize", "textures")


def test_every_blender_module_compiles():
    # setup
    sources = [p for p in (SRC / "blender").rglob("*.py")
               if "__pycache__" not in p.parts]

    # do it
    errors = []
    for path in sources:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as ex:
            errors.append("%s: %s" % (path.name, ex))

    # postcondition
    assert sources, "blender package not found"
    assert errors == []


def test_blender_mirrors_the_core_areas():
    # postcondition: both hosts expose the same per-area surface
    for name in AREA_MODULES:
        assert (SRC / "blender" / name).is_file(), name
        assert (SRC / "cinema" / name).is_file(), name
    for name in AREA_PACKAGES:
        assert (SRC / "blender" / name / "__init__.py").is_file(), name
        assert (SRC / "cinema" / name / "__init__.py").is_file(), name
