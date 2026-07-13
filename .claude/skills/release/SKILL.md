---
name: release
description: >-
  Cut a Scene Organizer release: bump the version everywhere, run the CI
  gates locally, commit, tag v* and push — the release workflow builds the
  SceneOrganizer-<version>.zip — then write curated change notes into the
  GitHub release. Use when the user says "release", "mach ein Release",
  "neue Version bauen", "cut v1.2.0" or wants a new dist with change notes — then offer a clean
  local test that installs the released zip itself into Cinema 4D as a fresh
  user would. Also use when the user wants to test a release build locally.
---

# Release — neue Dist mit Release + Change Notes

Der eigentliche Build passiert in CI: ein `v*`-Tag-Push startet
`.github/workflows/release.yml`, das die Gates nochmal fährt, das Plugin
paketiert und `SceneOrganizer-<version>.zip` an ein GitHub-Release hängt
(mit `generate_release_notes: true` + festem Installations-Absatz als Body).
Dieser Skill macht alles drumherum: Version, Gates, Tag, kuratierte Notes.

## Ablauf

**1. Version bestimmen.**
- Nennt der User eine Version (z. B. `v1.0.0`) → nehmen.
- Sonst aus `frontend/package.json` die aktuelle lesen und einen Vorschlag
  machen (rc → final, sonst minor-Bump); den User NUR fragen, wenn der
  Sprung unklar ist (z. B. rc vs. final vs. major).
- Format prüfen: Tag ist `v<semver>[-rcN|-beta[.N]]`. PEP-440-Form für
  `pyproject.toml` ableiten: `1.0.0-rc1 → 1.0.0rc1`, `1.0.0-beta → 1.0.0b0`.

**Abkürzung — Version ist schon gebumpt:** Steht die Zielversion bereits an
allen vier Stellen (Schritt 2) und ist committet/gepusht, Schritt 2 und den
Version-Commit in Schritt 5 überspringen — es fehlen dann nur Gates, Notes,
Tag-Push und Release-Nacharbeit. (Typischer Fall: der Bump war Teil der
letzten Arbeitssession.)

**2. Version überall setzen** (alle vier Stellen, sonst driftet es):
- `frontend/package.json` → `"version": "<ohne v>"`
- `src/sceneorg/__init__.py` → `__version__ = "<ohne v>"`
- `pyproject.toml` → `version = "<PEP-440>"`
- `docs/ROADMAP.md` → „Current release:"-Zeile

**3. Gates lokal fahren** (dasselbe wie CI — ein roter Tag-Push erzeugt
KEIN Release, der Workflow bricht ab):
```bash
python -m pytest && python -m ruff check src tests
cd frontend && pnpm test && pnpm run build   # Build aktualisiert src/web/
```
Rot → fixen oder abbrechen, NICHT taggen.

