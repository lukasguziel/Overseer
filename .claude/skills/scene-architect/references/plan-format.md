# Umstrukturierungs-Plan — Format & Leitplanken

Der Plan ist der **KI-Kern des Skills**: die semantische Arbeit (Raeume/Etagen
zuordnen), die Regeln nicht koennen, eingefroren in eine deterministische
JSON-Datei. Ausgefuehrt von `c4d_adapter.apply_plan` via `POST /api/apply_plan`
— **ein einziger Undo-Schritt**, keine Live-KI.

Ablage: `src/plans/<name>.json` → `deploy.ps1` kopiert nach `plans/` im
Plugin (dortiger Ordner wird nie geleert). Validieren mit
`scripts/validate_plan.py` BEVOR der User anwendet.

## Format

```json
{
  "meta": {"name": "Reinstate floors", "scene": "sample_0071.c4d",
           "description": "Fenster/Tueren zurueck in Etagen-Container."},
  "operations": [
    {"op": "group",  "id": "$gf", "name": "GROUND_FLOOR", "under": 42},
    {"op": "rename", "target": 108, "to": "KITCHEN_WINDOW"},
    {"op": "move",   "target": 108, "into": "$gf"},
    {"op": "layer",  "target": 250, "layer": "Lights"}
  ]
}
```

## Operations-Semantik (verifiziert gegen c4d_adapter.apply_plan)

- Reihenfolge zaehlt; jede Op wird einzeln try/except-gekapselt — ein Fehler
  bricht den Plan NICHT ab, er landet in `errors[]`.
- `target`/`under`/`into`: **`guid` (int, aus GENAU dem Export)** ODER **`$id`
  (str)** einer FRUEHER in diesem Plan per `group` erzeugten Null.
  `under`/`into` fehlt oder `null` → Szenen-Wurzel.
- `group`: legt eine Null an (`InsertUnderLast`), optional `id` zum spaeteren
  Referenzieren. Nicht aufgeloestes `under` → Objekt landet an der Wurzel
  (kein Fehler!).
- `rename`: `to` fehlt → Name bleibt. Fehlendes Target → `rename #i: target missing`.
- `move`: **Weltposition bleibt erhalten** (Mg wird gesichert/restauriert),
  Einfuegen als LETZTES Kind des Ziels.
- `layer`: Layer wird per Name gesucht oder angelegt (gecacht).
- Rueckgabe: `{applied: {group: n, rename: n, move: n, layer: n}, errors: [...], total}`.
- Nach `apply_plan` sind alle guids der Szene veraltet (Traversal-Reihenfolge
  hat sich geaendert) → fuer einen zweiten Plan IMMER neu exportieren.

## Leitplanken beim Plan-Bauen

1. **Semantik aus `name` + `path` + `depth`** ableiten (Praefixe wie
   `KITCHEN_`, Container wie `GROUND_FLOOR_01` verraten Raum/Etage).
2. **Unsicher → weglassen.** Lieber weniger, dafuer sichere Moves; den Rest
   dem User als Liste zur manuellen Entscheidung geben.
3. **Bestehende sinnvolle Verschachtelung nicht zerstoeren** — kein Flatten,
   keine Moves von Kindern unter Generatoren/Deformern (Cloner, Boole, Sweep):
   nur Objekte anfassen, deren Parent Root oder eine Null ist (gleiche Logik
   wie der Safety-Filter der Engine, aber im Plan bist DU dafuer zustaendig —
   apply_plan prueft das NICHT).
4. **`group`-Ops zuerst**, dann renames/moves — `$id` muss vor Verwendung
   definiert sein.
5. guids gelten nur fuer den zugehoerigen Export → dem User explizit sagen:
   Szene zwischen Export und Apply nicht aendern.
6. Vorschau geben: pro Operation eine Zeile "was passiert" (alter Pfad →
   neuer Container), bevor der User `apply_plan` ausloest.
