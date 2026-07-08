---
name: scene-conventions
description: >-
  Learn a C4D artist's personal naming & structure conventions from one or
  more real projects — including per-category affix habits like "ABC_ before
  every spline" — then confirm them in a short interview and freeze them into
  a validated Scene Organizer preset (schema 2) plus rules the plugin enforces
  deterministically. Use when the user says "lern wie ich arbeite", "analysiere
  mein(e) Projekt(e)", "bau ein Preset aus meinen Szenen", "versteh meine
  Naming-Regeln", or wants their convention captured as rules.
---

# Scene Conventions — persönliche Konventionen lernen & einfrieren

**Ziel:** Aus echten Projekten die *tatsächliche* Arbeitsweise des Artists
extrahieren (nicht eine Ideal-Konvention aufdrängen), sie mit Belegen und
Gegenbeispielen bestätigen lassen und als Preset v2 + RuleV2-Regeln
einfrieren. Alles KI-Denken passiert HIER, offline — das Plugin führt später
nur deterministische Regeln aus.

Kanal zur Szene: `scene_report.json` (Export des Plugins).
API-Endpoints/Rezepte: [references/api.md](references/api.md).
Interview-Fragenkatalog: [references/interview-guide.md](references/interview-guide.md).
Abnahme-Checkliste: [references/review-checklist.md](references/review-checklist.md).

## Grundsätze (nicht verhandelbar)

1. **Evidenz vor Meinung.** Jede vorgeschlagene Regel braucht Zahlen:
   Coverage (wie viele Mitglieder der Achse tragen das Muster) und Precision
   (wie viele Träger sitzen in der Achse) plus konkrete Gegenbeispiele.
2. **Reports nie roh in den Kontext lesen** — immer über die Skripte
   aggregieren (Reports sind 1–2 MB).
3. **Struktur nicht ungefragt reparieren.** Compliance 0.0 ist bei flachen
   Szenen oft ein False Negative; existierende Root-Taxonomie = die Struktur
   IST die Konvention.
4. **Die Szene hat recht.** Wenn 88 % der Splines `ABC_` tragen, ist `ABC_`
   die Regel und die 12 % sind die Todos — nicht umgekehrt.

## Schritt 1 — Reports besorgen

**Live** (Web-Dialog in C4D offen):
```bash
curl -s -X POST 127.0.0.1:8787/api/export -H "Content-Type: application/json" -d "{}"
```
**Mehrere Projekte** (je Projekt einmal exportieren, dann einsammeln):
```bash
python .claude/skills/scene-conventions/scripts/scan_reports.py <ordner> [...]
```
Mehr Projekte = stärkere Evidenz. Ein Muster, das in 3 Szenen auftaucht, ist
eine Konvention; eines in 1 Szene vielleicht nur ein Projekt-Tick — im
Interview kennzeichnen.

## Schritt 2 — Deterministisch minen

```bash
python .claude/skills/scene-conventions/scripts/analyze_report.py <report>
python .claude/skills/scene-conventions/scripts/learn_convention.py <report> [<report2> ...]
```

`learn_convention.py` ist das Herzstück. So liest du seine Sektionen:

| Sektion | Signal | Wird zu |
|---|---|---|
| CASING (+ BY CATEGORY) | dominanter Stil; Abweichler pro Kategorie (z. B. Lights UPPER) | `casing` im Preset; Kategorie-Abweichung → im Interview klären |
| ROOTS | wiederkehrende Top-Container = persönliche Taxonomie | `structure`-Baum + `aliases` |
| JUNK / DUPES | Default-Namen, Mehrfachnamen | Rename-Todos, `condition`-Regel (duplicates_gt) |
| NUMBERING | Padding-Breite, Startindex, Lücken, per-parent vs. global | `number_pad`, `renumber`-Regel |
| **AFFIXES** | Präfixe UND Suffixe (jede Schreibung: `ABC_`, `spl-`, `Geo.`), korreliert mit 4 Achsen: category / type / parent / root | `prefix`-Regeln mit passendem Match |
| SEMANTIC CLUSTERS | Token-Häufungen pro Container | `structure`-Keywords |
| SUGGESTED RULES | fertige RuleV2-Kandidaten inkl. `_evidence` | Preset (nach Interview, `_evidence` entfernen) |

