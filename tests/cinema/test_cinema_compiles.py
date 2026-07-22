from __future__ import annotations

import pathlib

CINEMA = pathlib.Path(__file__).resolve().parents[2] / "src" / "overseer" / "cinema"

AREA_MODULES = ("tags.py", "generators.py", "sims.py", "perf.py", "files.py",
                "layers.py", "materials.py")
AREA_PACKAGES = ("scene", "organize", "textures")


def test_every_cinema_module_compiles():
    # setup
    sources = [p for p in CINEMA.rglob("*.py") if "__pycache__" not in p.parts]

    # do it: c4d cannot be imported in CI, so the gate is compile-only
    errors = []
    for path in sources:
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as ex:
            errors.append("%s: %s" % (path.name, ex))

    # postcondition
    assert sources, "cinema package not found"
    assert errors == []


def test_cinema_mirrors_the_core_areas():
    # postcondition: one module (or package) per area, same names as core/
    for name in AREA_MODULES:
        assert (CINEMA / name).is_file(), name
    for name in AREA_PACKAGES:
        assert (CINEMA / name / "__init__.py").is_file(), name
