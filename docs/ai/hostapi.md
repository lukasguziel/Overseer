# overseer.core.hostapi — the host-abstraction layer (ports & adapters)

Overseer runs the SAME features and the SAME web UI on multiple 3D hosts
(Cinema 4D, Blender, and — by design — future ones). This package is the formal
**contract** every host implements. It is pure (no `c4d`, no `bpy`): it defines
the ports; each host package (`cinema/`, `blender/`, …) provides the adapters.

## The shape

```
        web frontend  (frozen JSON /api contract — never host-specific)
              │
   core/hostapi/webapi.py   ONE op registry + all _op_* handlers + IO/cache/
              │             progress/history/journal. Written against the PORTS.
              │  drives
   ┌──────────┴───────────────────────────────┐   (a HostContext per host)
   │  PORTS  (core/hostapi/ports.py, abstract) │
   │   SceneHost      the "document"           │
   │   SceneAdapter   every area's read/write  │
   │   Audit          per-area op dispatch     │
   │   HostContext    wires host → the webapi  │
   └──────────┬───────────────────────────────┘
     implemented by ▼                 ▼ implemented by
        cinema/ (c4d)             blender/ (bpy)          maya/ … (future)
```

**Golden rule stays:** the frontend is frozen; the shared webapi returns one
canonical JSON shape per op. Hosts never see the JSON — they only implement the
ports, which speak the *normalized* domain types (`core.model.SceneTree`,
`ops.RenameOp`, the per-area result dicts defined by the port docstrings).

## The ports (`core/hostapi/ports.py`)

### `SceneHost` — the normalized "document"
What C4D calls a `doc` and Blender calls the active scene. Read-only host state
plus the mutation plumbing the webapi needs, nothing area-specific:
`name`, `path`, `dirty()` (O(1) edit token), `selection_token()`, `undo_push()`,
`objects()`, `roots()`, `tag_redraw()`, `status()`. (C4D: wraps `BaseDocument`;
Blender: `BScene`.)

### `SceneAdapter` — every area's read + write, as abstract methods
The one place the host-specific bodies live. Grouped by area, all abstract so a
new host gets a compile-time checklist:
- tree: `build_tree`, `selected_guids`, `focus`
- naming/structure: `rename_object`, `apply_renames`, `apply_reparents`, `revert`
- layers: `apply_layers`, `scan_layers`, `_layer_object_counts`, `delete_layer`,
  `delete_empty_layers`, `set_layer_colors`
- materials: `scan_materials`, `focus_material`, `delete_material`,
  `delete_unused_materials`
- previews: `material_previews`, `texture_previews`
- textures: `scan_textures`, `make_textures_relative`, `texture_owners`,
  `collect_textures`, `relink_textures`, `clear_missing_textures`,
  `set_texture_path`, `texture_repath`, `texture_resize`

Each method's **normalized return shape** is fixed by its docstring (the same
dict both hosts already produce). Hosts keep composing these from mixins; the
ABC just makes the contract explicit and enforced.

### `Audit` — per-area op dispatch
The tags/generators/sims/perf/files audits share the same signature
`handle(op, payload, host, adapter, tree, progress)` (+ `has_any` where the tab
is conditionally shown). The base handles op→method routing and result
assembly; the host overrides the read/apply primitives.

### `HostContext` — the wiring that lets one webapi drive any host
The small host-specific surface the shared webapi calls instead of importing a
host: `active_host()`, `make_adapter(host)`, `data_dir`/`plugin_dir`,
`progress`/`clear_progress`, the bridge facades (`server_port`, `lan_enabled`,
config read/write for `netinfo`), `type_icons(ids)`, `pick_texture_path` /
`pick_folder`, `audit(prefix)` → the host's `Audit` for that area, and the
auto-update surface (`host_label` + `update_profile` → the host's release-asset
shape from `core/defaults.py`; empty profile = updates unsupported). Registered
per host; `webapi.build_handle(ctx)` returns that host's `handle(payload)`.

## Adding a new 3D host (the whole checklist)

1. `newhost/scene/doc.py` → a `SceneHost` subclass (map name/path/dirty/
   selection/undo onto the host SDK).
2. `newhost/scene/adapter.py` (+ per-area mixin modules mirroring the core
   areas: `organize/apply.py`, `layers.py`, `materials.py`, `textures/…`) → a
   `SceneAdapter` subclass. The ABC lists every method; implement each against
   the host SDK, returning the normalized dicts. Reuse ALL of the
   `core/<area>/logic.py` modules — that logic is host-neutral and already
   normalized.
3. `newhost/<area>.py` for tags/generators/sims/perf/files → subclass the
   matching `core/<area>/audit.py` base, expose an `AUDIT` instance.
4. `newhost/context.py` → a `HostContext` binding the above + the bridge/loader.
5. `newhost/webapi.py` → `handle = hostapi.webapi.build_handle(NewHostContext())`.
   No op logic to rewrite — it is all in the shared webapi.
6. A loader (`.pyp` / addon `__init__.py` / …) that starts the bridge and opens
   the web UI.

Everything else — the web UI, naming, translation, analysis, per-area logic,
history/journal/export, caching, progress — is inherited unchanged.

## Migration status

- **Phase 1 (done):** ports defined; both hosts declare them as their base so
  the contract is enforced (a host missing a method can't instantiate).
- **Phase 2 (done):** the two near-identical `webapi.py` copies are extracted
  into `core/hostapi/webapi.py` (one `WebApi(ctx)`). `blender/webapi.py` (16
  lines) and `cinema/webapi.py` (19 lines) now just bind a `BlenderContext` /
  `CinemaContext`. Removed ~2400 lines of duplicated op logic. Each host has a
  `SceneHost` wrapper (`BScene`, `CDoc`) + a `HostContext`. **The C4D path is
  static-verified only** (no `c4d` in CI): ruff-clean, `py_compile`-clean, and
  every port method confirmed present — but it needs a local C4D smoke-test
  before merging to main (the release skill offers one).
- **Phase 3 (done):** per-area layout everywhere. `core/<area>/` holds the
  pure logic + the area's `Audit` base (`core/<area>/audit.py`); both hosts
  mirror the same area names (`cinema/tags.py`, `blender/tags.py`, …) and ship
  `Audit` subclasses exposing `AUDIT`. Adding a host is a per-area checklist,
  enforced by the mirror tests in `tests/cinema/` / `tests/blender/` and the
  static resolver in `tests/test_import_graph.py`.

See [blender.md](blender.md) for the concrete Blender mapping and
[cinema.md](cinema.md) for the C4D one.
