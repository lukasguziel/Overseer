"""Generators audit for Blender.

A C4D "generator" (Subdivision Surface, Cloner, Extrude, Instance, Symmetry)
is a distinct object *type*; in Blender the same modelling power lives in
**modifiers** (Subdivision Surface, Array, Mirror, Solidify, Screw, Bevel,
Boolean, ...), in **Geometry Nodes** modifiers, and in object **instancing**
(``object.instance_type``). One object can carry several modifiers, so a
"generator" here is a single *modifier instance* (or an instancing object),
grouped by kind.

The result shape is the C4D one (see ``cinema/generators.py`` and the
frozen ``frontend/src/tabs/GeneratorsTab.tsx``): ``types`` -> per-type param
cards, each param summarised across its members via ``GeneratorsAudit.summarize``.
GeneratorsTab reads ``data.types`` and ``data.summary`` verbatim, so we return
those keys (NOT a flat ``generators`` list).

Declarative ``_REGISTRY`` maps a modifier ``type`` to the attributes to
surface; nothing is hand-tabled beyond the attribute *names*: every human
label (the modifier type name, each parameter label, every dropdown option)
is read from ``holder.bl_rna`` at scan time, exactly like the C4D build reads
labels from the object description. Modifier types not in the registry still
appear (as paramless cards) so the audit covers *every* modifier; Geometry
Nodes modifiers group by node-group name; instancing objects form one group.

No top-level ``import bpy`` - Blender objects arrive via ``adapter._by_guid``
and ``adapter.bpy``; every attribute access is defensive.
"""
from __future__ import annotations

from ..core.generators.audit import GeneratorsAudit

# Curated per-modifier-type parameter lists. Each entry: (attr, kind) where
# kind is the FRONTEND ParamKind ('int' | 'bool' | 'choice'). Blender has no
# separate float kind, so continuous floats (thickness, angle, ...) also use
# 'int' - the UI renders a free numeric input for them and we coerce back to
# the real property type on apply (never truncating). Labels are NOT stored
# here; they are read from bl_rna.
_REGISTRY = [
    {"key": "subsurf", "mod_type": "SUBSURF", "params": [
        ("levels", "int"), ("render_levels", "int"),
        ("subdivision_type", "choice"), ("use_limit_surface", "bool")]},
    {"key": "array", "mod_type": "ARRAY", "params": [
        ("fit_type", "choice"), ("count", "int"),
        ("use_relative_offset", "bool"), ("use_merge_vertices", "bool")]},
    {"key": "mirror", "mod_type": "MIRROR", "params": [
        ("use_clip", "bool"), ("use_mirror_merge", "bool"),
        ("merge_threshold", "int")]},
    {"key": "solidify", "mod_type": "SOLIDIFY", "params": [
        ("thickness", "int"), ("offset", "int"),
        ("solidify_mode", "choice"), ("use_even_offset", "bool")]},
    {"key": "screw", "mod_type": "SCREW", "params": [
        ("angle", "int"), ("steps", "int"), ("render_steps", "int"),
        ("screw_offset", "int"), ("use_smooth_shade", "bool")]},
    {"key": "bevel", "mod_type": "BEVEL", "params": [
        ("width", "int"), ("segments", "int"),
        ("limit_method", "choice"), ("affect", "choice")]},
    {"key": "boolean", "mod_type": "BOOLEAN", "params": [
        ("operation", "choice"), ("solver", "choice")]},
]

_BY_TYPE = {e["mod_type"]: e for e in _REGISTRY}

_GROUP_CACHE = {}

# Instancing is a per-object generator (not a modifier). Its holder is the
# object itself; the enum label for each value is read from the object bl_rna.
_INSTANCE_KEY = "instance"
_INSTANCE_LABEL = "Instancing"
_INSTANCE_PARAMS = [("instance_type", "choice")]


