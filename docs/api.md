# Plugin HTTP API (port 8787)

Prerequisite: C4D is running, the **"Overseer"** command was clicked,
and the **server dialog is open** (its timer drains the main-thread queue —
dialog closed = requests hang). All endpoints: `POST 127.0.0.1:8787/api/<op>`
with a JSON body; `webapi.py` is hot-reloaded per request.

## Endpoints (verified against webapi.handle)

| op | Body | Returns |
|---|---|---|
| `analyze` | `{}` | `{report, export_path}` — also writes `var/scene_report.json` into the repo + history |
| `export` / `export_csv` | `{}` | like analyze; csv additionally `scene_structure.csv` (semicolon, utf-8-sig) |
| `history` | `{}` | analysis history (newest first) |
| `detect` | `{}` | detected scheme `{style, language, number_pad, confidence, …}` |
| `config` | `{}` resp. `{save:true, data:{…}}` | read+write config.json |
| `plan_naming` / `apply_naming` | `{settings:{casing?,language?,number_pad?,selection?}}` | rename diff `{guid,old,new}` |
| `plan_translate` | `{}` | non-English names `{guid,old,new,words}` |
| `apply_translate` | `{"guids":[…]}` | applies ONLY the accepted guids |
| `plan_layers` / `apply_layers` | `{}` | layer assignment + `by_layer` counter |
| `assign_layer` | `{"guids":[…],"layer":"Decor"}` | selected objects onto the named layer (created if missing) |
| `set_layer_colors` | `{"colors":[{"name":"Decor","color":[r,g,b]}]}` | set layer colors (0..1 floats, one undo step) |
| `move_to_group` | `{"guids":[…],"group":"Furniture"}` | selected objects under a named Null (created if missing) |
| `focus` | `{"guid": 108}` | selects + frames the object in the viewport |
| `delete_material` / `delete_unused_materials` | `{"name":…}` / `{}` | material cleanup |
| `update_check` | `{}` resp. `{force:true}` | `{current, latest, update_available, writable, releases:[{version,name,notes,date,…}], state, host, repo}` — GitHub releases newer than the installed version, notes included; cached 6 h unless forced |
| `update_install` | `{version?}` | downloads + installs that release (default: latest), swaps the plugin folder with a backup, returns `{installed, backup, restart_required}` — restart the host to finish |
| `update_ack` | `{}` | clears a finished/rolled-back update state (dismisses the banner notice) |

## Recipes

Save a live report into `reports/`:
```bash
curl -s -X POST 127.0.0.1:8787/api/analyze -H "Content-Type: application/json" -d '{}' \
  | python -c "import sys,json;json.dump(json.load(sys.stdin)['report'],open('reports/A.json','w'),ensure_ascii=True,indent=1)"
```

## Failure modes

- No response/timeout → server dialog closed in C4D (queue is not being
  drained) or the server was never started.
