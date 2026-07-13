---
name: scene-rules
description: >-
  Generate or refresh the Overseer rule set (src/config.json) from the
  user's live Cinema 4D scene. Pulls a fresh scene_report.json from the running
  plugin's HTTP API (or reads the existing file), analyses the real naming +
  structure, writes a config.json (convention, translations, group rules), and
  recommends the right tool per scene — safe Tidy structure, layer tagging,
  or the per-object Translate flow — instead of blindly flattening. Use when the
  user says "bau/aktualisiere die Regeln", "generate the rules", "analyse meine
  Szene", "übersetze die Namen", or after they re-export a scene.
---

# Scene Rules — Regelwerk aus der echten Szene bauen

**Ziel:** aus der realen C4D-Szene ein `src/config.json` erzeugen (Konvention +
DE→EN-Uebersetzungen + Gruppen-Regeln), das der User im Node-Editor feinjustiert.
Kanal zur Szene: `scene_report.json`.

Schema, Leitplanken und Tool-Guide: [references/config-format.md](references/config-format.md).
API-Endpoints/Rezepte/Fehlerbilder: [../scene-architect/references/api.md](../scene-architect/references/api.md).
Report-Aufbau: [../scene-architect/references/report-schema.md](../scene-architect/references/report-schema.md).

## Schritt 1 — Frischen Report holen

**A) Live (bevorzugt).** Web-Dialog in C4D muss offen sein (Queue-Drain):
```bash
curl -s -X POST 127.0.0.1:8787/api/export -H "Content-Type: application/json" -d "{}"
```
Schreibt `scene_report.json` ins Repo-Root. Connection refused → User bittet
`Shift+C` → **"Overseer"** oeffnen, Server-Fenster offen lassen.

**B) Fallback:** vorhandene `scene_report.json` nutzen — Dateidatum/`file`-Feld
gegenpruefen und dem User sagen, wenn veraltet.

## Schritt 2 — Report analysieren (nie komplett lesen)

```bash
python .claude/skills/scene-rules/scripts/analyze_report.py
```
Liefert Kennzahlen, Root-Taxonomie (= `groups` + `aliases`-Kandidaten),
Token-Frequenzen und unbekannte deutsche Tokens (= `translations`-Kandidaten).
Interpretation (flaches Struktur-Modell, compliance-Fallen, Junk-Namen):
[references/config-format.md](references/config-format.md).

## Schritt 3 — config.json schreiben + validieren (Pflicht)

`src/config.json` nach dem Schema in
[references/config-format.md](references/config-format.md) schreiben, dann:
```bash
python .claude/skills/scene-rules/scripts/validate_config.py src/config.json Cams Licht Moebel
python -m pytest -q 2>&1 | tail -3
python -m ruff check src 2>&1 | tail -2
```
(Als Argumente die realen Container-Namen der Szene — testet die
Alias-Erkennung.) Optional Stichprobe `NamingConvention.normalize(name)` auf
echte Namen: gehen fuehrende Etagen-Indizes ("0.", "-1.") verloren → Naming
selektiv statt szenenweit empfehlen.

## Schritt 4 — Das richtige Tool empfehlen

Vier Aktionen: **Structure (Tidy)** fuer lose Objekte, **Layers** fuer die
Typ-Achse, **Translate** fuer einzeln abhakbare Uebersetzungen, **Naming** fuer
die volle Konvention (selektiv!). Entscheidungshilfe + Endpoints:
[references/config-format.md](references/config-format.md). Vorschauen dem User
per `plan_*`-Endpoints zeigen (curl-Rezepte in
[../scene-architect/references/api.md](../scene-architect/references/api.md)).

## Schritt 5 — Ehrliche Einschaetzung

1. **Struktur schon gut?** (meist ja, wenn Root-Taxonomie existiert) → NICHT
   umgruppieren, nur Naming/Translate.
2. **Reale Gewinne** benennen — und wo Blanko-Rename schadet (Junk-Namen,
   Etagen-Indizes).
3. **Schon flachgeklopfte Szene** (flache Typ-Roots + leere Alt-Container):
   benennen, Undo oder Aufraeumen vorschlagen.

## Nicht vergessen

- Live-Export braucht den offenen Web-Dialog (Queue-Drain).
- `scene_report.json` nie komplett in den Kontext lesen — immer per Skript.
- Neue reine Logik → `sceneorg/` (kein `c4d`-Import) + Test; pytest + ruff
  muessen gruen bleiben (CI-Gate).
