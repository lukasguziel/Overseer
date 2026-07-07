# Scene Organizer

Cinema-4D-Plugin (2024) zum **Analysieren**, **Vereinheitlichen der Benennung**
und **Optimieren der Struktur** von Szenen — speziell für Interior/ArchViz
(Furniture / Interior / Exterior / Lights / Cameras).

## Warum Plugin statt headless (c4dpy)?

`c4dpy.exe` blockiert beim Start an der Lizenzauswahl (`No License Model
defined`, wartet auf stdin). Das Plugin läuft in der laufenden GUI — voller
Zugriff, kein Lizenzthema, Änderungen sind **Undo-fähig**.

## Architektur

Die reine Domänenlogik (`sceneorg/`, **ohne `c4d`-Import**) ist von der
C4D-Schicht getrennt, damit sie in GitHub Actions **ohne Cinema 4D** getestet
werden kann.

```
src/
  scene_organizer.pyp      Loader (CommandData). Lädt sceneorg bei jedem Klick
                           frisch -> Hot-Reload ohne C4D-Neustart.
  sceneorg/
    model.py               SceneNode / SceneTree (Hierarchie, rein)
    naming.py              Tokenizer, Casing-Erkennung, Sprach-Heuristik
    translations.py        DE<->EN Wörterbuch (ArchViz)
    convention.py          NamingConvention: normalisiert Namen auf ein Schema
    detect.py              Auto-Erkennung des vorhandenen Schemas
    structure.py           StructureStandard: erwartete Gruppen + Bewertung
    ops.py                 Rename-/Reparent-Operationen + Planer (rein)
    analyzer.py            SceneAnalyzer: Tree -> Report (Ein-Durchlauf)
    c4d_adapter.py         *einziges* c4d-Modul: Tree lesen + Ops mit Undo
    plugin_entry.py        öffnet den Dialog
    dialog.py              GeDialog (Buttons, Dropdowns)
tests/                     pytest, laufen ohne c4d
.github/workflows/ci.yml   ruff + pytest (Py 3.9 & 3.11)
```

## Bedienung in C4D

1. Einmalig: Plugin deployen (`deploy.ps1`) und Cinema 4D **einmal** neu starten.
2. `Shift+C` → „Scene Organizer".
3. Im Dialog:
   - **Format aus Szene ermitteln** — erkennt das vorhandene Schema und setzt die Dropdowns.
   - **Analysieren** — Typ-/Kategorie-Statistik, Casing/Sprache, Struktur-Konformität; schreibt `scene_report.json`.
   - **Naming-Vorschau / anwenden** — vereinheitlicht Namen (Casing, Sprache, Nummerierung).
   - **Struktur-Vorschau / anwenden** — gruppiert Lights/Cameras/Furniture/Interior/Exterior.

Alle Änderungen sind über `Strg+Z` rückgängig machbar.

## Web-Frontend (optional)

Neben dem nativen Dialog gibt es ein Vite/React-Frontend, das das Plugin über
einen lokalen Server ausliefert (Dokument-Zugriffe laufen thread-sicher über
eine Main-Thread-Queue):

```
frontend/            Vite/React-App (Dropdowns, Slider, Checkboxen, Diff-Tabellen)
  npm install
  npm run build      -> Output nach src/web/ (deploy.ps1 verteilt es)
  npm run dev        -> Dev-Server mit HMR, Proxy /api -> localhost:8787
src/sceneorg/bridge.py   HTTP-Server + Main-Thread-Queue (Singleton)
src/sceneorg/webapi.py   JSON-API (nutzt dieselbe sceneorg-Logik)
```

In C4D: `Shift+C` → **„Scene Organizer (Web)"** startet den Server und öffnet
`http://127.0.0.1:8787`. API-Endpoints: `/api/analyze`, `/api/detect`,
`/api/rules`, `/api/plan_naming`, `/api/apply_naming`, `/api/plan_structure`,
`/api/apply_structure`, `/api/config`.

## Entwicklung

```
python -m pytest          # Tests (ohne c4d)
python -m ruff check src tests
powershell -File deploy.ps1   # ins C4D-Plugin-Verzeichnis kopieren
```

Nach dem ersten Registrieren wirken Code-Änderungen an `sceneorg/` **ohne
Neustart** — einfach `deploy.ps1` und das Command erneut ausführen.
