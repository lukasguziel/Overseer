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

# Deploy — plugin into one or more Cinema 4D installations

All deploy files live in THIS skill folder (`.claude/skills/deploy/`):
`deploy.ps1` (the script), `deploy.config.json` (**gitignored**,
machine-local — the target path is NEVER in the repo; template
`deploy.config.example.json`).

**Config schema 2 — per Windows user:** targets are keyed by the Windows
username (`$env:USERNAME`) so each user on the same machine can pick their
own Cinema. Each user holds a **list** `targets` — all entries are deployed
in ONE run (multi-Cinema deploy):

```json
{
  "schema": 2,
  "users": {
    "lukas": {
      "targets": [
        { "cinema": "<name>", "location": "prefs|app", "plugin_dir": "<full path>" }
      ]
    }
  }
}
```

Legacy flat configs (`{cinema, location, plugin_dir}`) are migrated to
schema 2 automatically by `deploy.ps1` on first run (as the current user's
target).

## Procedure

**1. Determine the target(s).**
- The user names a version/path explicitly → step 3 (and update the config).
- `.claude/skills/deploy/deploy.config.json` has entries under
  `users.<$env:USERNAME>.targets` → use them, briefly tell the user the
  targets. Continue with step 4.
- Otherwise step 2. (NEVER touch entries of OTHER Windows users.)

**2. Find installed Cinemas and let the user choose.**
```bash
powershell -File .claude/skills/deploy/scripts/list_cinemas.ps1
```
Returns JSON `[{name, location, plugin_dir, needs_admin}]` — per installation
the Program Files target (`app`, needs admin) and the user prefs folder
(`prefs`, no admin).

List **ALL** entries, do not truncate — the user wants to see the complete
list and choose from it. Do NOT use `AskUserQuestion` (it hard-caps at 4
options). Instead print a lean, numbered markdown list, one line per entry,
and let the user pick — **one number or several** (e.g. `1,3` or `1 and 3`);
multi-select = deploy to several Cinemas at once:

```
 1. Cinema 4D 2024 — prefs   ·  …\Maxon Cinema 4D 2024_A5DBFF93\plugins\Overseer   (no admin)
 2. Cinema 4D 2024 — app     ·  C:\Program Files\Maxon Cinema 4D 2024\plugins\Overseer   (admin)
 …
```
- Order: per version first `prefs` (no admin), then `app` (admin);
  versions descending (newest first).
- Mark the user's current targets from `deploy.config.json` (if present)
  with `← current`.
- Add a short line above: "Which number(s)?" — then resolve the typed
  numbers. Don't push a recommendation; the choice is open.

**3. Write the choice to `.claude/skills/deploy/deploy.config.json`**
(gitignored, schema 2, see above): set the chosen entries under
`users.<$env:USERNAME>.targets` (replaces this user's previous list; leave
other users untouched).

**4. Deploy.**
```bash
powershell -File .claude/skills/deploy/deploy.ps1
```
Deploys all `targets` of the current Windows user one after another (or
explicitly: `-Target <dir1>,<dir2>`). If the list contains `app` targets
(Program Files) and the shell is not elevated: deploy ONLY the `app` targets
in an elevated, hidden window (the elevated window's output is invisible —
therefore redirect it into a log and print that afterwards;
`-WindowStyle Hidden` prevents the briefly flashing empty window):
```powershell
$log = "$env:TEMP\so_deploy.log"
Start-Process powershell -Verb RunAs -Wait -WindowStyle Hidden -ArgumentList "-NoProfile","-Command","& '<repo>\.claude\skills\deploy\deploy.ps1' -Target '<app plugin_dir 1>','<app plugin_dir 2>' *> '$log'"
Get-Content $log
```
(Announce the UAC prompt to the user.) Deploy `prefs` targets afterwards
normally without elevation (`-Target` with the prefs paths). Then verify
success PER TARGET: `Test-Path "<plugin_dir>\overseer.pyp"` and, for
frontend changes, compare the asset hashes in `<plugin_dir>\web\index.html`
against `src/web/index.html`.

**5. Failure modes.**
- `Cannot write` → elevation missing (see above) or wrong path.
- `FAIL: web/` while C4D is running → close the web dialog in C4D (it locks
  files), deploy again.
- `WARN: no web/ bundle` → run `cd frontend && npm run build` first.
- `no targets for Windows user '<name>'` → this Windows user has not chosen
  targets yet → step 2.
- One target fails, others ok → the script keeps deploying the rest, reports
  "DEPLOY INCOMPLETE" per target and exits 1 at the end.

## Don't forget
- Frontend changes need `npm run build` BEFORE the deploy (output `src/web/`).
- `bridge/`/`.pyp` changes only take effect after a C4D restart; pure
  `overseer` logic hot-reloads on the next command click.
- A `config.json` in the target is never touched (no seeding anymore —
  `src/config.json` is a personal working config and gitignored); without a
  `config.json` the plugin runs on `DEFAULT_CONFIG` like a zip install.
- The plugin is developed against C4D **2024** — deploying into other
  versions is untested; mention that briefly.
