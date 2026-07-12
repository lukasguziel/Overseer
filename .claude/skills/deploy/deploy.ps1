# Deploys the Scene Organizer plugin into one or more Cinema 4D plugin folders.
#
# The repo carries NO target path. Targets come from (first hit wins):
#   1. -Target <dir>[,<dir>...]  explicit plugin directories (deploys to ALL of them)
#   2. deploy.config.json        machine-local, GITIGNORED. Schema 2 keys the
#                                targets by WINDOWS USER ($env:USERNAME), so each
#                                user on this machine can point at their own
#                                Cinema(s). Each user holds a LIST of targets -
#                                all of them are deployed in one run.
#                                Legacy flat configs ({cinema, location, plugin_dir})
#                                are migrated in place on first run.
#                                Template: deploy.config.example.json. The 'deploy'
#                                skill in Claude Code fills this interactively.
param(
  [Parameter(Mandatory = $false)]
  [string[]]$Target = @()
)

$ErrorActionPreference = "Stop"

# `powershell -File` flattens array arguments into one comma-joined string,
# so accept "dir1,dir2" as well as a real string[].
$Target = @($Target | ForEach-Object { $_ -split ',' } | ForEach-Object { $_.Trim() } | Where-Object { $_ })
# Script lives in .claude/skills/deploy/ -- the repo root is three levels up.
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..\..")).Path
$src = Join-Path $repoRoot "src"

$cfgPath = Join-Path $PSScriptRoot "deploy.config.json"

if (-not $Target -or $Target.Count -eq 0) {
  if (Test-Path $cfgPath) {
    try {
      $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
    } catch {
      Write-Error "deploy.config.json is not valid JSON: $($_.Exception.Message)"
      exit 1
    }
    if ($cfg.PSObject.Properties.Name -contains "plugin_dir") {
      # Legacy flat schema: adopt as the current Windows user's single target
      # and rewrite the file as schema 2.
      $entry = @{ cinema = $cfg.cinema; location = $cfg.location; plugin_dir = $cfg.plugin_dir }
      $cfg = [pscustomobject]@{ schema = 2; users = [pscustomobject]@{ $env:USERNAME = [pscustomobject]@{ targets = @([pscustomobject]$entry) } } }
      $cfg | ConvertTo-Json -Depth 6 | Set-Content -Path $cfgPath -Encoding utf8
      Write-Output "Migrated deploy.config.json to per-user schema 2 (user '$env:USERNAME')."
    }
    $userEntry = $null
    if ($cfg.users) { $userEntry = $cfg.users.PSObject.Properties[$env:USERNAME].Value }
    if ($userEntry -and $userEntry.targets) {
      $Target = @($userEntry.targets | ForEach-Object { $_.plugin_dir })
    } else {
      Write-Error ("deploy.config.json has no targets for Windows user '$env:USERNAME'. " +
        "Run the 'deploy' skill in Claude Code to pick your Cinema 4D installation(s), " +
        "or pass -Target <plugin dir>.")
      exit 1
    }
  }
}
if (-not $Target -or $Target.Count -eq 0) {
  Write-Error ("No target. Create deploy.config.json (copy deploy.config.example.json, " +
    "or run the 'deploy' skill in Claude Code to pick an installed Cinema 4D) - " +
    "or pass -Target <plugin dir>.")
  exit 1
}

# Mirror a directory in place with robocopy: unchanged (possibly locked)
# files are skipped instead of aborting mid-copy, so a lock can never leave
# the target half-empty like delete-then-copy did. Exit codes 0-7 = success.
function Mirror([string]$From, [string]$To) {
  robocopy $From $To /MIR /R:0 /W:0 /XD __pycache__ /NFL /NDL /NJH /NJS | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "robocopy failed (exit $LASTEXITCODE) - a changed file is locked; close the Scene Organizer dialogs in C4D and retry." }
  $global:LASTEXITCODE = 0
}

