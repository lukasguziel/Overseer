# CLAUDE.md — Scene Organizer

Kontext-Datei für Claude Code. Kurz, aktuell, verbindlich. Bei Architektur-Änderungen mitpflegen.

## Was das ist

Cinema-4D-2024-Plugin, das Szenen (Interior/ArchViz) **analysiert**, **Objektnamen vereinheitlicht**
und die **Struktur optimiert** (Objekte in Gruppen wie Cameras/Lights/Furniture/Interior/Exterior).
Zwei Oberflächen auf derselben Logik: nativer C4D-Dialog **und** ein Web-Frontend (Vite/React) mit
Node-Editor fürs Regelwerk.

Beispiel-/Produktionsszene des Users: `D:\3D\PROJECTS\01 - SAMPLE\sample_0070.c4d` (~2.3 GB).

## Wichtigste Entscheidung: Plugin, NICHT headless

`c4dpy.exe` (2024) **hängt beim Start** an `No License Model defined` und wartet auf eine
stdin-Lizenzauswahl (Maxon App). Der User will das nicht. → **Aller Code läuft als Plugin in der
laufenden C4D-GUI** (bereits lizenziert, Szene offen, Änderungen Undo-fähig). c4dpy ist tabu.

## Architektur

**Kernprinzip: reine Domänenlogik strikt von `c4d` getrennt.** Das Package `src/sceneorg/` importiert
NIE `c4d` → in GitHub Actions ohne Cinema testbar. Nur diese Module importieren `c4d` und werden von
Tests nie geladen: `c4d_adapter.py`, `dialog.py`, `plugin_entry.py`, `bridge.py`, `webapi.py`.

```
src/
  scene_organizer.pyp     Loader. Registriert 3 Plugins (s.u.). Hot-Reload: purged bei jedem
                          Dialog-Aufruf alle sceneorg-Module AUSSER sceneorg.bridge und lädt neu.
  config.example.json     Vorlage -> als config.json neben den .pyp kopieren.
  sceneorg/
    model.py              SceneNode / SceneTree (reine Hierarchie)
    naming.py             Tokenizer, Casing-Erkennung (Casing-Enum), Sprach-Heuristik
    translations.py       DE<->EN Wörterbuch + add_translations() (Laufzeit-Erweiterung)
    convention.py         NamingConvention: normalisiert Namen (Casing/Sprache/Nummerierung), disambiguate()
    detect.py             Auto-Erkennung des vorhandenen Schemas (style/language/number_pad + Konfidenz)
    structure.py          GroupRule / StructureStandard: erwartete Gruppen + evaluate(); default_standard()
    ops.py                RenameOp/ReparentOp + plan_renames()/plan_reparents() (Scope, Kollisionen, Safety, Präfixe)
    analyzer.py           SceneAnalyzer: SceneTree -> SceneReport (Ein-Durchlauf)
    config.py             config.json (dict) -> Config(convention, standard, prefixes, extra_translations)
    c4d_adapter.py        [c4d] SceneAdapter: doc -> SceneTree lesen; Rename/Reparent mit Undo; selected_guids()
    dialog.py             [c4d] nativer GeDialog (Dropdowns, Checkboxen, Buttons)
    plugin_entry.py       [c4d] öffnet den Dialog
    bridge.py             [c4d] HTTP-Server (BG-Thread) + Main-Thread-Queue. PROZESS-SINGLETON.
    webapi.py             [c4d] JSON-API; bei jedem Request frisch reloaded
  web/                    Vite-Build-Output (von deploy.ps1 verteilt; gitignored)
frontend/                 Vite/React-App (Quelle des Web-UIs)
  src/App.jsx             Organizer-View (Settings + Diff-Tabellen)
  src/RuleGraph.jsx       Node-Editor (React Flow) fürs Regelwerk
  src/api.js              fetch-Client (relative /api/*)
tests/                    pytest, laufen OHNE c4d (conftest baut SceneTrees + archviz_standard-Fixture)
.github/workflows/ci.yml  ruff + pytest auf Python 3.9 & 3.11
deploy.ps1                kopiert .pyp + config.example.json + sceneorg/ + web/ ins Plugin-Verzeichnis
```

