# Plugin-HTTP-API (Port 8787)

Voraussetzung: C4D laeuft, Command **"Scene Organizer"** wurde geklickt,
und der **Server-Dialog ist offen** (sein Timer draint die Main-Thread-Queue â€”
Dialog zu = Requests haengen). Alle Endpoints: `POST 127.0.0.1:8787/api/<op>`
mit JSON-Body; `webapi.py` wird pro Request hot-reloaded.

## Endpoints (verifiziert gegen webapi.handle)

| op | Body | Liefert |
|---|---|---|
| `analyze` | `{}` | `{report, export_path}` â€” schreibt auch `scene_report.json` ins Repo + Historie |
| `export` / `export_csv` | `{}` | wie analyze; csv zusaetzlich `scene_structure.csv` (Semikolon, utf-8-sig) |
| `history` | `{}` | Analyse-Historie (neueste zuerst) |
| `detect` | `{}` | erkanntes Schema `{style, language, number_pad, confidence, â€¦}` |
| `rules` / `config` | `{}` bzw. `{save:true, data:{â€¦}}` | aktives Regelwerk / config.json lesen+schreiben |
| `presets` | `{}` | Preset-Liste + aktives Preset |
| `apply_preset` | `{"id": "so-arbeitest-du"}` | schreibt deployte config.json (inkl. generiertem Node-Graph) |
| `plans` | `{}` | Plan-Liste aus `plans/` im Plugin-Verzeichnis |
| `apply_plan` | `{"plan":{â€¦}}` ODER `{"id":"<name>"}` | `{applied:{group,rename,move,layer}, errors:[â€¦], total}` |
| `plan_naming` / `apply_naming` | `{settings:{casing?,language?,number_pad?,selection?}}` | Rename-Diff `{guid,old,new}` |
| `plan_structure` / `apply_structure` | `{settings:{safe:true,tidy:true,selection?}}` | Reparent-Diff + `skipped` |
| `plan_translate` | `{}` | nicht-englische Namen `{guid,old,new,words}` |
| `apply_translate` | `{"guids":[â€¦]}` | wendet NUR die akzeptierten guids an |
| `plan_layers` / `apply_layers` | `{}` | Layer-Zuordnung + `by_layer`-Counter |
| `assign_layer` | `{"guids":[â€¦],"layer":"Deko"}` | gewÃ¤hlte Objekte auf benannten Layer (wird angelegt) |
| `move_to_group` | `{"guids":[â€¦],"group":"Furniture"}` | gewÃ¤hlte Objekte unter benanntes Null (wird angelegt) |
| `focus` | `{"guid": 108}` | selektiert + framt Objekt im Viewport |
| `delete_material` / `delete_unused_materials` | `{"name":â€¦}` / `{}` | Material-Aufraeumen |

## Rezepte

Live-Report in `reports/` sichern:
```bash
curl -s -X POST 127.0.0.1:8787/api/analyze -H "Content-Type: application/json" -d '{}' \
  | python -c "import sys,json;json.dump(json.load(sys.stdin)['report'],open('reports/A.json','w'),ensure_ascii=True,indent=1)"
```

Plan ausfuehren (Datei direkt posten):
```bash
curl -s -X POST 127.0.0.1:8787/api/apply_plan -H "Content-Type: application/json" \
  --data-binary @src/plans/<name>.json
```
(Die Datei ist selbst das `{meta, operations}`-Objekt â€” webapi akzeptiert sie,
weil `operations` vorhanden ist.)

## Fehlerbilder

- `target missing` in apply_plan-errors â†’ Szene hat sich seit dem Export
  geaendert â†’ neu exportieren, Plan neu bauen.
- Kein Response/Timeout â†’ Server-Dialog in C4D geschlossen (Queue wird nicht
  gedraint) oder Server nie gestartet.
- Preset/Plan "not found" â†’ Datei liegt nur im Repo, nicht im deployten
  Plugin-Verzeichnis â†’ `powershell -File .claude/skills/deploy/deploy.ps1`.
