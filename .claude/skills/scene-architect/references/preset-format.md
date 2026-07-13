# Preset — Format & Aktivierung

Ein Preset ist das eingefrorene "so arbeitest du": Konvention + Uebersetzungen
+ Gruppen-Taxonomie. Ablage `src/presets/<id>.json`; `deploy.ps1` spiegelt den
Ordner ins Plugin. `POST /api/apply_preset {"id": …}` schreibt daraus die
deployte `config.json` (inkl. generiertem Node-Editor-Graph via
`graph_from_groups`) — das Preset erscheint sofort im Rules-Tab.

## Schema

```json
{
  "meta": {"id": "so-arbeitest-du", "name": "So arbeitest du",
           "description": "Gelernt aus <N> Projekten am <Datum>. <Besonderheiten!>"},
  "casing": "PascalCase",
  "language": "en",
  "number_pad": 2,
  "prefixes": {},
  "translations": {"tuer": "door", "tür": "door"},
  "groups": [
    {"name": "Lights", "categories": ["light"], "keywords": [],
     "aliases": ["lichter", "beleuchtung"], "priority": 100}
  ]
}
```

## Feld-Regeln

- `casing`: nur producible Werte — `PascalCase`, `camelCase`, `lower_snake`,
  `UPPER_SNAKE`, `kebab`. Erkannte Stile wie `spaced`/`Capitalized`/`mixed`
  sind NICHT producible → auf den naechstliegenden mappen und die Abweichung
  in `meta.description` dokumentieren (siehe vorhandenes `so-arbeitest-du`:
  Title-Case-Realitaet → PascalCase + Warnung "Naming nicht szenenweit anwenden").
- `language`: `"en"`, `"de"` oder `null` (= nicht uebersetzen).
- `translations`: de→en, **Umlaut- UND ae/oe/ue-Schreibweise beide eintragen**
  (`"tuer"` und `"tür"`), Keys lowercase.
- `groups`: Match ueber `categories` (light/camera/null/mesh/spline/other)
  ODER `keywords` (englisch — Namen werden vor dem Match uebersetzt).
  `aliases` erkennen bestehende, anders benannte Container ("Möbel" ==
  "Furniture"). Hoehere `priority` gewinnt.
- Nur Taxonomie aufnehmen, die in MEHREREN Projekten (oder klar bewusst)
  auftaucht — Einzelfaelle sind kein Stil.

## Validieren & Aktivieren

```bash
python .claude/skills/scene-architect/scripts/validate_preset.py src/presets/<id>.json
curl -s -X POST 127.0.0.1:8787/api/apply_preset -H "Content-Type: application/json" -d '{"id":"<id>"}'
```
Server aus? `apply_preset` schreibt nur die deployte config.json — ohne Server
den config-Inhalt direkt nach
`…\plugins\Overseer\config.json` schreiben (Format: die cfg-Keys plus
`"graph"` aus `graph_from_groups` und `"preset": "<id>"`).

Vorher immer `deploy.ps1` laufen lassen, sonst kennt das Plugin die neue
Preset-Datei nicht.