## Plugin-IDs / Ports (in scene_organizer.pyp)

- Offizielle Maxon-Basis-ID: `1069217` ("GFCSceneOrganizer"). Die vier global registrierten
  Elemente leiten sich als zusammenhaengender Block daraus ab (raus aus dem geteilten Dev-Range):
- `1069217` CommandData "Scene Organizer" (nativer Dialog)
- `1069218` Dialog-ID (GeDialog, nativer Dialog; plugin_entry.py)
- `1069219` CommandData "Scene Organizer (Web)" (startet Server + Kontroll-Dialog)
- `1069220` ServerDialog-ID (draint die Queue per Timer, s.u.; bridge.py)
- Web-Port `8787`.
- **KEINE MessageData mehr.** Beim Start werden NUR die zwei CommandData registriert (kein
  Startup-Risiko). Die Web-Request-Queue wird vom Timer des ServerDialog (bridge.ServerDialog,
  `SetTimer(100)`) auf dem Main-Thread abgearbeitet — nur solange dieses Fenster offen ist.

## Deploy-Ziel

Anwendungsweiter Plugin-Ordner (globale CLAUDE.md; `deploy.ps1` schreibt hierhin -> **braucht Admin**):

`C:\Program Files\Maxon Cinema 4D 2024\plugins\SceneOrganizer\`

Alternative ohne Elevation: der User-Prefs-Ordner
`%APPDATA%\Maxon\Maxon Cinema 4D 2024_A5DBFF93\plugins\SceneOrganizer\` (C4D laedt beide gleichwertig).

## Commands

```bash
python -m pytest                 # Unit-Tests (ohne c4d), aktuell 103 grün
python -m ruff check src tests   # Lint (muss sauber sein — CI-Gate)
python -m ruff check --fix src tests

cd frontend && npm install
cd frontend && npm run build     # Output -> src/web/  (danach deploy.ps1)
cd frontend && npm run dev       # Dev-Server mit HMR, Proxy /api -> localhost:8787

powershell -File deploy.ps1      # ins C4D-Plugin-Verzeichnis kopieren
```

Syntax-Check der c4d-Dateien ohne Cinema: `py_compile` (kompiliert, führt `import c4d` nicht aus).
Server-Smoke-Test ohne Cinema: `c4d` als leeres Modul stubben (`SpecialEventAdd = lambda *a: None`),
`bridge.start()`, statischer GET `/` prüfen (Static-Pfad braucht keinen Main-Thread).

## Bedienung in C4D

Nach 1× Neustart (registriert die Plugins): `Shift+C` →
- **"Scene Organizer"** — nativer Dialog.
- **"Scene Organizer (Web)"** — startet Server, öffnet `http://127.0.0.1:8787`.

Web-Endpoints: `/api/analyze`, `/api/export`, `/api/detect`, `/api/rules`,
`/api/plan_naming`, `/api/apply_naming`, `/api/plan_structure`, `/api/apply_structure`, `/api/config`.

## Dev-Workflow: was braucht einen Neustart?

- **Reine `sceneorg`-Logik / `dialog.py`**: kein Neustart. `deploy.ps1` → Command erneut klicken (Hot-Reload).
- **Frontend**: `npm run build` + deploy → Browser neu laden (bzw. HMR im Dev-Server).
- **`bridge.py`, `webapi`-Signatur, `.pyp`**: C4D-Neustart nötig (eingefrorene, registrierte Teile).
  `bridge` ist bewusst vom Hot-Reload-Purge ausgenommen (Queue/Server-Singleton, sonst Request-Verlust).

## Domänen-Konzepte

- **Kategorien**: light, camera, null, mesh, spline, other (vom Adapter aus c4d-Typ + Name-Fallback).
- **Casing-Stile**: PascalCase, camelCase, lower_snake, UPPER_SNAKE, kebab (erzeugbar); Erkennung
  zusätzlich UPPER/lower/Capitalized/spaced/mixed.
- **NamingConvention**: tokenisieren → (optional) DE↔EN übersetzen → Casing anwenden → Zahl mit Padding.
  Ist idempotent (property-getestet). `disambiguate()` macht Namen pro Elternobjekt eindeutig.
