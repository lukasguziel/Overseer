# scene_report.json — Schema & Umgang

Erzeugt von `POST /api/analyze` (bzw. Export-Button im Misc-Tab). Landet als
`var/scene_report.json` im Repo und in der API-Antwort unter `report`.

**Reports sind gross (1–2 MB, tausende Nodes) — NIE komplett in den Kontext
lesen. Immer per Python aggregieren** (`scripts/scan_reports.py`,
`scripts/learn_convention.py`) oder gezielt filtern.

## Top-Level-Felder (analyzer.SceneReport.to_dict)

| Feld | Bedeutung |
|---|---|
| `file` | Dateiname der Szene (`sample_0071.c4d`) |
| `object_count`, `max_depth` | Groesse/Verschachtelung |
| `total_points`, `total_polys` | Geometrie-Summen |
| `types` | Counter c4d-Typname → Anzahl |
| `categories` | Counter Kategorie (light/camera/null/mesh/spline/other) |
| `casing` | Counter erkannter Casing-Stile ueber alle Namen |
| `language` | Counter en/de/unknown |
| `top_level` | Root-Objekte: `{name, type, children}` |
| `polys_by_category`, `polys_by_group` | Polygon-Verteilung |
| `largest` | Top-12 schwerste Objekte `{guid,name,type,polygons,points}` |
| `lights_by_group`, `cameras_by_group` | wo Lichter/Kameras haengen |
| `structure_compliance` | 0..1 — ACHTUNG: 0.0 ist oft False Negative bei flachem Modell (siehe Memory `scene-structure-flat-model`) |
| `misplaced` | `{name, category, current, expected}` laut Regelwerk |
| `nodes` | ALLE Objekte, flach in Traversal-Reihenfolge (der grosse Teil) |
| `file_size`, `materials`, `analyzed_ts`, `analyzed_at` | von webapi ergaenzt |

## Node-Eintrag

```json
{"guid": 108, "name": "Küchenfenster", "type": "Polygon", "category": "mesh",
 "depth": 3, "path": "House/GroundFloor/Kitchen/Küchenfenster",
 "casing": "Capitalized", "language": "de", "children": 0,
 "points": 320, "polygons": 298}
```

- **`guid` = stabiler Index in Traversal-Reihenfolge**, NICHT der C4D-GUID.
  Pläne referenzieren darüber → gueltig nur, solange die Szene zwischen Export
  und `apply_plan` unveraendert bleibt.
- `path` = `/`-getrennte Namenskette ab Root — Hauptquelle fuer Semantik
  (Raum-/Etagen-Zuordnung, Praefixe wie `KITCHEN_`).

## Report als Datei erkennen (Ordner-Scan)

Ein JSON ist ein Scene-Report, wenn es `nodes` UND `object_count` enthaelt —
genau das prueft `scripts/scan_reports.py`.
