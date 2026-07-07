# config.json — Schema + Leitplanken

Datei: **`src/config.json`** (dort liest `webapi.CONFIG_PATH`; `deploy.ps1`
ueberschreibt sie nicht). Vollstaendiges Schema: `src/sceneorg/config.py`
(DEFAULT_CONFIG).

```json
{
  "casing": "PascalCase",
  "language": "en",
  "number_pad": 2,
  "prefixes": {},
  "translations": { "zylinder": "cylinder" },
  "groups": [
    { "name": "Cameras", "categories": ["camera"], "keywords": [], "aliases": ["cams"], "priority": 100 },
    { "name": "Lights",  "categories": ["light"],  "keywords": [], "aliases": ["licht"], "priority": 100 }
  ]
}
```

## Leitplanken

- **Kategorie-Regeln (Cameras/Lights) mit `priority` 100** — ueber den c4d-Typ
  eindeutig, immer korrekt.
- **Inhaltliche Gruppen** (Furniture/Building/Exterior/Instances) ueber
  `keywords` (englisch; werden intern uebersetzt gematcht) + niedrigere Prioritaet.
- **`aliases`** = die tatsaechlichen, evtl. deutsch benannten Container des Users,
  damit `canonical_group()` sie erkennt. Fehlende aliases sind die haeufigste
  Ursache fuer faelschlich niedrige `structure_compliance`.
- **Keinen Root-Container als Alias einer Untergruppe** missbrauchen (z.B.
  `House` NICHT als Alias von `Building` — der Root enthaelt mehr).
- **Prefixe nur setzen, wenn der User sie real nutzt** — sonst leer lassen.
- **`translations`**: nur Tokens aufnehmen, die `sceneorg/translations.py` noch
  nicht kennt (analyze_report.py listet Kandidaten).

## Interpretation des Reports

- **Root-Taxonomie** (depth 0-1 Nulls mit Kindern) = mentales Modell des Users →
  wird zu `groups[].name` + `aliases`.
- **`structure_compliance` ist hierarchie-bewusst**: `enclosing_group()` =
  naechstgelegener erkannter Gruppen-Vorfahre. Licht in
  `Scene > Lights > Interior` gilt als korrekt.
- **Struktur-Modell ist EINE Ebene (flach)** — kann Raum-Verschachtelung nicht
  ausdruecken. Durchdachte Raum-Hierarchien NIE aggressiv umgruppieren.
  Siehe Memory [[scene-structure-flat-model]].
- **Default-C4D-Namen** (`Cube`, `Zylinder`, `Null`, `Boole`) tragen keine
  Bedeutung — Casing/Uebersetzung macht sie nicht sinnvoll; ehrlich benennen.

## Die vier Plugin-Aktionen — was wann empfehlen

- **Structure (Tidy-Modus, Default AN)** — sammelt nur *lose* Objekte ein; was
  schon in einem Container steckt, bleibt unberuehrt. Sicher. Tidy AUS = flach
  klopfen → nur bei strukturlosen Szenen. `plan_structure`/`apply_structure`,
  `settings.tidy` (bool).
- **Layers** — taggt Lights/Cameras/Proxies als farbige C4D-Layer, ohne die
  Hierarchie zu aendern. Typ-Achse = Layer, Raum-Achse = Nulls — nie vermischen.
  `plan_layers`/`apply_layers`; Schema `ops.DEFAULT_LAYER_SCHEME`.
- **Translate** — erkennt nicht-englische Namen, casing-erhaltende Uebersetzung
  (nur Woerter tauschen). User hakt einzeln ab. `plan_translate` (liefert `diff`
  mit `words`), `apply_translate` (`{guids:[...]}`). Logik: `sceneorg/translate.py`.
- **Naming** — volle Konvention (Casing + DE→EN + Nummerierung). ACHTUNG:
  PascalCase frisst fuehrende Etagen-Indizes (`0.`, `-1.`) → selektiv anwenden,
  nicht szenenweit.

Regeln bearbeiten: Node-Editor (Rules-Tab) speichert `groups`+`graph` via
`POST /api/config` in dieselbe config.json. Live-Hot-Reload:
`POST /api/config {"save":true,"data":{...}}`; ist der Server aus, direkt die
deployte Datei schreiben (`…\plugins\SceneOrganizer\config.json`).
