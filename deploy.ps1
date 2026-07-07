# Deploys the Scene Organizer plugin into a Cinema 4D plugin folder.
#
# The repo carries NO target path. The target comes from (first hit wins):
#   1. -Target <dir>        explicit plugin directory
#   2. deploy.config.json   machine-local, GITIGNORED - each user picks their
#                           own Cinema once (the 'deploy' skill in Claude Code
#                           lists all installed versions and writes this file;
#                           template: deploy.config.example.json)
param(
  [Parameter(Mandatory = $false)]
  [string]$Target = ""
)

$ErrorActionPreference = "Stop"
$src = Join-Path $PSScriptRoot "src"

if (-not $Target) {
  $cfgPath = Join-Path $PSScriptRoot "deploy.config.json"
  if (Test-Path $cfgPath) {
    try {
      $Target = (Get-Content $cfgPath -Raw | ConvertFrom-Json).plugin_dir
    } catch {
      Write-Error "deploy.config.json is not valid JSON: $($_.Exception.Message)"
      exit 1
    }
  }
}
if (-not $Target) {
  Write-Error ("No target. Create deploy.config.json (copy deploy.config.example.json, " +
    "or run the 'deploy' skill in Claude Code to pick an installed Cinema 4D) - " +
    "or pass -Target <plugin dir>.")
  exit 1
}

# Elevation hint: Program Files needs admin, the prefs folder does not.
try {
  if (-not (Test-Path $Target)) { New-Item -ItemType Directory -Force -Path $Target | Out-Null }
  $probe = Join-Path $Target ".write_probe"
  New-Item -ItemType File -Force -Path $probe | Out-Null
  Remove-Item -Force $probe
} catch {
  Write-Error ("Cannot write to '$Target' ($($_.Exception.Message)). " +
    "If this is under Program Files, run an elevated PowerShell - or deploy to the " +
    "user prefs plugin folder instead (no admin needed).")
  exit 1
}

$failed = @()
function Step([string]$What, [scriptblock]$Do) {
  try { & $Do; Write-Output "  ok: $What" }
  catch { $script:failed += "$What -> $($_.Exception.Message)"; Write-Output "  FAIL: $What -> $($_.Exception.Message)" }
}

Write-Output "Deploying to: $Target"

# Loader + config template (the user's config.json is NOT overwritten)
Step "scene_organizer.pyp" { Copy-Item (Join-Path $src "scene_organizer.pyp") $Target -Force }
Step "so_logo.jpg" { Copy-Item (Join-Path $src "so_logo.jpg") $Target -Force }
Step "config.example.json" { Copy-Item (Join-Path $src "config.example.json") $Target -Force }

# config.json: ONLY seed if none exists in the target (never overwrite user/preset
# changes in the plugin).
$cfgSrc = Join-Path $src "config.json"
$cfgDst = Join-Path $Target "config.json"
if ((Test-Path $cfgSrc) -and (-not (Test-Path $cfgDst))) {
  Step "config.json (seeded, was missing)" { Copy-Item $cfgSrc $cfgDst -Force }
}

# Mirror package cleanly (without __pycache__)
Step "sceneorg/" {
  $pkgDst = Join-Path $Target "sceneorg"
  if (Test-Path $pkgDst) { Remove-Item -Recurse -Force $pkgDst }
  New-Item -ItemType Directory -Force -Path $pkgDst | Out-Null
  Get-ChildItem (Join-Path $src "sceneorg") -Filter *.py | Copy-Item -Destination $pkgDst -Force
}

# Merge presets: repo presets are copied in, but presets the user saved in
# the plugin ("Save current settings as preset") are NEVER deleted.
Step "presets/" {
  $presetSrc = Join-Path $src "presets"
  $presetDst = Join-Path $Target "presets"
  if (-not (Test-Path $presetDst)) { New-Item -ItemType Directory -Force -Path $presetDst | Out-Null }
  if (Test-Path $presetSrc) {
    Get-ChildItem $presetSrc -Filter *.json | Copy-Item -Destination $presetDst -Force
  }
}

# Bring along restructuring plans (written by the skill), if present.
# The plans/ folder in the plugin is NOT deleted (user/skill artifacts).
$planSrc = Join-Path $src "plans"
if (Test-Path $planSrc) {
  Step "plans/" {
    $planDst = Join-Path $Target "plans"
    if (-not (Test-Path $planDst)) { New-Item -ItemType Directory -Force -Path $planDst | Out-Null }
    Get-ChildItem $planSrc -Filter *.json | Copy-Item -Destination $planDst -Force
  }
}

# Mirror web bundle (Vite build output)
$webSrc = Join-Path $src "web"
if (Test-Path $webSrc) {
  Step "web/" {
    $webDst = Join-Path $Target "web"
    if (Test-Path $webDst) { Remove-Item -Recurse -Force $webDst }
    Copy-Item -Recurse $webSrc $webDst -Force
  }
} else {
  Write-Output "  WARN: no web/ bundle - run 'npm run build' in frontend/ first."
}

if ($failed.Count) {
  Write-Output ""
  Write-Output "DEPLOY INCOMPLETE - $($failed.Count) step(s) failed:"
  $failed | ForEach-Object { Write-Output "  - $_" }
  Write-Output "(Locked files? Close the Scene Organizer dialogs in C4D and retry.)"
  exit 1
}
Write-Output ""
Write-Output "Deployed to: $Target"
