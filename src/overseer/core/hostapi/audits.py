"""Per-area audit base classes (the ``Audit`` port, specialized per area).

Each area (tags / generators / sims / perf / files) gets a base class that owns
the SHARED workflow — the op dispatch, and (where it exists) the result-shaping
via the area's pure ``core.*_logic`` — and declares the host-specific primitives
as abstract methods. A host provides a subclass that overrides only those
primitives:

    core.hostapi.audits.SimsAudit          (base: dispatch + scan_result shaping)
      ├── blender.audit_sims.BlenderSimsAudit   (collect/select/set_enabled via bpy)
      └── cinema.audit_sims.CinemaSimsAudit      (… via c4d)

The host module exposes a ready instance as ``AUDIT`` and the ``HostContext``
returns it from ``audit(prefix)``. The shared webapi calls ``AUDIT.handle(...)``
/ ``AUDIT.has_any(...)`` — identical for every host.
"""
from __future__ import annotations

from abc import abstractmethod

from .. import sims_logic
from .ports import Audit


class TagsAudit(Audit):
    """Object-attachment audit. Fully host-specific reads, so the base only
    owns the op dispatch + the always-on tab (has_any default True)."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "tags_scan":
            return self.scan(doc, adapter, tree, progress)
        if op == "tags_add_phong":
            return self.add_phong(doc, adapter, tree, payload)
        if op == "tags_set_phong_angle":
            return self.set_phong_angle(doc, adapter, tree, payload)
        if op == "tags_delete_duplicates":
            return self.delete_duplicates(doc, adapter, tree, payload)
        if op == "tags_select":
            return self.select(doc, adapter, tree, payload)
        return {"error": "unknown tags op: %s" % op}

    @abstractmethod
    def scan(self, doc, adapter, tree, progress) -> dict: ...

    @abstractmethod
    def add_phong(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def set_phong_angle(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def delete_duplicates(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def select(self, doc, adapter, tree, payload) -> dict: ...


class GeneratorsAudit(Audit):
    """Generator/modifier settings audit."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "gens_scan":
            return self.scan(doc, adapter, tree, progress)
        if op == "gens_apply":
            return self.apply(doc, adapter, tree, payload)
        if op == "gens_select":
            return self.select(doc, adapter, tree, payload)
        return {"error": "unknown gens op: %s" % op}

    @abstractmethod
    def has_any(self, adapter, tree) -> bool: ...

    @abstractmethod
    def scan(self, doc, adapter, tree, progress) -> dict: ...

    @abstractmethod
    def apply(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def select(self, doc, adapter, tree, payload) -> dict: ...


class SimsAudit(Audit):
    """Simulation audit. The base owns the whole scan workflow: collect the
    host's sims into normalized ``sims_logic.SimHit`` objects, then shape the
    result via the pure ``sims_logic.scan_result`` (identical for every host).
    Hosts implement only ``collect`` / ``select`` / ``set_enabled`` /
    ``has_any``."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "sims_scan":
            hits = self.collect(doc, adapter, tree, progress)
            return sims_logic.scan_result(hits)
        if op == "sims_select":
            return self.select(doc, adapter, payload)
        if op == "sims_set_enabled":
            return self.set_enabled(doc, adapter, payload)
        return {"error": "unknown sims op: %s" % op}

    @abstractmethod
    def has_any(self, adapter, tree) -> bool: ...

    @abstractmethod
    def collect(self, doc, adapter, tree, progress) -> list: ...

    @abstractmethod
    def select(self, doc, adapter, payload) -> dict: ...

    @abstractmethod
    def set_enabled(self, doc, adapter, payload) -> dict: ...


class PerfAudit(Audit):
    """Viewport rebuild-cost audit."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "perf_scan":
            return self.scan(doc, adapter, tree, payload, progress)
        if op == "perf_select":
            return self.select(doc, adapter, tree, payload)
        return {"error": "unknown perf op: %s" % op}

    @abstractmethod
    def scan(self, doc, adapter, tree, payload, progress) -> dict: ...

    @abstractmethod
    def select(self, doc, adapter, tree, payload) -> dict: ...


class FilesAudit(Audit):
    """External-file reference audit."""

    def handle(self, op, payload, doc, adapter, tree, progress):
        if op == "files_scan":
            return self.scan(doc, adapter, tree, progress)
        if op == "files_make_relative":
            return self.make_relative(doc, adapter, tree, payload)
        if op == "files_select":
            return self.select(doc, adapter, tree, payload)
        if op == "files_pick_path":
            return self.pick_path(doc, adapter, tree, payload)
        if op == "files_relink":
            return self.relink(doc, adapter, tree, payload, progress)
        return {"error": "unknown files op: %s" % op}

    @abstractmethod
    def scan(self, doc, adapter, tree, progress) -> dict: ...

    @abstractmethod
    def make_relative(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def select(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def pick_path(self, doc, adapter, tree, payload) -> dict: ...

    @abstractmethod
    def relink(self, doc, adapter, tree, payload, progress) -> dict: ...