class BlenderGeneratorsAudit(GeneratorsAudit):
    """Blender modifier / instancing settings audit."""

    # -----------------------------------------------------------------------
    # introspection helpers (all read labels from bl_rna, never hand-tabled)
    # -----------------------------------------------------------------------
    def _jsonify(self, value):
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return round(value, 4)
        if isinstance(value, str):
            return value
        # bpy vectors / bool arrays / colours -> plain list of rounded floats.
        try:
            return [round(float(x), 4) for x in value]
        except Exception:
            return str(value)

    def _read(self, holder, attr):
        """Current value of ``attr`` on a modifier or object, JSON-safe."""
        try:
            return self._jsonify(getattr(holder, attr))
        except Exception:
            return None

    def _prop_type(self, holder, attr):
        try:
            return holder.bl_rna.properties[attr].type
        except Exception:
            return None

    def _coerce(self, holder, attr, value):
        """Coerce an incoming JSON value to the property's real Blender type, so
        a float parameter that the UI edits as a number is never truncated."""
        ptype = self._prop_type(holder, attr)
        if ptype == "BOOLEAN":
            return bool(value)
        if ptype == "INT":
            try:
                return int(value)
            except (TypeError, ValueError):
                return value
        if ptype == "FLOAT":
            try:
                return float(value)
            except (TypeError, ValueError):
                return value
        if ptype == "ENUM":
            return str(value)
        return value

    def _param_label(self, holder, attr):
        try:
            return holder.bl_rna.properties[attr].name or attr
        except Exception:
            return attr

    def _enum_choices(self, holder, attr):
        """{enum_identifier: human name} read from bl_rna - never hand-tabled."""
        out = {}
        try:
            for item in holder.bl_rna.properties[attr].enum_items:
                ident = str(item.identifier)
                out[ident] = item.name or ident
        except Exception:
            pass
        return out

    def _mod_type_label(self, mod):
        """Human name of the modifier's own type, from the ``type`` enum."""
        try:
            return mod.bl_rna.properties["type"].enum_items[mod.type].name or mod.type
        except Exception:
            try:
                return str(mod.type)
            except Exception:
                return "Modifier"

    def _type_id(self, key: str) -> int:
        """Stable non-negative int per group key (the frozen UI types type_id as
        a number; Blender has no numeric modifier id, so we hash the group key).
        Only used for the icon-cache key, so a hash is sufficient."""
        h = 2166136261
        for ch in key:
            h = ((h ^ ord(ch)) * 16777619) & 0xFFFFFFFF
        return h & 0x7FFFFFFF

    def _group_for_mod(self, mod):
        """(group_key, label, params_def) for a modifier, or None to skip.

        Geometry Nodes group by node-group name; registry types use their
        curated params; any other modifier still appears, with no editable
        params.

        Results are memoised on ``_GROUP_CACHE`` keyed by (mod.type, node-group
        name) - both session-stable - so the bl_rna label introspection runs
        once per distinct modifier type/name instead of once per modifier
        instance (apply/select re-walk the whole tree on every interaction)."""
        try:
            mtype = mod.type
        except Exception:
            return None
        if mtype == "NODES":
            gname = ""
            try:
                ng = getattr(mod, "node_group", None)
                gname = ng.name if ng is not None else ""
            except Exception:
                gname = ""
            cache_key = ("NODES", gname)
            cached = _GROUP_CACHE.get(cache_key)
            if cached is not None:
                return cached
            result = ("nodes:" + gname, gname or "Geometry Nodes", [])
            _GROUP_CACHE[cache_key] = result
            return result

        cache_key = (mtype, None)
        cached = _GROUP_CACHE.get(cache_key)
        if cached is not None:
            return cached
        label = self._mod_type_label(mod)
        entry = _BY_TYPE.get(mtype)
        if entry is not None:
            result = (entry["key"], label, entry["params"])
        else:
            result = ("mod:" + str(mtype), label, [])
        _GROUP_CACHE[cache_key] = result
        return result

    def _instance_type(self, obj):
        try:
            return getattr(obj, "instance_type", "NONE")
        except Exception:
            return "NONE"

    def _is_instancing(self, obj) -> bool:
        return self._instance_type(obj) not in ("NONE", "", None)

    # -----------------------------------------------------------------------
    # tab visibility
    # -----------------------------------------------------------------------
    def has_any(self, adapter, tree) -> bool:
        for node in tree.walk():
            obj = adapter._by_guid.get(node.guid)
            if obj is None:
                continue
            try:
                if len(obj.modifiers) > 0:
                    return True
            except Exception:
                pass
            if self._is_instancing(obj):
                return True
        return False

    # -----------------------------------------------------------------------
    # scan
    # -----------------------------------------------------------------------
    def scan(self, doc, adapter, tree, progress):
        groups = {}  # key -> {"label", "params_def", "members": [(node, holder)]}
        nodes = list(tree.walk())
        total = len(nodes)
        for i, node in enumerate(nodes):
            if progress and i % 200 == 0:
                progress("Scanning generators", i, total, node.name)
            obj = adapter._by_guid.get(node.guid)
            if obj is None:
                continue
            try:
                mods = list(obj.modifiers)
            except Exception:
                mods = []
            for mod in mods:
                g = self._group_for_mod(mod)
                if g is None:
                    continue
                key, label, params_def = g
                bucket = groups.setdefault(
                    key,
                    {"label": label, "params_def": params_def, "members": []})
                bucket["members"].append((node, mod))
            if self._is_instancing(obj):
                bucket = groups.setdefault(
                    _INSTANCE_KEY,
                    {"label": _INSTANCE_LABEL, "params_def": _INSTANCE_PARAMS,
                     "members": []})
                bucket["members"].append((node, obj))

        types_out = []
        non_uniform_params = 0
        total_gens = 0
        for key, bucket in groups.items():
            members = bucket["members"]
            total_gens += len(members)
            params_out = []
            for attr, kind in bucket["params_def"]:
                entries = []
                for node, holder in members:
                    value = self._read(holder, attr)
                    if value is None:
                        continue
                    entries.append(self.value_entry(node.guid, node.name, value))
                summary = self.summarize(entries)
                if not summary["uniform"]:
                    non_uniform_params += 1
                choices = {}
                label = attr
                if members:
                    first_holder = members[0][1]
                    label = self._param_label(first_holder, attr)
                    if kind == "choice":
                        choices = self._enum_choices(first_holder, attr)
                params_out.append(self.param_row(
                    attr, label, kind, choices, summary))
            types_out.append(self.type_row(
                key, bucket["label"], self._type_id(key), len(members),
                params_out))

        return self.scan_result(types_out, total_gens, non_uniform_params)

    # -----------------------------------------------------------------------
    # apply / select
    # -----------------------------------------------------------------------
    def _members_of(self, adapter, tree, type_key, guids=None):
        """(node, holder) pairs for every member of ``type_key``. The holder is
        a modifier for modifier groups, the object itself for the instancing
        group - matching what ``_read`` / ``_coerce`` operate on."""
        wanted = set(guids) if guids is not None else None
        out = []
        for node in tree.walk():
            if wanted is not None and node.guid not in wanted:
                continue
            obj = adapter._by_guid.get(node.guid)
            if obj is None:
                continue
            if type_key == _INSTANCE_KEY:
                if self._is_instancing(obj):
                    out.append((node, obj))
                continue
            try:
                mods = list(obj.modifiers)
            except Exception:
                mods = []
            for mod in mods:
                g = self._group_for_mod(mod)
                if g is not None and g[0] == type_key:
                    out.append((node, mod))
        return out

    def apply(self, doc, adapter, tree, payload):
        type_key = payload.get("type_key")
        param_key = payload.get("param_key")
        value = payload.get("value")
        guids = payload.get("guids")
        if not type_key or not param_key:
            return {"error": "missing type_key/param_key"}

        members = self._members_of(adapter, tree, type_key, guids)
        applied = 0
        for _node, holder in members:
            try:
                setattr(holder, param_key, self._coerce(holder, param_key, value))
                applied += 1
            except Exception:
                pass

        if applied:
            doc.undo_push("Overseer: align generators")
            doc.tag_redraw()
        return {"ok": True, "applied": applied}

    def _in_view_layer(self, view_objects, obj) -> bool:
        """Whether ``select_set`` can act on ``obj``. ``Object.select_set``
        raises RuntimeError for objects absent from the active view layer
        (excluded collection, other scene). When membership cannot be
        determined we return True and let the guarded ``select_set`` be the
        final arbiter."""
        if view_objects is None:
            return True
        try:
            return obj.name in view_objects
        except Exception:
            return True

    def _select_guids(self, adapter, doc, guids, progress=None):
        bpy = adapter.bpy
        try:
            for o in doc.selected_objects():
                o.select_set(False)
        except Exception:
            pass

        try:
            view_objects = bpy.context.view_layer.objects
        except Exception:
            view_objects = None

        selected = 0
        skipped = 0
        active = None
        total = len(guids)
        for i, guid in enumerate(guids):
            if progress and total > 500 and i % 500 == 0:
                progress("Selecting generators", i, total, "")
            obj = adapter._by_guid.get(guid)
            if obj is None:
                continue
            if not self._in_view_layer(view_objects, obj):
                skipped += 1
                continue
            try:
                obj.select_set(True)
                active = obj
                selected += 1
            except Exception:
                skipped += 1
        if active is not None:
            try:
                bpy.context.view_layer.objects.active = active
            except Exception:
                pass
        doc.tag_redraw()
        return selected, skipped

    def select(self, doc, adapter, tree, payload):
        type_key = payload.get("type_key")
        param_key = payload.get("param_key")
        if not type_key:
            # Direct guid selection fallback (task contract); the frozen UI
            # drives selection by type/param/value, handled below.
            guids = payload.get("guids") or []
            selected, skipped = self._select_guids(adapter, doc, guids)
            return {"ok": True, "selected": selected, "skipped": skipped}

        members = self._members_of(adapter, tree, type_key)
        if param_key is not None and "value" in payload:
            wanted = self._hashable(payload.get("value"))
            members = [(n, h) for n, h in members
                       if self._hashable(self._read(h, param_key)) == wanted]

        guids = []
        seen = set()
        for node, _holder in members:
            if node.guid not in seen:
                seen.add(node.guid)
                guids.append(node.guid)
        selected, skipped = self._select_guids(adapter, doc, guids)
        return {"ok": True, "selected": selected, "skipped": skipped}


AUDIT = BlenderGeneratorsAudit()
