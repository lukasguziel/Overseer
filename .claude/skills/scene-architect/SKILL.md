---
name: scene-architect
description: >-
  Learn how the user organises Cinema 4D scenes from ONE OR MORE real projects,
  then (1) write a personal "how you work" preset, (2) give deterministic
  insights on what to improve using the Scene Organizer rules, and (3) freeze a
  logical restructuring into an executable plan the plugin runs WITHOUT any live
  AI/API calls. Use when the user says "lern wie ich arbeite", "bau ein Preset
  aus meinen Projekten", "analysiere mehrere Szenen", "schlag eine
  Umstrukturierung vor", or wants a restructuring plan.
---

# Scene Architect — Preset lernen + Umstrukturierung festschreiben

Die Idee: **Die KI (dieser Skill) läuft offline über die exportierten Szenen —
kein bezahlter API-Button im Plugin.** Sie friert ihr Verständnis in zwei
deterministische Artefakte ein, die das Tool danach ohne KI ausführt:

1. **Preset** (`src/presets/*.json`) — „so arbeitest du": Casing, Sprache,
   Übersetzungen, Gruppen. Deterministisch anwendbar via `/api/apply_preset`.
2. **Umstrukturierungs-Plan** (`src/plans/*.json`) — die *semantische* Arbeit,
   die Regeln nicht können (Räume/Etagen zuordnen). Ausführbar via
   `/api/apply_plan` (ein Undo-Schritt).

Dazwischen liefert die **deterministische Regel-Engine** (`sceneorg/`) die
Insights. Siehe auch [[scene-structure-flat-model]] und Skill `scene-rules`.

## Schritt 1 — Quelle interaktiv erfragen (Projekt / mehrere / Ordner)

ZUERST den User flüssig fragen, WAS analysiert werden soll — nicht raten. Nutze
das AskUserQuestion-Tool mit diesen Optionen (immer auch Custom zulassen, falls
nichts passt):

- **Aktuell offene Szene** — Live-API (`/api/analyze`), Web-Dialog muss offen sein.
- **Bestimmte Report-Datei(en)** — vorhandene `scene_report.json` / `reports/*.json`.
- **Ganzer Ordner** — scanne ihn nach exportierten Reports (`*.json`) und
  analysiere alle gefundenen zusammen.
- **Custom** — der User nennt Pfade/Projekte selbst.

Ordner scannen (Reports finden + Kurzinfo, ohne sie ganz zu lesen):
```bash
python -c "
import json,glob,sys
folder=sys.argv[1]
for f in sorted(glob.glob(folder+'/**/*.json',recursive=True)):
    try:
        d=json.load(open(f,encoding='utf-8'))
        if 'nodes' in d and 'object_count' in d:
            print(f, '->', d.get('file'), d.get('object_count'),'obj', d.get('analyzed_at',''))
    except Exception: pass
" \"<ORDNER>\"
```
Dann dem User die Fundliste zeigen und ihn wählen lassen (alle / Auswahl / andere).

**Wichtige Grenze — `.c4d` ist NICHT offline lesbar** (binär, braucht C4D; c4dpy
ist tabu). Ein Ordner voller `.c4d` kann NICHT direkt gescannt werden. Optionen,
die du dem User anbietest:
- Er öffnet die Szenen nacheinander in C4D; du ziehst je einen Live-Report
  (`/api/analyze`) und speicherst ihn nach `reports/<name>.json`.
- Oder er exportiert sie über den Misc-Tab (JSON) in einen Ordner, den du scannst.

Pro Projekt landet ein Report; mehrere Szenen = mehrere Dateien (`reports/A.json`,
`reports/B.json` …). Live-Export einer offenen Szene:
```bash
curl -s -X POST 127.0.0.1:8787/api/analyze -H "Content-Type: application/json" -d '{}' \
  | python -c "import sys,json;json.dump(json.load(sys.stdin)['report'],open('reports/A.json','w'),ensure_ascii=True,indent=1)"
```

**Reports sind groß (1–2 MB) — nie komplett lesen, immer per Python aggregieren.**
Jeder `nodes`-Eintrag hat: `guid, name, type, category, depth, path, casing,
language, children, points, polygons`. `guid` = stabiler Index (Traversal-Reihen-
folge) — Pläne referenzieren darüber (gültig, solange die Szene zwischen Export
und Apply unverändert bleibt).

## Schritt 2 — Konvention über alle Projekte lernen

```bash
python -c "
import json,glob,collections
cas=collections.Counter(); lang=collections.Counter(); roots=collections.Counter()
for f in glob.glob('reports/*.json'):
    d=json.load(open(f,encoding='utf-8'))
    for k,v in d['casing'].items(): cas[k]+=v
    for k,v in d['language'].items(): lang[k]+=v
    for n in d['nodes']:
        if n['depth']==0 and n['children']: roots[n['name']]+=1
print('CASING',cas.most_common(5)); print('LANG',lang.most_common()); print('ROOTS',roots.most_common(20))
"
```
- **Dominantes Casing** → producible Style wählen (PascalCase/camelCase/
  lower_snake/UPPER_SNAKE/kebab). „spaced"/„Capitalized" sind NICHT producible →
  auf den nächstliegenden producible mappen und dem User sagen.
- **Sprache** → `en`/`de`/`null`.
- **Wiederkehrende Root-Container** über Projekte = die persönliche Taxonomie →
  `groups` + `aliases`. Nur was in mehreren Projekten (oder klar bewusst)
  auftaucht, ist „so arbeitest du".

## Schritt 3 — Persönliches Preset schreiben

