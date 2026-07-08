# Scene Organizer — code docs

Source files carry no docstrings or explanatory comments (see
[.claude/rules.md](../.claude/rules.md)). The prose lives here instead — one
markdown file per module, mirroring `src/`.

## Entry / host glue
- [scene_organizer.md](scene_organizer.md) — plugin loader (`src/scene_organizer.pyp`)
- [sceneorg/bridge.md](sceneorg/bridge.md) — HTTP server + main-thread queue (process singleton)
- [sceneorg/config.md](sceneorg/config.md) — config.json schema 2 + migration

## cinema/ — the only c4d-dependent domain code
- [sceneorg/cinema/adapter.md](sceneorg/cinema/adapter.md) — doc ⇄ SceneTree, writes with undo
- [sceneorg/cinema/webapi.md](sceneorg/cinema/webapi.md) — JSON API (hot-reloaded per request)
- [sceneorg/cinema/constants.md](sceneorg/cinema/constants.md) — c4d-bound constant tables

## core/ — pure hierarchy + planning
- [sceneorg/core/model.md](sceneorg/core/model.md) — SceneNode / SceneTree
- [sceneorg/core/analyzer.md](sceneorg/core/analyzer.md) — SceneTree → SceneReport
- [sceneorg/core/ops.md](sceneorg/core/ops.md) — plan renames / reparents / layers
- [sceneorg/core/pipeline.md](sceneorg/core/pipeline.md) — combined one-pass planning
- [sceneorg/core/imagesize.md](sceneorg/core/imagesize.md) — header-only image dimension reader
- [sceneorg/core/defaults.md](sceneorg/core/defaults.md) — central built-in domain constants

## naming/
- [sceneorg/naming/casing.md](sceneorg/naming/casing.md) — tokenizer, casing + language heuristics
- [sceneorg/naming/convention.md](sceneorg/naming/convention.md) — NamingConvention
- [sceneorg/naming/detect.md](sceneorg/naming/detect.md) — auto-detect existing scheme
- [sceneorg/naming/translate.md](sceneorg/naming/translate.md) — language-only rename proposals
- [sceneorg/naming/translations.md](sceneorg/naming/translations.md) — DE↔EN dictionary

## structure/
- [sceneorg/structure/standard.md](sceneorg/structure/standard.md) — GroupRule / StructureStandard
- [sceneorg/structure/rules.md](sceneorg/structure/rules.md) — declarative rule engine v2
- [sceneorg/structure/graph.md](sceneorg/structure/graph.md) — node-editor graph
