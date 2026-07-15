---
name: deploy
description: >-
  Deploy the Overseer plugin into one or more Cinema 4D installations.
  The repo carries no target path: the machine-local, gitignored
  deploy.config.json holds each WINDOWS USER's target list (schema 2, keyed by
  $env:USERNAME — different users on the same machine can point at different
  Cinemas, and one user can deploy to several Cinemas at once). If the current
  user has no entry (or names a different Cinema), the skill discovers all
  installed Cinema 4D versions and asks which one(s) to use (showing each
  install path), writes the config, and runs the skill's deploy.ps1. Use when
  the user says "deploy", "deploye das Plugin", "deploy nach Cinema",
  "installier das Plugin", or after building the frontend.
---

# Deploy — Plugin in ein oder mehrere Cinema 4D deployen

Alle Deploy-Dateien leben in DIESEM Skill-Ordner (`.claude/skills/deploy/`):
`deploy.ps1` (das Script), `deploy.config.json` (**gitignored**,
maschinenlokal — der Zielpfad steht NIE im Repo; Vorlage
`deploy.config.example.json`).

**Config-Schema 2 — pro Windows-User:** Ziele haengen am Windows-Usernamen
(`$env:USERNAME`), damit auf derselben Maschine jeder User sein eigenes
Cinema waehlen kann. Pro User eine **Liste** `targets` — alle Eintraege
werden in EINEM Lauf deployt (Multi-Cinema-Deploy):

```json
{
  "schema": 2,
  "users": {
    "lukas": {
      "targets": [
        { "cinema": "<name>", "location": "prefs|app", "plugin_dir": "<voller Pfad>" }
      ]
    }
  }
}
```

Alte flache Configs (`{cinema, location, plugin_dir}`) migriert `deploy.ps1`
beim ersten Lauf automatisch auf Schema 2 (als Ziel des aktuellen Users).

## Ablauf

**1. Ziel(e) bestimmen.**
- Nennt der User Version/Pfad explizit → Schritt 3 (und Config aktualisieren).
- Hat `.claude/skills/deploy/deploy.config.json` unter `users.<$env:USERNAME>.targets`
  Eintraege → verwenden, dem User die Ziele kurz nennen. Weiter zu Schritt 4.
- Sonst Schritt 2. (Eintraege ANDERER Windows-User nie anfassen.)

**2. Installierte Cinemas finden und auswaehlen lassen.**
```bash
powershell -File .claude/skills/deploy/scripts/list_cinemas.ps1
```
Liefert JSON `[{name, location, plugin_dir, needs_admin}]` — pro Installation
das Program-Files-Ziel (`app`, braucht Admin) und den User-Prefs-Ordner
(`prefs`, kein Admin).

**ALLE** Eintraege auflisten, nichts kuerzen — der User will die komplette
Liste sehen und daraus waehlen. NICHT `AskUserQuestion` benutzen (das cappt
hart bei 4 Optionen). Stattdessen eine schlanke, nummerierte Markdown-Liste
ausgeben, eine Zeile pro Eintrag, und den User waehlen lassen — **eine Nummer
oder mehrere** (z. B. `1,3` oder `1 und 3`), Mehrfachauswahl = Deploy auf
mehrere Cinemas gleichzeitig:

```
 1. Cinema 4D 2024 — prefs   ·  …\Maxon Cinema 4D 2024_A5DBFF93\plugins\Overseer   (kein Admin)
 2. Cinema 4D 2024 — app     ·  C:\Program Files\Maxon Cinema 4D 2024\plugins\Overseer   (Admin)
 …
```
- Reihenfolge: pro Version zuerst `prefs` (kein Admin), dann `app` (Admin);
  Versionen absteigend (neueste zuerst).
- Aktuelle Ziele des Users aus `deploy.config.json` (falls vorhanden) mit
  `← aktuell` markieren.
- Kurz drueberschreiben: „Welche Nummer(n)?" — dann die getippten Zahlen
  aufloesen. Keine Empfehlung aufdraengen, die Wahl ist offen.

**3. Wahl in `.claude/skills/deploy/deploy.config.json` schreiben** (gitignored,
Schema 2, s. oben): unter `users.<$env:USERNAME>.targets` die gewaehlten
Eintraege setzen (ersetzt die bisherige Liste dieses Users; andere User
unveraendert lassen).

**4. Deployen.**
```bash
powershell -File .claude/skills/deploy/deploy.ps1
```
Deployt alle `targets` des aktuellen Windows-Users nacheinander (oder explizit:
`-Target <dir1>,<dir2>`). Enthaelt die Liste `app`-Ziele (Program Files) und
die Shell ist nicht elevated: NUR die `app`-Ziele in einem elevated,
versteckten Fenster deployen (Output des elevated Fensters ist unsichtbar —
deshalb in ein Log umleiten und das danach ausgeben; `-WindowStyle Hidden`
verhindert das kurz aufblitzende leere Fenster):
```powershell
$log = "$env:TEMP\so_deploy.log"
Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList "-NoProfile","-Command","& '<repo>\.claude\skills\deploy\deploy.ps1' -Target '<app plugin_dir 1>','<app plugin_dir 2>' *> '$log'"
Get-Content $log
```
(UAC-Prompt beim User ankuendigen.) `prefs`-Ziele danach normal ohne Elevation
deployen (`-Target` mit den prefs-Pfaden). Danach Erfolg PRO ZIEL pruefen:
`Test-Path "<plugin_dir>\overseer.pyp"` und bei Frontend-Aenderungen
die Asset-Hashes in `<plugin_dir>\web\index.html` gegen `src/web/index.html`
vergleichen.

**5. Fehlerbilder.**
- `Cannot write` → Elevation fehlt (s.o.) oder Pfad falsch.
- `FAIL: web/` bei laufendem C4D → Web-Dialog in C4D schliessen (lockt
  Dateien), erneut deployen.
- `WARN: no web/ bundle` → erst `cd frontend && npm run build`.
- `no targets for Windows user '<name>'` → dieser Windows-User hat noch keine
  Ziele gewaehlt → Schritt 2.
- Ein Ziel schlaegt fehl, andere ok → Script deployt alle weiter, meldet
  „DEPLOY INCOMPLETE" pro Ziel und exit 1 am Ende.

## Nicht vergessen
- Frontend-Aenderungen brauchen VOR dem Deploy `npm run build` (Output `src/web/`).
- `bridge.py`/`.pyp`-Aenderungen wirken erst nach C4D-Neustart; reine
  `overseer`-Logik hot-reloadet beim naechsten Command-Klick.
- Die deployte `config.json` wird nie ueberschrieben, nur geseedet, wenn sie fehlt.
- Das Plugin ist gegen C4D **2024** entwickelt — Deploy in andere Versionen
  ist ungetestet, kurz dazusagen.