Datei `src/presets/so-arbeitest-du.json` (Schema wie die vorhandenen Presets):
```json
{
  "meta": {"id": "so-arbeitest-du", "name": "So arbeitest du",
           "description": "Gelernt aus <N> Projekten am <Datum>."},
  "casing": "UPPER_SNAKE", "language": "en", "number_pad": 2,
  "prefixes": {}, "translations": { "...": "..." },
  "groups": [ { "name": "...", "categories": [], "keywords": [], "aliases": [], "priority": 0 } ]
}
```
Validieren + im Plugin aktivieren:
```bash
python -c "import sys,json;sys.path.insert(0,'src');from sceneorg import config as C,graph as G;p=json.load(open('src/presets/so-arbeitest-du.json',encoding='utf-8'));cfg={k:p[k] for k in('casing','language','number_pad','prefixes','translations','groups') if k in p};cfg['graph']=G.graph_from_groups(p['groups']);C.load_config(cfg);print('preset valid')"
curl -s -X POST 127.0.0.1:8787/api/apply_preset -H "Content-Type: application/json" -d '{"id":"so-arbeitest-du"}'
```
(Server aus? Preset-Datei liegt via `deploy.ps1` im Plugin; `apply_preset`
schreibt die deployte `config.json`. Ohne Server direkt dorthin schreiben.)

## Schritt 4 — Deterministische Insights (die Regel-Engine)

NICHT raten — durch `sceneorg` laufen lassen und konkret benennen:
```bash
python -c "
import sys,json;sys.path.insert(0,'src')
from sceneorg import config as C, translate as TR, translations as T, ops
from sceneorg import model
# ... Report -> SceneTree rekonstruieren (ueber path/depth) ODER die Live-API nutzen:
"
```
Praktischer über die Live-API (Szene offen):
```bash
curl -s -X POST 127.0.0.1:8787/api/plan_translate -H "Content-Type: application/json" -d '{}'   # nicht-englische Namen
curl -s -X POST 127.0.0.1:8787/api/plan_structure -H "Content-Type: application/json" -d '{"settings":{"safe":true,"tidy":true}}'  # lose Objekte
curl -s -X POST 127.0.0.1:8787/api/plan_layers   -H "Content-Type: application/json" -d '{}'   # Layer-Verteilung
```
Daraus konkrete Verbesserungen ableiten: Default-Junk-Namen (`CUBE`, `POLYGON`,
`NULL` …), Duplikate, leere Container-Leichen, gemischtes Casing/Sprache,
flach-geklopfte Struktur (viele flache Typ-Roots + leere Alt-Container).

## Schritt 5 — Umstrukturierungs-Plan festschreiben (der KI-Kern)

Für das, was Regeln NICHT können (Räume/Etagen semantisch zuordnen), schreibst DU
(die KI) einen deterministischen Plan nach `src/plans/<name>.json`. Format:

```json
{
  "meta": {"name": "Reinstate floors", "scene": "sample_0071.c4d",
           "description": "Fenster/Türen zurück in Etagen-Container gruppieren."},
  "operations": [
    {"op": "group",  "id": "$gf", "name": "GROUND_FLOOR", "under": 42},
    {"op": "rename", "target": 108, "to": "KITCHEN_WINDOW"},
    {"op": "move",   "target": 108, "into": "$gf"},
    {"op": "layer",  "target": 250, "layer": "Lights"}
  ]
}
```
Regeln des Formats (siehe `c4d_adapter.apply_plan`):
- `op`: `group` | `rename` | `move` | `layer`. Reihenfolge zählt.
- `target`/`under`/`into` = **`guid`** (int, aus dem Export) ODER **`$id`** einer
  vorher in DIESEM Plan per `group` erzeugten Null. `under`/`into` = `null` →
  Szenen-Wurzel.
- `group` legt eine neue Null an (optional `id` zum Referenzieren, `under`).
- Weltposition bleibt bei `move` erhalten; alles läuft in EINEM Undo-Schritt.

**Leitplanken beim Plan-Bauen:**
- Semantik aus `name`/`path`/`depth` ableiten (z.B. Präfixe wie `KITCHEN_`,
  `GROUND_FLOOR_01` verraten Raum/Etage). Bei Unsicherheit: lieber weniger, dafür
  sichere Moves — und den Rest dem User zur Bestätigung auflisten.
- Bestehende, sinnvolle Verschachtelung NICHT zerstören (kein Flatten).
- guids stammen aus GENAU dem Export, den der User danach anwendet — sag ihm, die
  Szene zwischen Export und `apply_plan` nicht zu ändern.

Ausführen (Vorschau zeigen, dann anwenden):
```bash
curl -s -X POST 127.0.0.1:8787/api/apply_plan -H "Content-Type: application/json" \
  --data-binary @src/plans/reinstate-floors.json   # {"plan":{...}} ODER {"id":"reinstate-floors"}
```
Rückgabe: `{applied:{group,rename,move,layer}, errors:[...], total}`. Bei
`target missing`-Fehlern hat sich die Szene seit dem Export geändert → neu
exportieren, Plan neu bauen.

## Schritt 6 — Ehrliche Einschätzung

1. Was ist DEIN Stil (aus den Projekten gelernt) — und wo bist du inkonsistent?
2. Was erledigen die deterministischen Tools (Naming/Translate/Tidy/Layers)?
3. Welche semantische Umstrukturierung schlägst du vor — als Plan zum Ausführen,
   plus die unsicheren Fälle zur manuellen Entscheidung.

## Nicht vergessen
- Reports nie komplett in den Kontext lesen — per Python aggregieren.
- Plan-guids gelten nur für den zugehörigen Export (Szene unverändert lassen).
- Neue reine Logik → `sceneorg/` (kein `c4d`) + Test; `pytest`+`ruff` grün.
- `apply_plan`/`apply_preset` sind hot-reloaded → kein C4D-Neustart, nur
  Web-Dialog offen (Queue-Drain).
