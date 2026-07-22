from __future__ import annotations

from abc import ABC


class ItemsBase(ABC):  # noqa: B024 - carries the ABCMeta for the area bases
    """Shared per-area iteration base: progress-chunked loops.

    Every area base inherits this so long scans report progress the same way
    everywhere: one event every ``PROGRESS_EVERY`` items plus a final one.
    ``describe(item)`` supplies the per-item detail string (usually a name).
    """

    PROGRESS_EVERY = 50

    def each(self, items, progress=None, label="", describe=None):
        items = list(items)
        total = len(items)
        for i, item in enumerate(items):
            if progress and i % self.PROGRESS_EVERY == 0:
                detail = ""
                if describe is not None:
                    try:
                        detail = str(describe(item))
                    except Exception:
                        detail = ""
                progress(label, i, total, detail)
            yield item
        if progress and total:
            progress(label, total, total, "")
