# Clean-install a released Overseer-<version>.zip into a Cinema 4D plugin
# folder — the way a new user would get it. Wipes the target (after a full
# backup) so no dev leftovers (config.json, presets/, plans/, dev_repo.txt)
# can mask a packaging bug.
#
# Program Files targets need an ELEVATED shell. Cinema 4D must be closed.
#
#   powershell -File .claude/skills/release/test-release.ps1 `
#       -Zip  C:\path\Overseer-v1.0.0.zip `
#       -Target "C:\Program Files\Maxon Cinema 4D 2024\plugins\Overseer"
#
# The target holds real user data (config.json with the rule set, presets/,
# plans/). A verified full backup is ALWAYS taken first; nothing is deleted
# unless it succeeded. The install is throwaway - ALWAYS -Restore afterwards.
#
#   -KeepData   keep the user's config.json + presets/ + plans/ across the
#               wipe (tests release CODE against real data, not the first run)
#   -Restore    undo: put the newest backup back and exit
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$Zip,
    [Parameter(Mandatory = $true)][string]$Target,
    [string]$BackupRoot = (Join-Path $env:TEMP "Overseer-release-test"),
    [switch]$KeepData,
    [switch]$Restore
)

$ErrorActionPreference = "Stop"
# User data the release zip does not ship — never destroyed without a backup.
$DataItems = @("config.json", "presets", "plans", "dev_repo.txt")

function Fail($msg) { Write-Host "FAILED: $msg" -ForegroundColor Red; exit 1 }
function Step($msg) { Write-Host "  $msg" -ForegroundColor DarkGray }

if (-not (Test-Path $BackupRoot)) { New-Item -ItemType Directory -Force $BackupRoot | Out-Null }

# --- Preflight (applies to install AND restore - both write to $Target) ---
if (Get-Process -Name "Cinema 4D" -ErrorAction SilentlyContinue) {
    Fail "Cinema 4D is running - close it (loaded files are locked, and the .pyp only reloads on start)."
}
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator) -and $Target -like "$env:ProgramFiles*") {
    Fail "Target is under Program Files - run this in an ELEVATED shell."
}

# --- Restore mode: newest backup wins ------------------------------------
if ($Restore) {
    $bak = Get-ChildItem $BackupRoot -Directory -ErrorAction SilentlyContinue |
           Where-Object { Test-Path (Join-Path $_.FullName "overseer.pyp") } |
           Sort-Object Name -Descending | Select-Object -First 1
    if (-not $bak) { Fail "No usable backup found under $BackupRoot" }
    Step "Restoring $($bak.Name) -> $Target"
    if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
    Copy-Item -Recurse -Force $bak.FullName $Target
    Write-Host "RESTORED: $((Get-ChildItem $Target -Recurse -File).Count) files from backup $($bak.Name)" -ForegroundColor Green
    exit 0
}

if (-not (Test-Path $Zip)) { Fail "Zip not found: $Zip" }

# --- Unpack --------------------------------------------------------------
$work = Join-Path $BackupRoot "unpacked"
if (Test-Path $work) { Remove-Item -Recurse -Force $work }
Step "Unpacking $(Split-Path $Zip -Leaf)"
Expand-Archive -Path $Zip -DestinationPath $work

# The zip carries a top-level Overseer/ folder; install its CONTENTS.
$src = Join-Path $work "Overseer"
if (-not (Test-Path $src)) { $src = $work }
if (-not (Test-Path (Join-Path $src "overseer.pyp"))) {
    Fail "No overseer.pyp in the zip - wrong artifact or broken packaging."
}

# --- Backup (MANDATORY - the target holds the user's real config.json, ----
# --- presets/ and plans/; nothing is deleted before this verifies) --------
$stamp = Get-Date -Format "yyyy-MM-dd-HHmmss"
if (Test-Path $Target) {
    $bak = Join-Path $BackupRoot $stamp
    $before = (Get-ChildItem $Target -Recurse -File).Count
    Step "Backing up current install ($before files) -> $bak"
    Copy-Item -Recurse -Force $Target $bak
    $saved = (Get-ChildItem $bak -Recurse -File -ErrorAction SilentlyContinue).Count
    if ($saved -ne $before) { Fail "Backup incomplete ($saved/$before files) - target left untouched." }
    Step "Backup verified: $saved files"
} else {
    $bak = $null
    Step "No existing install (nothing to back up)."
}

# --- Wipe + install ------------------------------------------------------
if (Test-Path $Target) { Remove-Item -Recurse -Force $Target }
New-Item -ItemType Directory -Force $Target | Out-Null
Step "Installing release -> $Target"
Copy-Item -Path (Join-Path $src "*") -Destination $Target -Recurse -Force

if ($KeepData -and $bak) {
    foreach ($item in $DataItems) {
        $from = Join-Path $bak $item
        if (Test-Path $from) { Step "Restoring $item"; Copy-Item -Recurse -Force $from $Target }
    }
}

# --- Verify --------------------------------------------------------------
$count = (Get-ChildItem $Target -Recurse -File).Count
if (-not (Test-Path (Join-Path $Target "overseer.pyp"))) { Fail "Loader missing after install." }
if (-not (Test-Path (Join-Path $Target "web\index.html")))      { Fail "Frontend (web/index.html) missing - zip built without a frontend build." }
if (-not $KeepData) {
    foreach ($item in $DataItems) {
        if (Test-Path (Join-Path $Target $item)) { Fail "Leftover dev data in a clean install: $item" }
    }
}

Write-Host "OK: $count files installed from $(Split-Path $Zip -Leaf)" -ForegroundColor Green
if ($bak) { Write-Host "Backup: $bak" -ForegroundColor DarkGray }
Write-Host "Next: start Cinema 4D, Shift+C -> 'Overseer'." -ForegroundColor Green
Write-Host "Then ALWAYS restore (this install is throwaway, it has none of your data):" -ForegroundColor Yellow
Write-Host "  test-release.ps1 -Target `"$Target`" -Restore" -ForegroundColor Yellow
