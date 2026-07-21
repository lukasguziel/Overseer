# Overseer — code docs

Source files carry no docstrings or explanatory comments (see
[ai/rules.md](ai/rules.md)). The prose lives here instead — one
markdown file per module, mirroring `src/`.

Per-package working guides for AI agents (conventions, gotchas, module maps —
formerly per-package instruction files inside the source tree): [ai/](ai/).

## Entry / host glue
- [plugin/cinema4d.md](plugin/cinema4d.md) — C4D plugin loader (`src/plugin/cinema4d/overseer.pyp`)
- [overseer/bridge.md](overseer/bridge.md) — HTTP server + main-thread queue (process singleton)
- [overseer/config.md](overseer/config.md) — config.json schema 2 + migration

## cinema/ — the only c4d-dependent domain code
- [overseer/cinema/adapter.md](overseer/cinema/adapter.md) — doc ⇄ SceneTree, writes with undo
- [overseer/cinema/webapi.md](overseer/cinema/webapi.md) — JSON API (hot-reloaded per request)
- [overseer/cinema/constants.md](overseer/cinema/constants.md) — c4d-bound constant tables

## core/ — pure hierarchy + planning
- [overseer/core/model.md](overseer/core/model.md) — SceneNode / SceneTree
- [overseer/core/analyzer.md](overseer/core/analyzer.md) — SceneTree → SceneReport
- [overseer/core/ops.md](overseer/core/ops.md) — plan renames / reparents / layers
- [overseer/core/imagesize.md](overseer/core/imagesize.md) — header-only image dimension reader
- [overseer/core/defaults.md](overseer/core/defaults.md) — central built-in domain constants

## naming/
- [overseer/naming/casing.md](overseer/naming/casing.md) — tokenizer, casing + language heuristics
- [overseer/naming/convention.md](overseer/naming/convention.md) — NamingConvention
- [overseer/naming/detect.md](overseer/naming/detect.md) — auto-detect existing scheme
- [overseer/naming/translate.md](overseer/naming/translate.md) — language-only rename proposals
- [overseer/naming/translations.md](overseer/naming/translations.md) — DE↔EN dictionary

## structure/
- [overseer/structure/standard.md](overseer/structure/standard.md) — GroupRule / StructureStandard
- [overseer/structure/rules.md](overseer/structure/rules.md) — declarative rule engine v2
- [overseer/structure/graph.md](overseer/structure/graph.md) — node-editor graph
