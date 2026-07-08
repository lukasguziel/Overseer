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

**Idee:** Die KI (dieser Skill) laeuft offline ueber exportierte Szenen-Reports
— kein bezahlter API-Button im Plugin. Sie friert ihr Verstaendnis in zwei
deterministische Artefakte ein, die das Tool danach ohne KI ausfuehrt:

1. **Preset** (`src/presets/*.json`) — "so arbeitest du" → [references/preset-format.md](references/preset-format.md)
2. **Plan** (`src/plans/*.json`) — semantische Umstrukturierung → [references/plan-format.md](references/plan-format.md)

Dazwischen liefert die Regel-Engine die Insights. Was sie kann und wo die KI
uebernimmt: [references/plugin-logic.md](references/plugin-logic.md). API-Details:
[references/api.md](references/api.md). Report-Aufbau: [references/report-schema.md](references/report-schema.md).
Siehe auch [[scene-structure-flat-model]] und Skill `scene-rules`.

## Schritt 1 — Quelle interaktiv erfragen

ZUERST per AskUserQuestion klaeren, WAS analysiert wird (Custom immer moeglich):
**aktuell offene Szene** (Live-API, Web-Dialog offen) · **bestimmte
Report-Datei(en)** · **ganzer Ordner** · **Custom**.

Ordner scannen und Fundliste zeigen:
```bash
python .claude/skills/scene-architect/scripts/scan_reports.py <ORDNER>
```

**Grenze:** `.c4d` ist offline NICHT lesbar (binaer; c4dpy tabu). Bei einem
Ordner voller `.c4d`: User oeffnet die Szenen nacheinander in C4D, du ziehst je
einen Live-Report nach `reports/<name>.json` (curl-Rezept in
[references/api.md](references/api.md)) — oder er exportiert via Misc-Tab.

**Reports (1–2 MB) nie komplett lesen — immer per Skript aggregieren.**

## Schritt 2 — Konvention ueber alle Projekte lernen

```bash
python .claude/skills/scene-architect/scripts/learn_convention.py reports/*.json
```
Liefert Casing-/Sprach-Verteilung, wiederkehrende Root-Container (= persoenliche
Taxonomie), Junk-Namen und Duplikate. Nicht-producible Casing (spaced/
Capitalized) auf den naechstliegenden producible Stil mappen und dem User sagen
(Details: [references/preset-format.md](references/preset-format.md)).

## Schritt 3 — Persoenliches Preset schreiben

`src/presets/so-arbeitest-du.json` nach dem Schema in
[references/preset-format.md](references/preset-format.md) schreiben, dann:
```bash
python .claude/skills/scene-architect/scripts/validate_preset.py src/presets/so-arbeitest-du.json
powershell -File .claude/skills/deploy/deploy.ps1
curl -s -X POST 127.0.0.1:8787/api/apply_preset -H "Content-Type: application/json" -d '{"id":"so-arbeitest-du"}'
```

## Schritt 4 — Deterministische Insights (nicht raten)

Live-API bei offener Szene (Payloads: [references/api.md](references/api.md)):
`plan_translate` (nicht-englische Namen), `plan_structure` mit
`{safe:true,tidy:true}` (lose Objekte), `plan_layers` (Layer-Verteilung),
`detect` (Schema + Konfidenz). Daraus konkret benennen: Junk-Namen, Duplikate,
leere Container-Leichen, gemischtes Casing/Sprache. ACHTUNG: compliance 0.0
beim flachen Modell ist oft False Negative — Struktur nicht auto-"reparieren".

## Schritt 5 — Umstrukturierungs-Plan festschreiben (KI-Kern)

Fuer das, was Regeln nicht koennen (Raeume/Etagen semantisch zuordnen),
schreibst DU einen Plan nach `src/plans/<name>.json` — Format, Semantik und
Leitplanken in [references/plan-format.md](references/plan-format.md). Danach:
```bash
python .claude/skills/scene-architect/scripts/validate_plan.py src/plans/<name>.json scene_report.json
curl -s -X POST 127.0.0.1:8787/api/apply_plan -H "Content-Type: application/json" --data-binary @src/plans/<name>.json
```
Die Validator-Vorschau dem User VOR dem Apply zeigen. guids gelten nur fuer
genau diesen Export — Szene dazwischen nicht aendern. `target missing`-Fehler
→ neu exportieren, Plan neu bauen.

## Schritt 6 — Ehrliche Einschaetzung

1. DEIN Stil (gelernt) — und wo du inkonsistent bist.
2. Was die deterministischen Tools erledigen (Naming/Translate/Tidy/Layers).
3. Welche semantische Umstrukturierung der Plan macht — plus unsichere Faelle
   als Liste zur manuellen Entscheidung.
