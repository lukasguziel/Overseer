from __future__ import annotations

from abc import abstractmethod

from ..items import ItemsBase


class MaterialsBase(ItemsBase):
    """The materials area: the shared scan workflow lives here, a host
    subclasses and implements only the ``get_*`` primitives that read its own
    material system. ``focus_material``/``delete_*`` stay host machinery."""

    # -- shared workflow ----------------------------------------------------
    def scan_materials(self, include_hidden: bool = True,
                       accepted=None) -> dict:
        accepted = set(accepted or ())
        try:
            mats = list(self.get_materials())
        except Exception:
            return self.scan_result(0, [], [], [], accepted, [])

        used_any, used_visible = self.get_material_usage()

        unused: list = []
        only_hidden: list = []
        accepted_out: list = []
        missing: list = []
        for m in mats:
            name = self.get_material_name(m)
            if name is None:
                continue
            if self.is_internal(name):
                continue
            key = self.get_material_key(m)
            nowhere = key not in used_any
            hidden_only = (not nowhere) and key not in used_visible
            if nowhere or (hidden_only and include_hidden):
                if name in accepted:
                    accepted_out.append(name)
                else:
                    unused.append(name)
                    if hidden_only:
                        only_hidden.append(name)
            missing.extend(self.get_missing_textures(m, name))

        return self.scan_result(len(mats), unused, only_hidden,
                                    accepted_out, accepted, missing)

    @staticmethod
    def is_internal(name: str) -> bool:
        """Whether ``name`` is plugin machinery, not an artist material. The
        core convention (dunder names); Blender overrides to add its prefixes."""
        n = (name or "").strip()
        return len(n) > 4 and n.startswith("__") and n.endswith("__")

    @staticmethod
    def scan_result(total: int, unused: list, only_hidden: list,
                    accepted_out: list, accepted_all, missing: list) -> dict:
        return {
            "total": total,
            "unused": unused,
            "only_hidden": only_hidden,
            "accepted": accepted_out,
            "accepted_all": sorted(accepted_all or ()),
            "deletable_count": len(unused),
            "missing": missing[:50],
            "missing_textures": len(missing),
        }

    # -- host primitives ----------------------------------------------------
    @abstractmethod
    def get_materials(self) -> list:
        """Every material in the document."""

    @abstractmethod
    def get_material_name(self, mat):
        """The material's display name, or None to skip the material."""

    @abstractmethod
    def get_material_key(self, mat):
        """A stable identity for the material, keyed like get_material_usage."""

    @abstractmethod
    def get_material_usage(self) -> tuple:
        """``(used_any, used_visible)`` sets keyed like get_material_key."""

    @abstractmethod
    def get_missing_textures(self, mat, name: str) -> list:
        """``{"material","file"}`` dicts for this material's missing textures."""

    # -- host machinery -----------------------------------------------------
    @abstractmethod
    def focus_material(self, name: str) -> dict: ...

    @abstractmethod
    def delete_material(self, name: str, include_hidden=False) -> int: ...

    @abstractmethod
    def delete_unused_materials(self, include_hidden=False,
                                accepted=None) -> int: ...
