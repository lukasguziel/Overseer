---
name: release
description: >-
  Cut an Overseer release: bump the version everywhere, run the CI
  gates locally, commit on dev and merge to main — every main push rebuilds
  the Overseer-<version>.zip and replaces the release of the stamped version
  (the tag moves along) — then write curated change notes into the
  GitHub release. Use when the user says "release", "mach ein Release",
  "neue Version bauen", "cut v1.2.0" or wants a new dist with change notes — then offer a clean
  local test that installs the released zip itself into Cinema 4D as a fresh
  user would. Also use when the user wants to test a release build locally.
---

# Release — neue Dist mit Release + Change Notes

**Branch-Modell: `main` IST der Release-Branch.** Gearbeitet wird auf `dev`;
JEDER Push auf `main` lässt `.github/workflows/release.yml` die Gates fahren,
das Zip bauen und das Release der im Repo gestempelten Version ERSETZEN (der
`v*`-Tag wandert mit, der Mirror aktualisiert das öffentliche Repo). Neue
Version = Version bumpen + nach `main` mergen — mehr nicht. Der Body bleibt
beim Refresh unangetastet (kuratierte Notes überleben); BEWUSST ohne GitHubs
`generate_release_notes` — dessen „Full Changelog"-Link würde das interne
Dev-Repo in den öffentlichen Mirror leaken.
Dieser Skill macht alles drumherum: Version, Gates, Merge, kuratierte Notes.

## Ablauf

**0. Docs frisch?** Hat sich seit dem letzten Release die UI geändert (neuer
Tab, geänderte Texte/Screens), ZUERST das `readme`-Skill laufen lassen
(frische Screenshots + README) — der Docs-Mirror ins öffentliche Repo hängt
am `main`-Push und nimmt sie dann automatisch mit.

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
- `src/overseer/__init__.py` → `__version__ = "<ohne v>"`
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
- **NIE das Dev-Repo referenzieren** (`Goodsoup-Family-Crypt/…`): keine
  Compare-/Commit-/Issue-Links, kein „Full Changelog". Die Notes landen 1:1
  im öffentlichen Mirror — jeder Link zeigt dort ins Leere bzw. leakt den
  internen Repo-Namen.
- Notes dem User kurz zeigen (im Chat), bevor sie live gehen — er will
  ggf. umformulieren.

**5. Commit auf `dev`, merge nach `main`, push.** KEIN manuelles Tag — der
Workflow setzt/verschiebt `v<version>` selbst auf den released Commit:
```bash
git add <versionierte Dateien>   # nur Version-Bump + ggf. offene Arbeit, keine Scratch-Artefakte
git commit -m "v<version>"
git push origin dev
git checkout main && git merge dev && git push origin main
git checkout dev
```
(Der `main`-Push triggert Release-Build + Mirror. Gleiche Version wie das
bestehende Release → Asset wird ersetzt; neue Version → neues Release.)

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
`Overseer-v<version>.zip` muss als Asset dranhängen. Dem User die
Release-URL geben.

**8. Mirror verifizieren (läuft automatisch).** Das Dev-Repo
(`Goodsoup-Family-Crypt/overseer`) bleibt intern; **`lukasguziel/overseer`**
ist die öffentliche Datenquelle — dort liegen die Releases und die Doku
(README ohne Development-Abschnitt + `docs/FEATURES.md` + Screenshots, kein
Code). Das Spiegeln macht `.github/workflows/mirror.yml` selbst:

- Release: `release.yml` ruft nach dem Build den Mirror-Job auf (Asset +
  Body → öffentliches Repo). Der Notes-Edit aus Schritt 6 feuert
  `release: edited` und synct den Body automatisch nach.
- Docs: jeder Push auf `main`, der `README.md`, `docs/FEATURES.md` oder
  `docs/screenshots/**` anfasst, synct die Doku ins öffentliche Repo.

Hier nur prüfen, dass es geklappt hat:

```bash
gh release view v<version> --repo lukasguziel/overseer --json url,assets --jq '{url, assets: [.assets[].name]}'
```

Fehlt das Release, den Mirror-Lauf ansehen (`gh run list
--workflow=mirror.yml`) — häufigste Ursache: `MIRROR_TOKEN`-Secret abgelaufen
oder widerrufen (es ist das `gh`-Token von lukasguziel; neu setzen mit
`gh secret set MIRROR_TOKEN --repo Goodsoup-Family-Crypt/overseer --body "$(gh auth token)"`).
Das öffentliche Repo ist ggf. noch privat — der Mirror funktioniert trotzdem;
öffentlich schaltet es der User selbst.

Danach die **öffentlichen Issues checken** — sie sind der einzige Rückkanal
der Nutzer und tauchen im Dev-Repo nirgends auf:
```bash
gh issue list --repo lukasguziel/overseer --state open
```
Offene Issues dem User kurz nennen (bereits Gefixtes gehört in die Notes).

**9. Clean-Test anbieten (immer fragen).** Das Release ist erst dann echt
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
    -Zip "$env:TEMP\so-release\Overseer-v<version>.zip" `
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
  `%TEMP%\Overseer-release-test\<timestamp>\`, BEVOR es löscht, und
  bricht ab, wenn das Backup nicht schreibbar ist. Dem User den Backup-Pfad
  nennen.
- Der Test läuft **komplett frisch** (Default: kein `config.json`, keine
  `presets/`, kein `dev_repo.txt` → echtes First-Run-Verhalten eines neuen
  Users). Nur wenn der User ausdrücklich den Release-Code gegen seine echten
  Daten sehen will: `-KeepData`.
- Danach: C4D starten, `Shift+C` → **„Overseer"**, Web-UI muss
  aufgehen. Läuft es nicht, ist das ein **Release-Bug** (Packaging), kein
  lokales Problem — Zip-Inhalt prüfen (`web/index.html`, `overseer/`,
  `vendor/` vorhanden?), fixen, neue Version.

**10. Restore — immer, nicht fragen.** Der Clean-Test ist ein Wegwerf-Zustand:
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
- **Workflow rot nach `main`-Push** → Ursache auf `dev` fixen, erneut nach
  `main` mergen — kein Tag-Handling nötig, der Workflow verschiebt den Tag
  selbst und nur bei grünen Gates. (Es entsteht kein halbes Release — der
  Release-Step läuft zuletzt.)
- **`gh` nicht eingeloggt** → `gh auth status`; der User muss `gh auth
  login` selbst ausführen (interaktiv, ggf. via `! gh auth login`).
- **Tag existiert schon** → Version war schon released; neue Version
  wählen, niemals einen bestehenden Release-Tag verschieben.
- **Uncommitted fremde Änderungen im Tree** → den User fragen, ob sie mit
  ins Release sollen; nie stillschweigend mittaggen oder stashen.

## Nicht vergessen
- Zip ist gegen **C4D 2024** gebaut/getestet (steht so im Release-Body).
- Der Clean-Test (Schritt 9) installiert das **Release-Asset**, nicht den
  Working Tree — das ist der ganze Punkt. Niemals stattdessen `deploy.ps1`
  fahren, das würde den Dev-Stand testen.
- Danach gilt wieder die normale Deploy-Regel: wer weiterentwickelt,
  deployt mit dem `deploy`-Skill (und überschreibt den Release-Stand).
