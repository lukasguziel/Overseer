from __future__ import annotations

from abc import abstractmethod

from ..items import ItemsBase
from . import logic as mat_logic
from .logic import is_internal_material


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
            return mat_logic.scan_result(0, [], [], [], accepted, [])

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

        return mat_logic.scan_result(len(mats), unused, only_hidden,
                                      accepted_out, accepted, missing)

    def is_internal(self, name: str) -> bool:
        """Whether ``name`` is plugin machinery, not an artist material. The
        core convention (dunder names); Blender overrides to add its prefixes."""
        return is_internal_material(name)

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
