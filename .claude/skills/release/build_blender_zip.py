"""Assemble the installable Blender addon zip: Overseer-Blender-<version>.zip.

Blender's `bpy.ops.preferences.addon_install` expects a single top-level folder
that IS the addon package. So the zip contains one folder, `overseer/`, holding:

    overseer/__init__.py   <- src/blender_addon/__init__.py (the addon loader)
    overseer/overseer/     <- src/overseer  (shared core/naming/config + blender/)
    overseer/web/          <- src/web       (Vite build output)
    overseer/vendor/       <- src/vendor    (Pillow, optional)

    python .claude/skills/release/build_blender_zip.py

The version is read from src/overseer/__init__.py (the three version spots -
pyproject.toml, __init__.py, package.json - are kept in lockstep by the release
skill, so reading one is enough). Output lands in dist/ (gitignored).

Run `pnpm run build` in frontend/ first so src/web/ exists; run
vendor_pillow.py first if the zip should ship Pillow (it works without it).
"""
from __future__ import annotations

import pathlib
import re
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
DIST = ROOT / "dist"

# Top folder inside the zip == the addon package name Blender installs.
PKG = "overseer"

# What goes into the zip, as (source path, path inside overseer/).
LAYOUT = [
    (SRC / "blender_addon" / "__init__.py", "__init__.py"),
    (SRC / "blender_addon" / "blender_manifest.toml", "blender_manifest.toml"),
    (SRC / "overseer", "overseer"),
    (SRC / "web", "web"),
    (SRC / "vendor", "vendor"),
]

# Never ship compiled/cache junk.
EXCLUDE_DIRS = {"__pycache__"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def read_version() -> str:
    text = (SRC / "overseer" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'__version__\s*=\s*["\']([^"\']+)["\']', text)
    if not m:
        raise SystemExit("could not read __version__ from src/overseer/__init__.py")
    return m.group(1)


def _skip(path: pathlib.Path) -> bool:
    if path.suffix in EXCLUDE_SUFFIXES:
        return True
    return any(part in EXCLUDE_DIRS for part in path.parts)


def add_tree(zf: zipfile.ZipFile, src: pathlib.Path, arc_prefix: str) -> int:
    """Write `src` (file or dir) into the zip under `arc_prefix`. Returns count."""
    n = 0
    if src.is_file():
        zf.write(src, arc_prefix)
        return 1
    for path in sorted(src.rglob("*")):
        if path.is_dir() or _skip(path):
            continue
        rel = path.relative_to(src).as_posix()
        zf.write(path, "%s/%s" % (arc_prefix, rel))
        n += 1
    return n


def main() -> int:
    version = read_version()

    missing = [str(s) for s, _ in LAYOUT if not s.exists()]
    # web/ and vendor/ are build artifacts; warn but don't hard-require vendor.
    hard_missing = [m for m in missing if m.endswith("__init__.py") or m.endswith("overseer")]
    if hard_missing:
        raise SystemExit("missing required inputs:\n  " + "\n  ".join(hard_missing))
    for m in missing:
        if m.endswith("web"):
            print("WARN: src/web/ missing - run `pnpm run build` in frontend/ first.",
                  file=sys.stderr)
        elif m.endswith("vendor"):
            print("WARN: src/vendor/ missing - zip ships without Pillow "
                  "(run vendor_pillow.py to include it).", file=sys.stderr)

    DIST.mkdir(parents=True, exist_ok=True)
    out = DIST / ("Overseer-Blender-v%s.zip" % version)
    if out.exists():
        out.unlink()

    total = 0
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for src, arc in LAYOUT:
            if not src.exists():
                continue
            total += add_tree(zf, src, "%s/%s" % (PKG, arc) if arc else PKG)

    print("wrote %s (%d files)" % (out, total))
    print("Install in Blender: Edit > Preferences > Add-ons > Install... -> "
          "pick this zip, then enable 'Overseer'.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
