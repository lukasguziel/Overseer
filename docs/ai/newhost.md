# Porting Overseer to a new 3D host — the playbook

When the user says "port this to Houdini / Maya / 3ds Max / …", follow this
file top to bottom. The Blender port was built exactly this way: `blender/` is
the reference implementation of this playbook, `cinema/` is the origin. Read
[hostapi.md](hostapi.md) (the contract) and [core.md](core.md) (the areas)
first.

## What you get for free

The web frontend (frozen JSON `/api` contract), ALL op logic
(`core/hostapi/webapi.py`), every area's pure logic and display shaping
(the `core/<area>` base/audit classes), config/journal/history/updater. A host
port writes ONLY the glue: ~15 small modules mirroring the area layout, plus a
loader and a bridge. Nothing in `core/` or `frontend/` changes.

## Step 0 — the host questionnaire (answer BEFORE writing code)

Start `docs/ai/<host>.md` as the port's design doc (model: [blender.md](blender.md))
and answer these. Every past porting bug traces back to one of them:

1. **Embedded Python?** Which version? Code must stay 3.9-syntax-clean (ruff
   gate) — the runtime may be newer.
2. **Main-thread rule.** Which API calls are main-thread-only? What is the
   deferred-execution primitive that runs a callback on the main thread
   (C4D: `GeDialog.Timer`; Blender: `bpy.app.timers`; Houdini would be
   `hdefereval`)? The HTTP server always stays on a background thread and only
   enqueues.
3. **O(1) dirty signal.** Something that bumps on data edits but NOT on
   selection/camera moves (keys the cross-request scene cache). If the host
   has none, register an edit-event callback that bumps a monotonic epoch in
   the process singleton (the Blender pattern, `blender/host.py`).
4. **Stable per-object id** within a session (C4D `GetGUID()`, Blender
   `session_uid`). Needed for the journal/revert (`_by_sid`).
5. **Hierarchy.** How to enumerate roots and children in a stable order; how
   to read point/poly counts of the *evaluated* result (modifiers/generators
   applied).
6. **Categories.** Map host object types onto light/camera/null/mesh/spline/
   other (`core.scene.model.CAT_*`) — goes into `<host>/constants.py`.
7. **The layer-equivalent.** The host's grouping/color primitive the layers
   AREA maps onto (C4D: layers; Blender: collections; Houdini: pick one —
   e.g. bundles — and write the decision down). This is a product decision,
   not a technical one: ask the user if ambiguous.
8. **Undo batching.** How to wrap a batch of edits into ONE user-visible undo
   step (C4D: `StartUndo`/`AddUndo`/`EndUndo`; Blender: one `undo_push` after;
   Houdini: `hou.undos.group()`).
9. **Selection.** Read AND write — and does the read work inside the deferred/
   timer context? (Blender's `bpy.context.selected_objects` silently does not;
   that bug shipped once. Route every selection read through the doc wrapper.)
10. **Per-area vocabulary.** What does the host call tags / generators / sims /
    external file refs? If a concept genuinely does not exist, the area's
    `has_any` returns False and the tab hides — never fake data.
11. **Native file/folder pickers** reachable from the pump context? If not,
    return `{"cancelled": True}` — the UI handles it.
12. **Data dir.** A per-user writable prefs/config dir (install dirs may be
    read-only) — feeds `webio.resolve_data_dir`.

## Step 1 — skeleton (mirror the area layout EXACTLY)

```
src/overseer/<host>/
  __init__.py  constants.py  context.py  webapi.py
  host.py  pump.py  server.py  reload.py     process singleton (copy the
                                             Blender four; server.py is
                                             host-neutral, near-verbatim)
  scene/    doc.py (SceneHost wrapper)  readers.py  adapter.py
  organize/ apply.py  journal.py
  layers.py  materials.py
  textures/ paths.py  resize.py  previews.py
  tags.py  generators.py  sims.py  files.py  perf.py
src/plugin/<host>/   the loader (ONLY what the host's plugin format demands)
```

Rules: only `src/overseer/<host>/` may import the host SDK, and NEVER at
module load time — import it lazily inside functions (the Blender rule; it is
what lets a fake SDK module drive the whole package in CI).

**Registration:** core is host-agnostic and carries NO host values. The host
registers its values in `<host>/constants.py` — `DEFAULT_PORT` (own port, so
hosts run side by side) and `UPDATE_PROFILE` (release-asset shape for the
clean `updater.UpdateTarget`) — and surfaces them through its `HostContext`
(`default_port`, `update_profile`). Add a `test_<host>_registration.py` in
`tests/<host>/` (copy the Blender/Cinema ones); `tests/test_import_graph.py::
test_core_is_host_agnostic` enforces the direction.

