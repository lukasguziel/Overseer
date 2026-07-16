# Roadmap to 1.0

Current release: **1.0.0** (leaner core: retired structure/rules era removed).
This file turns the beta feedback into concrete, ordered features. Check items
off as they ship; when the list is done we cut 1.0.

## Beta feedback digest (2026-07-10)

Verbatim themes from the tester, grouped:

1. **Layers tab gaps** — no way to delete empty layers; "empty" must mean *no
   objects AND no materials* (layers are commonly used to sort materials, not
   just geo); the "no layer" column should *suggest* a layer (inherit the
   parent's layer when children have none).
2. **Mixed-layer hierarchies are often intentional** — a Null on layer 1 with
   children on layer 3 is frequently deliberate; flag it as a finding the user
   can accept, never auto-"fix" it.
3. **Guided flow + tooltips** — a wizard that walks through layer findings so
   the user only presses yes/no; hover tooltips throughout the web UI.
4. **Full revert / persistent history** — log every change the plugin makes,
   store the history *with the scene*, and allow selective revert ("the
   45° phong change was dumb, undo just that — keep the rest").
5. **Linked-textures category** — list every referenced texture with
   absolute/relative path marking, offer Python-based resize (25/50/75 %),
   plus per-texture analysis: VRAM cost, channels used, colorspace,
   RGB vs. greyscale, alpha present.

## Planned features

### M1 — Layers overhaul (highest impact, smallest surface)

- [x] **Delete empty layers** action in the Layers tab (single + "delete all
      empty"), one undo step.
- [x] **True emptiness check**: a layer counts as empty only when no objects,
      no materials, and no tags reference it. Requires extending the adapter's
      layer scan to material/tag `[c4d.ID_LAYER_LINK]`.
- [x] **Layer suggestions for unassigned objects**: if an object has no layer
      but an ancestor does, propose the ancestor's layer. Pure logic in
      `core/ops.py` (`plan_layers` extension), rendered as accept/reject rows.
- [x] **Intentional-mismatch finding, not fix**: parent on layer A, children on
      layer B → report as an informational finding with an "accept as-is" keep
      (existing keeps mechanism), never part of an auto-apply.

### M2 — Change history + selective revert (trust feature)

- [x] **Change journal**: every applied op (rename/reparent/layer/tag edit)
      appends a record `{ts, section, op, target-uuid, before, after}`.
- [x] **Persist with the scene**: journal stored in a scene BaseContainer
      (survives save/load) plus a sidecar JSON next to the .c4d as fallback.
- [x] **History tab**: chronological list grouped by apply-run; per-run and
      per-op **selective revert** (re-applies the `before` values via the
      adapter, one undo step per revert).
- [x] **Full revert button**: revert an entire run in one click.
- [x] Robustness: reverting ops whose targets were deleted/renamed since →
      skip with a clear per-row note, never abort the whole revert.

### M3 — Guided mode + tooltips (UX polish)

- [x] **Layer guide / wizard**: sequential card flow over all layer findings —
      one finding, plain-language explanation, Yes/No/Skip buttons. Reuses the
      existing plan/keeps backend; purely a frontend mode.
- [x] **Hover tooltips** on every non-obvious control and table column across
      all tabs (shared `<Tip>` component).
- [ ] Later: extend the guide pattern to Naming and Structure tabs.

### M4 — Textures deep-dive (extends the Files/Assets tabs)

- [x] **Linked textures list**: every referenced texture with resolved path,
      **absolute vs. relative** badge, exists/missing state, which materials/
      channels use it. (Materials tab · Textures section.)
- [x] **Per-texture analysis**: resolution, bit depth, RGB vs. greyscale,
      alpha channel, colorspace tag, estimated **VRAM cost** (also aggregated —
      feeds the existing Overview texture-budget card real numbers). Pure
      header parsers in `core/textures.py` (Pillow when importable, else
      struct-based PNG/JPEG/TIFF/EXR/BMP/TGA/HDR).
- [x] **Batch resize** to 25 / 50 / 75 % via Python (Pillow if available in the
      C4D Python env, else pure-Python PNG fallback). Writes resized copies
      next to the originals (`_50` suffix) and relinks materials — original
      files are never overwritten; relink is journaled (M2, `texpath` field)
      so it is revertible.
- [x] **Make relative/absolute** path conversion helpers (`texture_repath`,
      journaled).

## Ordering rationale

M1 and M3's layer guide answer the most concrete complaints and are cheap.
M2 is the trust feature that makes aggressive use safe ("brutales plugin" —
revert removes the remaining fear) and is a prerequisite for M4's relinking.
M4 is the biggest new surface and lands last before 1.0.

## Release plan

- 0.9.x betas: one milestone per beta drop, tester feedback loop after each.
- 1.0: all four milestones shipped + README/FEATURES regenerated.