- **StructureStandard / GroupRule**: Objekt → Zielgruppe via Kategorie ODER (ins Englische übersetzte)
  Keywords. `aliases` erkennen bestehende, anders benannte Container (z.B. „Möbel" == „Furniture").
- **Safety-Filter** (`is_safe_to_reparent`): nur verschieben, wenn Elternteil Wurzel oder Null →
  Generator-/Deformer-Kinder (Cloner, Boole, Sweep …) bleiben unangetastet. Default an.
- **Scope**: „nur Auswahl" beschränkt Operationen auf `selected_guids()` (inkl. Kinder).
- Alle Schreiboperationen laufen über `doc.StartUndo/AddUndo/EndUndo` → per Strg+Z rückgängig.

## Konfiguration (config.json neben der .pyp)

Optional. Überschreibt: `casing`, `language` (en/de/null), `number_pad`, `prefixes`
(z.B. `{"light":"LGT_"}`, idempotent), `translations` (extra de→en), `groups` (Regelwerk).
Der Node-Editor speichert `groups` + `graph` (Editor-Layout) hierher via `POST /api/config`.
`default_standard()` enthält bewusst NUR Cameras+Lights — inhaltliche Gruppen kommen aus config.json.

## Konventionen für Änderungen

- Neue reine Logik → in `sceneorg/` (kein `c4d`-Import) + Test in `tests/`. `pytest` und `ruff` müssen grün sein.
- c4d-abhängiges → nur in den [c4d]-Modulen; nicht in Tests importieren.
- Ruff-Config in `pyproject.toml` (ignoriert bewusst UP031 %-Format, UP042 StrEnum wegen 3.9-Support).
- Deutsche Kommentare/Strings ohne Umlaute in Python-Quellen bevorzugen (Encoding-Sicherheit), UI-Texte dürfen Umlaute.

## Aktueller Stand / nächster Schritt

Plugin läuft (User bestätigt). Web-UI + Node-Editor stehen. **Offen:** Der User exportiert seine echte
Szene über den Button **„Komplette Struktur exportieren"** → schreibt `scene_report.json` ins Repo-Root.
Claude liest die Datei, analysiert reales Naming + Struktur und baut daraus das **echte Regelwerk**
(config.json + Node-Graph-Vorbelegung), das der User im Editor feinjustiert.

## Merkzettel / Stolpersteine

- c4dpy = Sackgasse (Lizenz-stdin-Hang). Immer im Plugin arbeiten. **ACHTUNG:** hängengebliebene
  `c4dpy.exe`-Prozesse belegen die Maxon-Lizenz -> Cinema-4D-Start blockiert bei „initializing
  plugins" (wartet auf freie Lizenz). Diagnose bei langsamem/blockiertem Start ZUERST:
  `tasklist | grep -i c4dpy` und alle killen. (War die reale Ursache eines vermeintlichen
  Plugin-Startup-Hangs.)
- Main-Thread-Draining läuft über den Timer des ServerDialog, NICHT über MessageData (letztere
  barg Startup-Risiko). Server-Dialog offen lassen, solange die Web-UI genutzt wird.
- `bridge` niemals in den Hot-Reload-Purge aufnehmen.
- Dokument-Zugriff nur auf dem Main-Thread → Web-Requests laufen über die Bridge-Queue.
- `scene_report.json` (Repo-Root) ist der Kanal, über den Claude die echte Szene sieht.
- **c4d-Plugin-Basisklassen (CommandData/MessageData/GeDialog): wenn `__init__` überschrieben wird,
  MUSS `super().__init__()` aufgerufen werden — sonst korrupter C++-Teil → C4D-Freeze beim Start.**
  Bei MessageData daher lieber gar kein `__init__`; schwere Imports erst faul im Event. `main()` im
  .pyp defensiv kappseln (jede Register-Zeile in try/except), damit ein Fehler C4D nicht lahmlegt.
- Bridge/MessageData werden erst nach echtem C4D-Neustart aktiv (nicht per Hot-Reload) — Startup-Bugs
  dort zeigen sich erst beim nächsten Kaltstart.
