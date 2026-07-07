---
name: scene-rules
description: >-
  Generate or refresh the Scene Organizer rule set (src/config.json) from the
  user's live Cinema 4D scene. Pulls a fresh scene_report.json from the running
  plugin's HTTP API (or reads the existing file), analyses the real naming +
  structure, writes a config.json (convention, translations, group rules), and
  recommends the right tool per scene — safe Tidy structure, layer tagging,
  or the per-object Translate flow — instead of blindly flattening. Use when the
  user says "bau/aktualisiere die Regeln", "generate the rules", "analyse meine
  Szene", "übersetze die Namen", or after they re-export a scene.
---

# Scene Organizer — Regelwerk aus der echten Szene bauen

Ziel: aus der realen C4D-Szene ein sinnvolles `src/config.json` erzeugen
(Naming-Konvention + DE→EN-Übersetzungen + Struktur-Gruppen), das der User
danach im Node-Editor feinjustiert. Der Kanal zur Szene ist `scene_report.json`.

## Schritt 1 — Frischen Report holen

Zwei Wege, in dieser Reihenfolge versuchen:

**A) Live aus dem laufenden Plugin (bevorzugt, „automatisch").**
Das Plugin serviert eine HTTP-API auf `127.0.0.1:8787`. Wenn in C4D der
Dialog **„Scene Organizer (Web)"** offen ist (nur dann wird die Main-Thread-Queue
gedraint), triggert dieser Aufruf einen frischen Export und schreibt zugleich
`scene_report.json` ins Repo-Root:

```bash
curl -s -X POST http://127.0.0.1:8787/api/export -H "Content-Type: application/json" -d "{}"
```

- Antwort enthält `{"ok":true,"report":{...},"export_path":"...scene_report.json"}`.
- Schlägt der Aufruf fehl (Connection refused / Timeout): Server läuft nicht →
  User bitten, in C4D `Shift+C` → **„Scene Organizer (Web)"** zu öffnen und
  das Fenster offen zu lassen. Dann erneut.

**B) Fallback — vorhandene Datei.**
Existiert `scene_report.json` bereits im Repo-Root, direkt damit arbeiten
(ist evtl. veraltet — Dateidatum/`file`-Feld gegenprüfen und dem User sagen).

## Schritt 2 — Report analysieren

`scene_report.json` ist ~1–2 MB. NICHT komplett lesen — mit Python auswerten:

```bash
python -c "
import json,collections,re
d=json.load(open('scene_report.json',encoding='utf-8'))
print('file',d['file'],'objs',d['object_count'],'depth',d['max_depth'],'compliance',d['structure_compliance'])
print('types',d['types']); print('categories',d['categories'])
print('casing',d['casing']); print('language',d['language'])
# reale Top-Level-Taxonomie (Root-Container)
for x in d['nodes']:
    if x['depth']<=2 and x['children']:
        print('  '*x['depth']+x['name']+' <%d>'%x['children'])
# deutsche/uebrige Tokens fuer Uebersetzungen
tok=collections.Counter()
for x in d['nodes']:
    for t in re.findall(r'[A-Za-zÄÖÜäöüß]+',x['name']):
        if len(t)>2: tok[t.lower()]+=1
print('tokens',tok.most_common(60))
"
```

