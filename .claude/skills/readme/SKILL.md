---
name: readme
description: >-
  Regenerate the project README (English) with fresh screenshots of every web
  UI tab, rendered from a fake 1.2 GB / 40M-polygon sample scene via a mock
  API server + Playwright — no Cinema 4D needed. Use when the user says
  "update die readme", "mach neue screenshots", "readme neu generieren", or
  after shipping a feature that changes a tab's UI or adds a new tab.
---

# README — reproduzierbar generieren

**Ziel:** README.md bleibt dauerhaft im selben Stil aktualisierbar: pro Tab
eine Sektion mit Beschreibung, Feature-Checkliste (inkl. „warum") und einem
frischen Screenshot aus Sample-Daten. Screenshots entstehen ohne C4D — das
gebaute Frontend läuft gegen einen Mock-Server mit einer glaubwürdigen
Fake-Szene.

## Pipeline (3 Kommandos)

```bash
cd frontend && pnpm run build && cd ..                      # 1. frisches UI-Bundle
node .claude/skills/readme/scripts/mock_server.mjs 8899 &   # 2. Mock-API + src/web (Hintergrund)
node .claude/skills/readme/scripts/shoot.mjs 8899           # 3. Screenshots -> docs/screenshots/
```

Danach den Mock-Server-Prozess beenden. `shoot.mjs` nutzt `playwright-core`
(devDependency in `frontend/`) mit dem System-Chrome/Edge — kein
Browser-Download. Screenshots: 1440×960, DPR 2, Status-Toast ausgeblendet.

**Screenshots IMMER visuell prüfen** (Read auf die PNGs): leere Tabs, kaputte
Layouts oder `undefined`-Texte heißen fast immer, dass `fixtures.mjs` nicht
mehr zum API-Vertrag passt (siehe unten).

## Sample-Daten (`scripts/fixtures.mjs`)

Die Fake-Szene ist Teil des Stils — bei Änderungen konsistent halten:

- `penthouse_loft_final.c4d`, ~1.847 Objekte, **40M Polygone, 1,2 GB**.
- Deutsche Objektnamen mit echten Übersetzungsbeispielen
  (`Stuhl → Chair`, `Tuer_Eingang → Door_Entrance`).
- Absichtliche Probleme, damit jedes Feature etwas zu zeigen hat: Junk-Namen
  (`Cube.1`), Duplikate, gemischtes Casing, ungenutzte Materialien, 8K-Texturen,
  absolute Pfade, Objekte ohne Layer, versteckte Objekte.
- Der Node-Baum ist eine Preorder-Liste — `depth`/`children` müssen konsistent
  bleiben (Helper `group()`/`add()` benutzen).

**Neues Feature = neuer API-Endpoint?** Dann in `fixtures.mjs` eine Antwort
ergänzen und in `mock_server.mjs` unter `API` registrieren (unbekannte Ops
antworten generisch `{ok:true}`). Der API-Vertrag steht in
`frontend/src/types.ts` + `frontend/src/api.ts`.

**Neuer Tab?** In `shoot.mjs` die `TABS`-Liste erweitern (Nav-Label →
Dateiname); geparkte „soon"-Tabs bleiben draußen.

## README-Stilvertrag (README.md)

Sprache: **Englisch**. Reihenfolge der Sektionen = Tab-Reihenfolge der App.
Jede Tab-Sektion hat exakt diese Form:

```markdown
## <Tab name>

<Ein Satz: was der Bereich ist, in Nutzersprache.>

- ✅ **<Feature>** — <was es tut>. *Why: <welches Problem es löst>.*
- ✅ … (4–6 Punkte, wichtigstes zuerst)

![<Tab name>](docs/screenshots/<tab>.png)
```

Feste Rahmen-Sektionen (beibehalten, nur Inhalte aktualisieren):
1. Kopf: HTML-Kommentar mit Verweis auf diesen Skill, Titel, Ein-Satz-Pitch,
   Intro-Absatz, Hinweis auf die Sample-Szene.
2. Tab-Sektionen (Overview → Naming → Translate → Assets → Layers →
   Materials → Misc).
3. „The workflow in one paragraph".
4. Install (Releases-Link, Program-Files-Hinweis).
5. Development (Testkommandos, Verweis auf CLAUDE.md/docs).
6. **Support** (Buy-me-a-coffee-Link + Issues) — bleibt die letzte Sektion.

Tonalität: konkret statt Marketing; jedes „Why" nennt den echten
Artist-Schmerz. Zahlenbeispiele aus der Fake-Szene wiederverwenden (40M
Polygone, `Stuhl → Chair`), damit Text und Screenshots zusammenpassen.

## Fehlerbilder

- `no system Chrome/Edge found` → in `shoot.mjs` einen weiteren
  `channel` ergänzen oder `chromium.launch({executablePath})` setzen.
- Screenshot zeigt Empty-State → Mock-Server lief nicht vom Repo-Root oder
  `src/web/` fehlt (erst `pnpm run build`).
- Tab fehlt im Shot → Nav-Label in `TABS` stimmt nicht mehr mit der App
  überein (`frontend/src/lib/constants.ts`).