function Deploy-To([string]$Dir) {
  # Elevation hint: Program Files needs admin, the prefs folder does not.
  try {
    if (-not (Test-Path $Dir)) { New-Item -ItemType Directory -Force -Path $Dir | Out-Null }
    $probe = Join-Path $Dir ".write_probe"
    New-Item -ItemType File -Force -Path $probe | Out-Null
    Remove-Item -Force $probe
  } catch {
    Write-Output "  FAIL: cannot write to '$Dir' ($($_.Exception.Message))"
    Write-Output ("        If this is under Program Files, run an elevated PowerShell - or deploy to the " +
      "user prefs plugin folder instead (no admin needed).")
    $script:failed = @("write probe -> $($_.Exception.Message)")
    return
  }

  $script:failed = @()
  function Step([string]$What, [scriptblock]$Do) {
    try { & $Do; Write-Output "  ok: $What" }
    catch { $script:failed += "$What -> $($_.Exception.Message)"; Write-Output "  FAIL: $What -> $($_.Exception.Message)" }
  }

  # Stamp the repo root so the plugin knows where to mirror scene_report.json
  # (read by webapi._export_dir; machine-local by nature, lives only in the target).
  Step "dev_repo.txt" { Set-Content -Path (Join-Path $Dir "dev_repo.txt") -Value $repoRoot -Encoding utf8 }

  # Loader + config template (the user's config.json is NOT overwritten)
  Step "scene_organizer.pyp" { Copy-Item (Join-Path $src "scene_organizer.pyp") $Dir -Force }
  Step "so_logo.png" { Copy-Item (Join-Path $src "so_logo.png") $Dir -Force }
  Step "config.example.json" { Copy-Item (Join-Path $src "config.example.json") $Dir -Force }

  # config.json: ONLY seed if none exists in the target (never overwrite user/preset
  # changes in the plugin).
  $cfgSrc = Join-Path $src "config.json"
  $cfgDst = Join-Path $Dir "config.json"
  if ((Test-Path $cfgSrc) -and (-not (Test-Path $cfgDst))) {
    Step "config.json (seeded, was missing)" { Copy-Item $cfgSrc $cfgDst -Force }
  }

  # Mirror package recursively (subpackages: core/, naming/, structure/, cinema/).
  Step "sceneorg/" { Mirror (Join-Path $src "sceneorg") (Join-Path $Dir "sceneorg") }

  # Bundled third-party packages (Pillow, for high-quality texture resampling).
  # Optional: generate with: python tools/vendor_pillow.py
  # Without it the plugin falls back to the Cinema bitmap engine.
  # ASCII only in this file: PS 5.1 reads it as ANSI and chokes on fancy dashes.
  $vendorSrc = Join-Path $src "vendor"
  if (Test-Path $vendorSrc) {
    Step "vendor/ (Pillow)" { Mirror $vendorSrc (Join-Path $Dir "vendor") }
  } else {
    Write-Host "  WARN: no vendor/ - texture resize falls back to the Cinema scaler" -ForegroundColor Yellow
  }

  # Merge presets: repo presets are copied in, but presets the user saved in
  # the plugin ("Save current settings as preset") are NEVER deleted.
  Step "presets/" {
    $presetSrc = Join-Path $src "presets"
    $presetDst = Join-Path $Dir "presets"
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
      $planDst = Join-Path $Dir "plans"
      if (-not (Test-Path $planDst)) { New-Item -ItemType Directory -Force -Path $planDst | Out-Null }
      Get-ChildItem $planSrc -Filter *.json | Copy-Item -Destination $planDst -Force
    }
  }

  # Mirror web bundle (Vite build output)
  $webSrc = Join-Path $src "web"
  if (Test-Path $webSrc) {
    Step "web/" { Mirror $webSrc (Join-Path $Dir "web") }
  } else {
    Write-Output "  WARN: no web/ bundle - run 'npm run build' in frontend/ first."
  }
}

$anyFailed = $false
foreach ($dir in $Target) {
  Write-Output "Deploying to: $dir"
  Deploy-To $dir
  $failed = @($script:failed)
  if ($failed.Count) {
    $anyFailed = $true
    Write-Output ""
    Write-Output "DEPLOY INCOMPLETE for '$dir' - $($failed.Count) step(s) failed:"
    $failed | ForEach-Object { Write-Output "  - $_" }
    Write-Output "(Locked files? Close the Scene Organizer dialogs in C4D and retry.)"
  } else {
    Write-Output "Deployed to: $dir"
  }
  Write-Output ""
}

if ($anyFailed) { exit 1 }
Write-Output "All $($Target.Count) target(s) deployed."
