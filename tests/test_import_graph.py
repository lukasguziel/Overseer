from __future__ import annotations

import ast
import pathlib

SRC_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src"
PKG = SRC_ROOT / "overseer"


def _module_name(path: pathlib.Path) -> str:
    rel = path.relative_to(SRC_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _known_modules() -> set:
    known = set()
    for p in PKG.rglob("*.py"):
        if "__pycache__" in p.parts or "vendor" in p.parts:
            continue
        known.add(_module_name(p))
    return known


def _resolve(current: str, is_package: bool, node: ast.ImportFrom) -> str | None:
    if node.level == 0:
        target = node.module or ""
        return target if target.split(".")[0] == "overseer" else None
    parts = current.split(".")
    if not is_package:
        parts = parts[:-1]
    drop = node.level - 1
    if drop > len(parts):
        return "<beyond top: %s>" % ast.dump(node)
    base = parts[: len(parts) - drop]
    if node.module:
        base = base + node.module.split(".")
    return ".".join(base)


def test_every_overseer_import_resolves():
    # setup: the full module set plus every import statement in the package
    known = _known_modules()
    problems = []

    # do it: statically resolve each relative / overseer-absolute import —
    # cinema (c4d) and blender (bpy) cannot be imported in CI, so this is the
    # gate that catches a wrong relative depth or a renamed-away module
    for path in PKG.rglob("*.py"):
        if "__pycache__" in path.parts or "vendor" in path.parts:
            continue
        current = _module_name(path)
        is_package = path.name == "__init__.py"
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            target = _resolve(current, is_package, node)
            if target is None:
                continue
            if target not in known:
                problems.append("%s:%d -> %s" % (current, node.lineno, target))

    # postcondition
    assert problems == []