**Die AFFIXES-Sektion ist der Kern für persönliche Regeln.** Beispielausgabe:

```
prefix ABC_  x8  category='spline'  coverage 7/8 (88%)  precision 88%
       would rename 1 member(s) without it, e.g. ['Deko_Kurve']
       carried OUTSIDE the axis by 1, e.g. ['ABC_Sonderfall']
```

Lesart: „Der Artist setzt `ABC_` vor (fast) jeden Spline." Die Regel dazu:
```json
{"type": "prefix", "prefix": "ABC_", "match": {"categories": ["spline"]}}
```
- **coverage < 100 %** → die fehlenden Mitglieder sind genau das, was die
  Regel umbenennen würde. Liste sie im Interview auf.
- **intruders > 0** → Träger außerhalb der Achse. Wenige = Ausnahme (Regel
  trotzdem per category matchen, PrefixRule fasst bestehende Träger nie an).
  Viele = falsche Achse; prüfe, ob `type`, `parent` oder `root` besser passt
  (das Skript wählt bereits die Achse mit dem besten coverage×precision).
- **„no dominant axis (scattered)"** → wahrscheinlich keine Konvention;
  nicht vorschlagen, höchstens als Beobachtung erwähnen.

## Schritt 3 — Interview (Belege zeigen, nicht raten)

Fragenkatalog mit Formulierungen:
[references/interview-guide.md](references/interview-guide.md).
Kernprinzip: **jede Frage zeigt die Evidenz und die konkreten Namen**, z. B.

> „7 von 8 Splines tragen `ABC_`. Soll `Deko_Kurve` den Präfix bekommen?
> Und `ABC_Sonderfall` ist ein Mesh mit dem Präfix — Ausnahme oder Fehler?"

Antworten protokollieren; nur Bestätigtes wird Regel. Unbestätigtes → als
Kommentar in `meta.description` des Presets dokumentieren.

## Schritt 4 — Preset schreiben, validieren, trocken testen (Pflicht)

Preset v2 nach `src/presets/<id>.json` (Snapshot: casing/language/number_pad/
translations/structure/rules; `_evidence`-Felder entfernen). Dann IMMER:

```bash
python .claude/skills/scene-conventions/scripts/validate_preset.py src/presets/<id>.json
python .claude/skills/scene-conventions/scripts/dry_run.py src/presets/<id>.json <report> [...]
python -m pytest -q 2>&1 | tail -3
```

Den Dry-Run-Output GEGEN die Erwartung lesen, Zeile für Zeile:

- Renames, die eine erkannte Konvention **zerstören** (klassiker: globales
  Casing schreibt `Chair01_GEO → Chair01Geo` und killt die Suffix-Gewohnheit)
  → `apply_casing` aus, `keep_separators` an, oder Naming nur selektiv
  empfehlen. Suffix-Konventionen kann die Engine nicht erzwingen (steht unter
  `unsupported`) — sie darf sie aber auch nicht kaputt machen.
- Führende Etagen-Indizes (`0.`, `-1.`) dürfen nicht verschwinden.
- `rules applied` muss die bestätigten Regel-IDs enthalten; Warnings = null.

Iterieren bis der Dry-Run exakt das tut, was im Interview vereinbart wurde.
Abschließend gegen [references/review-checklist.md](references/review-checklist.md) prüfen.

## Schritt 5 — Übergabe

1. Preset deployen (liegt in `src/presets/`, `deploy.ps1` kopiert es mit).
2. User wendet es im Web-UI an (Misc → Presets → Apply) oder per API
   `apply_preset`; Vorschau über `plan_all` — nie blind anwenden.
3. Ehrlich zusammenfassen: was die Regeln tun, was bewusst NICHT
   automatisiert wurde (Suffixe, Ausnahmen) und warum.

## Fehlerbilder

- `Connection refused` beim Export → Web-Dialog in C4D öffnen (`Shift+C` →
  „Scene Organizer"), Server-Fenster offen lassen.
- `(sceneorg not importable)` im Miner → vom Repo-Root ausführen.
- Miner findet nichts unter AFFIXES → Szene hat schlicht keine Affix-Gewohnheit;
  nicht erfinden. Casing/Numbering/Structure tragen das Preset auch allein.