## Step 2 — build order (walking skeleton first)

Each step is verifiable in the real host via the web UI before the next:

1. Loader + singleton (`host/pump/server/reload`) → the browser opens,
   `/api/netinfo` answers.
2. `scene/doc.py` (SceneHost) + `scene/readers.py` + `build_tree` in
   `scene/adapter.py` → the Scene tab renders the live tree.
3. `organize/apply.py` + `journal.py` → rename/revert round-trips.
4. `layers.py`, `materials.py`, `textures/` → their tabs fill.
5. One `<area>.py` per audit: subclass `core/<area>/audit.py`, implement the
   abstract primitives, expose `AUDIT = <Host><Area>Audit()`.
6. `context.py` (HostContext: paths, progress, pickers, `audit(prefix)` map)
   + `webapi.py` (3 lines: bind `WebApi(<Host>Context())`).

## Step 3 — the contracts

- `core/hostapi/ports.py` is the compile-time checklist: a concrete class with
  a missing method cannot instantiate. The adapter areas are template-method
  bases (`core/<area>/base.py`): implement the abstract `get_*`/`set_*`
  primitives and the base runs the shared workflow; override a base method
  only where your host genuinely needs a different flow.
- Result shapes: build every row/envelope via the `core/<area>` factories
  (`layer_entry`, `texture_row`, `file_entry`, per-area `scan_result`,
  `organize.journal.change_item`, ...) — never hand-assemble the dicts. What
  has no factory yet: mirror `cinema/<area>.py` key-for-key (`docs/api.md`).
  The frontend is frozen.
- Guid semantics, cache invalidation (`invalidate_scene_cache` on mutating
  ops), progress publish + clear-in-finally: identical to both hosts (see
  [hostapi.md](hostapi.md) and the gotchas below).

## Step 4 — tests without the SDK

Create `tests/<host>/` with:
- `fake<sdk>.py` — a minimal fake SDK module injected into `sys.modules`,
  modeled on `tests/blender/fakebpy.py`. Only model what the code under test
  touches; grow it per test.
- `test_ports.py` — introspection: the concrete `SceneHost`/`SceneAdapter`/
  audit classes have empty `__abstractmethods__` (copy
  `tests/blender/test_ports.py`).
- `test_<host>_compiles.py` — compile gate + area-mirror assertions (copy
  `tests/blender/test_blender_compiles.py`).
- a webapi contract test against the fake (`tests/blender/test_webapi_contract.py`
  pattern) for at least `analyze` + one mutation + revert.

`tests/test_import_graph.py` picks the new package up automatically — every
relative import is verified even though CI can never import the SDK.

## Step 5 — packaging, deploy, docs

- Deploy: add `deploy_<host>.ps1` to the deploy skill (copy
  `deploy_blender.ps1`) + a `<host>_targets` list in `deploy.config.json`.
- Release: `scripts/release/build_<host>_zip.py` modeled on
  `build_blender_zip.py`; wire it into `release.yml` when the host ships.
- Docs: finish `docs/ai/<host>.md` (questionnaire answers + concept-mapping
  table + gotchas found), extend the AGENTS.md tree, add the host to
  [hostapi.md](hostapi.md)'s status list.

## Universal gotchas (each bit us at least once)

- Never touch the SDK at module import time; loaders wrap every register call
  in try/except.
- Selection is NOT part of the dirty token — re-read it on every scene-cache
  hit.
- The deferred/timer context often lacks UI context — route selection/viewport
  calls through the `SceneHost` wrapper with explicit fallbacks.
- Hot-reload keep-list: singletons + their ancestor packages survive the purge,
  everything else re-imports per request. A kept submodule under a purged
  parent is orphaned.
- ONE undo step per mutation; progress cleared in `finally`.
- All writes go to the per-user data dir, never the install dir.

## Sanity check: "port it to Houdini"

The questionnaire answers itself well for Houdini (unverified sketch — confirm
against the hou docs during Step 0): embedded Python via `hou`,
main-thread via `hdefereval.executeDeferred`, undo via `hou.undos.group()`,
stable ids via `hou.Node.sessionId()`, hierarchy from `/obj` children,
external refs via `hou.fileReferences()` (a gift for the files area), sims =
DOP networks, perf = cook timings. The open product decision is the
layer-equivalent (bundles vs. network boxes) — ask, then follow Steps 1-5.
