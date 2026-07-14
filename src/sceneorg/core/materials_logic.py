from __future__ import annotations


def is_internal_material(name: str) -> bool:
    """Renderer plugins park internal helper materials in the document —
    e.g. Octane's "__octanetemp__" clipboard/preview material. They look
    unused to the scan but belong to the plugin: never list them as unused,
    never delete them. The dunder naming (`__...__`) is the convention those
    helpers share.
    """
    n = (name or "").strip()
    return len(n) > 4 and n.startswith("__") and n.endswith("__")
