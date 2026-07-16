---
name: readme
description: >-
  Regenerate the project docs: the root README (English), docs/FEATURES.md
  and fresh screenshots of every web UI tab, rendered from a fake 1.2 GB /
  40M-polygon sample scene via a mock API server + Playwright — no Cinema 4D
  needed — and keep the GitHub repo About (description/homepage/topics) in
  sync with the README pitch. Use when the user says "update die readme",
  "mach neue screenshots", "readme neu generieren", or after shipping a
  feature that changes a tab's UI or adds a new tab.
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
2. Badge row + trailer embed (KEEP both verbatim): four shields.io badges —
   Trailer (YouTube link), Download (releases/latest), Docs
   (docs/FEATURES.md), Cinema 4D "2023 | 2024" (the tested versions —
   extend the badge when a new C4D version is verified; never a bare
   single-version pin) — followed by the clickable trailer
   thumbnail (GitHub cannot embed a playable YouTube iframe):
   `[![Watch the Overseer trailer](https://img.youtube.com/vi/jsoKxY_QdG0/maxresdefault.jpg)](https://www.youtube.com/watch?v=jsoKxY_QdG0)`
3. Intro paragraph: what the tool does + the trust sentence (preview first,
   per-row, undoable, logged).
4. Overview screenshot (`docs/screenshots/overview.png`).
5. "What it does": link to docs/FEATURES.md, then EXACTLY ONE bullet
   sentence per tab (**Tab** — what it does). No "why" justifications.
6. Installation — noob-friendly, three steps, NO technical details
   (no IP/localhost/port mention, no server window, no Program Files
   paragraph): download the release zip → unzip and copy the `Overseer`
   folder into the Cinema 4D `plugins` folder → restart Cinema, `Shift+C`,
   search for "Overseer".
7. License: one paragraph — custom "Overseer License": free for private
   and commercial projects, modification for own use ok; no selling, no
   bundling into paid products, no redistribution as your own work; link to
   `LICENSE`.
8. Development: test commands, note that `main` is the protected release
   branch (a PR into it replaces the release of the stamped version; work
   happens on `dev`/feature branches), reference to AGENTS.md/docs.
9. **Support** — stays the last section, keep it minimal: the shields.io
   "Support me" PayPal badge (donate link, no prose) + the GitHub Issues line.

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

## Repo About (GitHub) — keep in sync

The README pitch and the repo's About box must tell the same story. After
regenerating the README, compare and update if the pitch drifted:

```bash
gh repo view lukasguziel/overseer --json description,homepage,repositoryTopics
gh repo edit lukasguziel/overseer --description "<current one-sentence pitch>"
```

- Description = the README pitch in one sentence, **general-purpose** (the
  plugin analyzes any scene for insights, normalizes names/structure, keeps
  projects clean, manages assets, materials & textures) — NEVER narrow it
  to one niche like archviz/interior.
- Homepage stays the trailer link (`https://www.youtube.com/watch?v=jsoKxY_QdG0`).
- Topics: only touch when the feature story changes
  (`--add-topic`/`--remove-topic`).

## Failure modes

- `no system Chrome/Edge found` → add another `channel` in `shoot.mjs` or
  set `chromium.launch({executablePath})`.
- Screenshot shows an empty state → the mock server was not started from
  the repo root or `src/web/` is missing (run `pnpm run build` first).
- Tab missing from the shot → the nav label in `TABS` no longer matches
  the app (`frontend/src/lib/constants.ts`).
