---
name: deploy
description: >-
  Deploy the Scene Organizer plugin into a Cinema 4D installation. The repo
  carries no target path: the machine-local, gitignored deploy.config.json
  holds the user's choice. If it is missing (or the user names a different
  Cinema), the skill discovers all installed Cinema 4D versions and asks
  which one to use (showing each install path), writes the config, and runs
  deploy.ps1. Use when the user says "deploy", "deploye das Plugin", "deploy
  nach Cinema", "installier das Plugin", or after building the frontend.
---

# Deploy — Plugin in ein Cinema 4D deployen

Der Zielpfad steht NIE im Repo. Er lebt in **`deploy.config.json`**
(Repo-Root, **gitignored**, maschinenlokal; Vorlage
`deploy.config.example.json`) und wird pro Maschine einmal vom User gewaehlt.

## Ablauf

**1. Ziel bestimmen.**
- Nennt der User Version/Pfad explizit → Schritt 3 (und Config aktualisieren).
- Existiert `deploy.config.json` mit `plugin_dir` → verwenden, dem User das
  Ziel kurz nennen. Weiter zu Schritt 4.
- Sonst Schritt 2.

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
ausgeben, eine Zeile pro Eintrag, und den User die Nummer tippen lassen:

```
 1. Cinema 4D 2024 — prefs   ·  …\Maxon Cinema 4D 2024_A5DBFF93\plugins\SceneOrganizer   (kein Admin)
 2. Cinema 4D 2024 — app     ·  C:\Program Files\Maxon Cinema 4D 2024\plugins\SceneOrganizer   (Admin)
 …
```
- Reihenfolge: pro Version zuerst `prefs` (kein Admin), dann `app` (Admin);
  Versionen absteigend (neueste zuerst).
- Aktuelles Ziel aus `deploy.config.json` (falls vorhanden) mit `← aktuell`
  markieren.
- Kurz drueberschreiben: „Welche Nummer?" — dann die getippte Zahl aufloesen.
  Keine Empfehlung aufdraengen, die Wahl ist offen.

**3. Wahl in `deploy.config.json` schreiben** (Repo-Root, gitignored):
```json
{ "cinema": "<name>", "location": "prefs|app", "plugin_dir": "<voller Pfad>" }
```

**4. Deployen.**
```bash
powershell -File deploy.ps1
```
Bei `app`-Ziel (Program Files) ohne Admin-Shell:
```powershell
Start-Process powershell -Verb RunAs -Wait -ArgumentList "-NoProfile","-File","<repo>\deploy.ps1","-Target","<plugin_dir>"
```
(UAC-Prompt beim User ankuendigen.) Danach Erfolg pruefen:
`Test-Path "<plugin_dir>\scene_organizer.pyp"`.

**5. Fehlerbilder.**
- `Cannot write` → Elevation fehlt (s.o.) oder Pfad falsch.
- `FAIL: web/` bei laufendem C4D → Web-Dialog in C4D schliessen (lockt
  Dateien), erneut deployen.
- `WARN: no web/ bundle` → erst `cd frontend && npm run build`.

## Nicht vergessen
- Frontend-Aenderungen brauchen VOR dem Deploy `npm run build` (Output `src/web/`).
- `bridge.py`/`.pyp`-Aenderungen wirken erst nach C4D-Neustart; reine
  `sceneorg`-Logik hot-reloadet beim naechsten Command-Klick.
- Die deployte `config.json` wird nie ueberschrieben, nur geseedet, wenn sie fehlt.
- Das Plugin ist gegen C4D **2024** entwickelt — Deploy in andere Versionen
  ist ungetestet, kurz dazusagen.