Worauf achten:
- **Struktur-Taxonomie**: die Root-Container (`depth` 0–1 Nulls mit Kindern) =
  das mentale Modell des Users. Diese Namen werden zu `groups[].name` +
  `aliases` (damit bestehende Container als konform erkannt werden, statt
  massenhaft „misplaced").
- **`structure_compliance` ist jetzt hierarchie-bewusst**: `StructureStandard`
  wertet `enclosing_group()` = nächstgelegener erkannter Gruppen-Vorfahre. Ein
  Licht in `Scene > Lights > Interior` gilt als korrekt (Vorfahre `Lights`). Wenn
  eine ältere Analyse noch 0% zeigt, liegt es meist an fehlenden `aliases` — die
  realen Container-Namen der Szene als Alias/Name aufnehmen, dann stimmt's.
- **Das Struktur-Modell ist EINE Ebene (flach)** — es kann keine räumliche
  Verschachtelung ausdrücken (`Fenster → Ground Floor → Küche`). Bei Szenen mit
  durchdachter Raum-Hierarchie NIE aggressiv umgruppieren. Details:
  [[scene-structure-flat-model]].
- **Naming**: `casing`- und `language`-Verteilung. Viele Default-C4D-Namen
  (`Cube`, `Cube.1`, `Polygon`, `Zylinder`, `Null`, `Boole`) tragen keine
  Bedeutung — Casing/Übersetzung macht sie nicht sinnvoll; ehrlich benennen.
- **Deutsche Tokens** → in `translations` (de→en) aufnehmen, die der bereits
  vorhandene Wortschatz (`sceneorg/translations.py`) noch nicht kennt. Vor dem
  Hinzufügen prüfen (`from sceneorg import translations as t`).

## Schritt 3 — config.json schreiben/aktualisieren

Datei: **`src/config.json`** (dort liest `webapi.CONFIG_PATH` sie; `deploy.ps1`
überschreibt sie nicht). Schema siehe `src/sceneorg/config.py` (DEFAULT_CONFIG):

```json
{
  "casing": "PascalCase",
  "language": "en",
  "number_pad": 2,
  "prefixes": {},
  "translations": { "zylinder": "cylinder", "...": "..." },
  "groups": [
    { "name": "Cameras", "categories": ["camera"], "keywords": [], "aliases": ["cams"], "priority": 100 },
    { "name": "Lights",  "categories": ["light"],  "keywords": [], "aliases": ["licht"], "priority": 100 }
  ]
}
```

Leitplanken:
- **Kategorie-Regeln (Cameras/Lights) mit `priority` 100** — die sind über den
  c4d-Typ eindeutig und immer korrekt.
- **Inhaltliche Gruppen** (Furniture/Building/Exterior/Instances) über
  `keywords` (englisch, werden intern übersetzt gematcht) + niedrigere Priorität.
- **`aliases`** = die tatsächlichen, evtl. anders/deutsch benannten Container des
  Users, damit `canonical_group()` sie erkennt.
- **Kein Root-Container als Alias einer Untergruppe** missbrauchen (z.B. `House`
  NICHT als Alias von `Building` — der Root enthält mehr als nur das Gebäude).
- **Prefixe nur setzen, wenn der User sie real nutzt** — sonst leer lassen.

## Schritt 4 — Validieren (Pflicht, ohne C4D)

```bash
python -c "
import sys,json;sys.path.insert(0,'src')
from sceneorg import config as C, translations as T
data=json.load(open('src/config.json',encoding='utf-8'))
T.add_translations(data.get('translations',{}))
cfg=C.load_config(data)
print('OK', cfg.convention.style.value, cfg.convention.language, 'pad',cfg.convention.number_pad)
print('groups',[r.name for r in cfg.standard.rules])
for nm in ['Cams','Licht','Moebel']:  # reale Container-Namen aus der Szene einsetzen
    print(nm,'->',cfg.standard.canonical_group(nm))
"
python -m pytest -q 2>&1 | tail -3
python -m ruff check src 2>&1 | tail -2
```

Optional an einer Stichprobe echter Namen die Normalisierung prüfen
(`NamingConvention.normalize(name)`), um Datenverlust zu erkennen (z.B. führende
Etagen-Indizes „0.", „-1." fallen bei PascalCase weg → dem User sagen, dass
er Naming besser selektiv statt szenenweit anwendet).

## Schritt 5 — Das richtige Tool empfehlen (nicht alles über Regeln lösen)

Das Plugin hat vier Aktionen. Räume dem User auf, WELCHE für seine Szene passt:

- **Structure (Tidy-Modus, Default AN)** — sammelt nur *lose* Objekte in ihre
  Gruppe ein; alles, was schon in einem (auch verschachtelten) Container steckt,
  bleibt unberührt. Sicher. Aggressiv (Tidy AUS) macht flach → nur bei
  strukturlosen Szenen. Endpoints: `plan_structure`/`apply_structure`,
  `settings.tidy` (bool).
- **Layers** — taggt Lights/Cameras/Proxies als farbige C4D-**Layer**, ohne die
  Hierarchie zu ändern. DAS ist die richtige Achse für „alles vom Typ X
  togglen/rendern". Typ-Achse = Layer, Raum-Achse = Nulls — nie vermischen.
  Endpoints: `plan_layers`/`apply_layers`. Schema: `ops.DEFAULT_LAYER_SCHEME`.
- **Translate** — erkennt nicht-englische (deutsche) Namen und schlägt eine
  casing-erhaltende Übersetzung vor (nur Wörter tauschen, Struktur/Nummern
  bleiben). Der User hakt einzeln ab. Endpoints: `plan_translate` (liefert
  `diff` mit `words`), `apply_translate` (`{guids:[...]}`). Reine Logik:
  `sceneorg/translate.py`. Fehlende Wörter → in `config.json` `translations`.
- **Naming** — vollständige Konvention (Casing + DE→EN + Nummerierung). Nützlich,
  aber PascalCase kann Etagen-Indizes (`0.`, `-1.`) fressen → selektiv anwenden.

Regeln bearbeiten: Node-Editor (Rules-Tab) speichert `groups`+`graph` via
`POST /api/config` zurück in dieselbe `config.json`.

## Schritt 6 — Ehrliche Einschätzung liefern

Dem User klar sagen:
1. **Ist die Struktur schon gut?** (meist: ja, wenn eine durchdachte
   Root-Taxonomie existiert). Wenn ja: NICHT umgruppieren, nur Naming/Translate.
2. **Reale Gewinne**: Casing-Vereinheitlichung, DE→EN-Übersetzung (Translate-Tab
   für einzeln-annehmbare Renames), Layer-Tagging fürs Togglen — **und wo
   blanko-Rename schadet** (Default-Junk-Namen, Etagen-Indizes).
3. **Falls die Szene schon flachgeklopft wurde** (viele flache Typ-Roots
   `FURNITURE`/`BUILDING`/… + leere Alt-Container als Leichen): das benennen,
   Undo empfehlen oder Aufräumen der leeren Container vorschlagen.

## Live-Tools per API triggern (Web-Dialog offen)

Alle Aktionen gehen auch direkt per `curl` (JSON), nicht nur im UI — nützlich,
um dem User Vorschauen zu zeigen. Beispiele:

```bash
# Struktur-Vorschau im sicheren Tidy-Modus
curl -s -X POST 127.0.0.1:8787/api/plan_structure -H "Content-Type: application/json" \
  -d '{"settings":{"safe":true,"tidy":true,"selection":false}}'
# nicht-englische Namen erkennen
curl -s -X POST 127.0.0.1:8787/api/plan_translate -H "Content-Type: application/json" -d '{}'
# Layer-Verteilung ansehen
curl -s -X POST 127.0.0.1:8787/api/plan_layers -H "Content-Type: application/json" -d '{}'
```

`config.json` live ins laufende Plugin schreiben (Hot-Reload, kein Neustart):
`POST /api/config {"save":true,"data":{...}}`. Ist der Server aus, stattdessen
die deployte Datei direkt schreiben:
`…\plugins\SceneOrganizer\config.json`.

## Nicht vergessen
- Der Live-Export/-Trigger braucht den offenen Web-Dialog in C4D (Queue-Drain).
- `scene_report.json` niemals komplett in den Kontext lesen — immer per Python
  aggregieren.
- Neue reine Logik → `sceneorg/` (kein `c4d`-Import) + Test in `tests/`.
  `pytest` + `ruff` müssen grün bleiben (CI-Gate).