**4. Change Notes schreiben.** Quelle: Commits seit dem letzten Tag —
```bash
git tag --sort=-creatordate | head -5        # letzter Release-Tag
git log <letzter-tag>..HEAD --oneline
```
Daraus kuratierte Notes (Markdown, ENGLISCH — Release-Publikum) verfassen:
- Abschnitte nur wenn nicht leer: `## New`, `## Improved`, `## Fixed`.
- Nutzersprache, pro Punkt eine Zeile, Feature-Sicht statt Commit-Prosa
  (nicht „refactor webapi cache", sondern was der Artist davon hat).
- Interne/Doku/CI-Commits weglassen; Screenshots-Refresh o. Ä. maximal
  als Sammelpunkt.
- Notes dem User kurz zeigen (im Chat), bevor sie live gehen — er will
  ggf. umformulieren.

**5. Commit, Tag, Push.**
```bash
git add <versionierte Dateien>   # nur Version-Bump + ggf. offene Arbeit, keine Scratch-Artefakte
git commit -m "v<version>"
git tag v<version>
git push && git push origin v<version>
```
Auf `main` arbeiten (Releases bauen aus dem getaggten Stand).

**6. Workflow abwarten und Notes setzen.**
```bash
gh run watch --exit-status $(gh run list --workflow=release.yml --limit 1 --json databaseId --jq '.[0].databaseId')
```
Danach die kuratierten Notes ÜBER den bestehenden Body setzen — der
Installations-Absatz aus dem Workflow muss erhalten bleiben:
```bash
gh release view v<version> --json body --jq .body   # bestehenden Body holen
gh release edit v<version> --notes "<kuratierte Notes>

<bestehender Installations-Absatz>"
```

**7. Verifizieren + melden.**
```bash
gh release view v<version> --json assets,url --jq '{url, assets: [.assets[].name]}'
```
`SceneOrganizer-v<version>.zip` muss als Asset dranhängen. Dem User die
Release-URL geben.

**8. Clean-Test anbieten (immer fragen).** Das Release ist erst dann echt
grün, wenn das gebaute Zip auch installiert startet — CI baut das Paket,
prüft aber nie, ob es als Plugin lädt. Also den User fragen:

> „Release lokal clean testen? (Zip frisch in C4D 2024 installieren)"

- **Nein** → fertig, nichts anfassen.
- **Ja** → `test-release.ps1` (in diesem Skill-Ordner) fahren. Es lädt NICHT
  den Working Tree, sondern das Release-Asset:

```powershell
gh release download v<version> --dir $env:TEMP\so-release --clobber
# Ziel = plugin_dir aus .claude/skills/deploy/deploy.config.json (User-Eintrag)
powershell -File .claude/skills/release/test-release.ps1 `
    -Zip "$env:TEMP\so-release\SceneOrganizer-v<version>.zip" `
    -Target "<plugin_dir>"
```

Regeln dabei:
- **Cinema 4D muss geschlossen sein** (geladene Dateien sind gesperrt, und
  `.pyp`/`bridge` laden nur beim Start) — das Skript bricht sonst ab.
- **Program Files braucht Elevation**: via
  `Start-Process powershell -Verb RunAs -Wait -ArgumentList ...` starten, der
  User bestätigt den UAC-Dialog. Ohne Elevation bricht das Skript ab.
- **Backup ist Pflicht, nie überspringen.** Der Zielordner wird gewipt, und
  darin liegen die echten Nutzdaten (`config.json` mit dem Rule-Set,
  `presets/`, `plans/`). Das Skript sichert den kompletten Ordner nach
  `%TEMP%\SceneOrganizer-release-test\<timestamp>\`, BEVOR es löscht, und
  bricht ab, wenn das Backup nicht schreibbar ist. Dem User den Backup-Pfad
  nennen.
- Der Test läuft **komplett frisch** (Default: kein `config.json`, keine
  `presets/`, kein `dev_repo.txt` → echtes First-Run-Verhalten eines neuen
  Users). Nur wenn der User ausdrücklich den Release-Code gegen seine echten
  Daten sehen will: `-KeepData`.
- Danach: C4D starten, `Shift+C` → **„Scene Organizer"**, Web-UI muss
  aufgehen. Läuft es nicht, ist das ein **Release-Bug** (Packaging), kein
  lokales Problem — Zip-Inhalt prüfen (`web/index.html`, `sceneorg/`,
  `vendor/` vorhanden?), fixen, neue Version.

**9. Restore — immer, nicht fragen.** Der Clean-Test ist ein Wegwerf-Zustand:
Der User sitzt danach auf einem Release-Stand OHNE seine Daten. Sobald er den
Test bestätigt hat (egal ob grün oder rot), den vorherigen Stand vollständig
zurückspielen — C4D dazu wieder schließen lassen:
```powershell
powershell -File .claude/skills/release/test-release.ps1 `
    -Target "<plugin_dir>" -Restore      # neuestes Backup zurück, elevated
```
Erst danach ist der Release-Job fertig. Der User bekommt gemeldet: Test-
Ergebnis + „dein Stand (Rule-Set, Presets, Plans) ist zurück". Läuft er
ohnehin gleich weiter am Code, ist ein normaler `deploy`-Lauf die Alternative
— aber niemals den Release-Stand einfach stehen lassen.

## Fehlerbilder
- **Workflow rot nach Tag-Push** → Ursache fixen, dann Tag neu setzen:
  `git tag -d v<x> && git push origin :refs/tags/v<x>`, Fix committen,
  neu taggen und pushen. (Es entsteht kein halbes Release — der
  Release-Step läuft zuletzt.)
- **`gh` nicht eingeloggt** → `gh auth status`; der User muss `gh auth
  login` selbst ausführen (interaktiv, ggf. via `! gh auth login`).
- **Tag existiert schon** → Version war schon released; neue Version
  wählen, niemals einen bestehenden Release-Tag verschieben.
- **Uncommitted fremde Änderungen im Tree** → den User fragen, ob sie mit
  ins Release sollen; nie stillschweigend mittaggen oder stashen.

## Nicht vergessen
- Zip ist gegen **C4D 2024** gebaut/getestet (steht so im Release-Body).
- Der Clean-Test (Schritt 8) installiert das **Release-Asset**, nicht den
  Working Tree — das ist der ganze Punkt. Niemals stattdessen `deploy.ps1`
  fahren, das würde den Dev-Stand testen.
- Danach gilt wieder die normale Deploy-Regel: wer weiterentwickelt,
  deployt mit dem `deploy`-Skill (und überschreibt den Release-Stand).
