# Plugin-Logik — was die deterministische Engine kann (und was nicht)

Kurzmodell von `src/sceneorg/`, damit Insights und Plaene zur echten Engine
passen. Kernprinzip: reine Logik (`sceneorg/`) importiert nie `c4d`; nur
`cinema/` (adapter/webapi) und `bridge` sind c4d-abhaengig.

## Pipeline pro Feature

- **Naming** (`convention.py` + `ops.plan_renames`): tokenisieren →
  optional DE↔EN uebersetzen (`translations.py` + config-`translations`) →
  Casing anwenden → Nummer mit `number_pad`. Idempotent (property-getestet);
  `disambiguate()` macht Namen pro Parent eindeutig; `prefixes`
  (z.B. `{"light":"LGT_"}`) sind idempotent.
- **Detect** (`detect.py`): erkennt vorhandenes Schema (style/language/
  number_pad + Konfidenz) aus allen Namen — Basis fuer Schritt "Konvention
  lernen", wenn man die Live-API nutzt statt Reports zu aggregieren.
- **Structure** (`structure.py` + `ops.plan_reparents`): GroupRule matcht
  per Kategorie ODER (uebersetzten) Keywords; `aliases` mappen bestehende
  Container. `evaluate()` liefert `misplaced` + `structure_compliance`.
  **Safety-Filter** (`is_safe_to_reparent`, default an): bewegt nur Objekte,
  deren Parent Root oder Null ist — Generator-/Deformer-Kinder bleiben.
  `tidy=true` beschraenkt auf "lose" Objekte.
- **Translate** (`translate.py`): schlaegt nur Sprach-Uebersetzungen vor,
  laesst Casing/Struktur in Ruhe; `apply_translate` wendet nur vom User
  akzeptierte guids an. **Fuer diesen User meist das richtige Tool** —
  sein Title-Case-Stil ist nicht producible, also kein szenenweites Naming.
- **Layers** (`ops.plan_layers`): verteilt Objekte auf C4D-Layer statt sie
  umzuhaengen — strukturschonende Alternative zum Reparenting.
- **Preset/Plan/Config**: `apply_preset` schreibt config.json;
  `apply_plan` fuehrt Skill-Plaene aus (siehe plan-format.md). Beides
  hot-reloaded — kein C4D-Neustart, nur Web-Dialog offen.

## Kategorien & Casing

- Kategorien: `light, camera, null, mesh, spline, other` (aus c4d-Typ +
  Name-Fallback im Adapter).
- Producible Casing: PascalCase, camelCase, lower_snake, UPPER_SNAKE, kebab.
  Nur erkannt: UPPER, lower, Capitalized, spaced, mixed.

## Grenzen — hier uebernimmt der Skill (die KI)

- **Semantik**: Raeume/Etagen/Zonen zuordnen kann keine Regel → Plan-Datei.
- **Flaches Modell**: `structure_compliance` 0.0 ist bei diesem User oft ein
  False Negative (bewusst flaches Arbeiten) — Struktur NICHT automatisch
  "reparieren", nur Naming/Translate/Layers anbieten (Memory
  `scene-structure-flat-model`).
- `default_standard()` enthaelt bewusst nur Cameras+Lights — inhaltliche
  Gruppen kommen aus config.json/Preset.
- `.c4d`-Dateien sind offline NICHT lesbar (binaer; c4dpy ist tabu wegen
  Lizenz-stdin-Hang). Einzige Datenquelle: Reports aus dem laufenden Plugin.

## Dev-Regeln bei Code-Aenderungen im Zuge des Skills

- Neue reine Logik → `sceneorg/` (kein c4d-Import) + pytest; `pytest` und
  `ruff check src tests` muessen gruen sein.
- `bridge.py`/`.pyp`-Aenderungen brauchen C4D-Neustart; alles andere ist
  hot-reloaded (deploy.ps1 → Command erneut klicken).
