---
name: readme
description: >-
  Regenerate the project README (English) with fresh screenshots of every web
  UI tab, rendered from a fake 1.2 GB / 40M-polygon sample scene via a mock
  API server + Playwright — no Cinema 4D needed. Use when the user says
  "update die readme", "mach neue screenshots", "readme neu generieren", or
  after shipping a feature that changes a tab's UI or adds a new tab.
---

# README — generate reproducibly

**Goal:** README.md stays permanently updatable in the same style: one
section per tab with a description, feature checklist (incl. the "why") and
a fresh screenshot from sample data. Screenshots are produced without C4D —
the built frontend runs against a mock server with a believable fake scene.

## Pipeline (3 commands)

```bash
cd frontend && pnpm run build && cd ..                      # 1. fresh UI bundle
node .claude/skills/readme/scripts/mock_server.mjs 8899 &   # 2. mock API + src/web (background)
node .claude/skills/readme/scripts/shoot.mjs 8899           # 3. screenshots -> docs/screenshots/
```

Kill the mock server process afterwards. `shoot.mjs` uses `playwright-core`
(devDependency in `frontend/`) with the system Chrome/Edge — no browser
download. Screenshots: 1440×960, DPR 2, status toast hidden.

**ALWAYS inspect the screenshots visually** (Read the PNGs): empty tabs,
broken layouts or `undefined` texts almost always mean `fixtures.mjs` no
longer matches the API contract (see below).

## Sample data (`scripts/fixtures.mjs`)

The fake scene is part of the style — keep it consistent when changing it:

- `penthouse_loft_final.c4d`, ~1,847 objects, **40M polygons, 1.2 GB**.
- **English object names** in all screenshots; only the Translate tab
  demonstrates translation, specifically EN→FR (`Chair → Chaise`) —
  `shoot.mjs` selects engine "Google" + target "French" in the tab for that.
- Deliberate problems so every feature has something to show: junk names
  (`Cube.1`), duplicates, mixed casing, unused materials, 8K textures,
  absolute paths, objects without layers, hidden objects.
- The node tree is a preorder list — `depth`/`children` must stay
  consistent (use the `group()`/`add()` helpers).

**New feature = new API endpoint?** Then add a response in `fixtures.mjs`
and register it in `mock_server.mjs` under `API` (unknown ops answer a
generic `{ok:true}`). The API contract lives in `frontend/src/types.ts` +
`frontend/src/api.ts`.

**New tab?** Extend the `TABS` list in `shoot.mjs` (nav label → file name);
parked "soon" tabs stay out.

## Style contract

Language: **English**. Two documents, both with the reference comment to
this skill at the top:

**README.md — short, product-oriented, EXACTLY ONE screenshot:**
1. Title + bold one-sentence pitch ("Keep your Cinema 4D scenes organized …").
   No version mention, no audience narrowing (applies to all project
   types), no sample-scene note.
2. Intro paragraph: what the tool does + the trust sentence (preview first,
   per-row, undoable, logged).
3. Overview screenshot (`docs/screenshots/overview.png`).
4. "What it does": link to docs/FEATURES.md, then EXACTLY ONE bullet
   sentence per tab (**Tab** — what it does). No "why" justifications.
5. Installation — noob-friendly, three steps, NO technical details
   (no IP/localhost/port mention, no server window, no Program Files
   paragraph): download the release zip → unzip and copy the `Overseer`
   folder into the Cinema 4D `plugins` folder → restart Cinema, `Shift+C`,
   search for "Overseer".
6. License: one paragraph — custom "Overseer License": free for private
   and commercial projects, modification for own use ok; no selling, no
   bundling into paid products, no redistribution as your own work; link to
   `LICENSE`. (Sits BEFORE Development — the mirror cuts Development
   through Support out, License must survive the cut.)
7. Development: test commands, note that `main` is the release branch
   (every push replaces the release of the stamped version; work happens
   on `dev`), reference to CLAUDE.md/docs.
8. **Support** (buy-me-a-coffee + issues) — stays the last section.

**docs/FEATURES.md — the detail tour, per tab exactly this form:**

```markdown
## <Tab name>

![<Tab name>](screenshots/<tab>.png)

<One sentence: what the area is, in user language.>

- ✅ **<Feature>** — <what it does / which problem it solves>.
- ✅ … (4–6 bullets, most important first)
```

Order = tab order of the app (Overview → Naming → Translate →
Assets → Layers → Materials → Misc). Always heading → screenshot →
features. Tone: concrete instead of marketing; reuse number examples from
the fake scene (`Chair → Chaise`, EN 1288 / DE 138) so text and screenshots
match.

## Failure modes

- `no system Chrome/Edge found` → add another `channel` in `shoot.mjs` or
  set `chromium.launch({executablePath})`.
- Screenshot shows an empty state → the mock server was not started from
  the repo root or `src/web/` is missing (run `pnpm run build` first).
- Tab missing from the shot → the nav label in `TABS` no longer matches
  the app (`frontend/src/lib/constants.ts`).
