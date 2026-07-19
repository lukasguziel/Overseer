# Deploys the Overseer addon into one or more Blender addon folders.
#
# Blender twin of deploy.ps1. The installable addon is a single folder named
# "overseer" that bundles the addon loader (__init__.py = src/blender_addon/__init__.py),
# the shared package (overseer/), the Vite build (web/) and Pillow (vendor/).
# This script mirrors those from the working tree into
#   <blender_config>/scripts/addons/overseer/
#
# The repo carries NO target path. Targets come from (first hit wins):
#   1. -Target <dir>[,<dir>...]  explicit ADDON directories (the "overseer"
#                                folder itself, e.g.
#                                ...\Blender\4.2\scripts\addons\overseer).
#                                Deploys to ALL of them.
#   2. deploy.config.json        machine-local, GITIGNORED. Schema 2 keys targets
#                                by WINDOWS USER ($env:USERNAME). Blender targets
#                                live in an OPTIONAL per-user "blender_targets"
#                                list (separate from the Cinema "targets" list),
#                                each entry { blender, addon_dir }. All are
#                                deployed in one run.
#                                Template: deploy.config.example.json.
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
$addonLoader = Join-Path $src "blender_addon\__init__.py"

$cfgPath = Join-Path $PSScriptRoot "deploy.config.json"

if (-not $Target -or $Target.Count -eq 0) {
  if (Test-Path $cfgPath) {
    try {
      $cfg = Get-Content $cfgPath -Raw | ConvertFrom-Json
    } catch {
      Write-Error "deploy.config.json is not valid JSON: $($_.Exception.Message)"
      exit 1
    }
    $userEntry = $null
    if ($cfg.users) { $userEntry = $cfg.users.PSObject.Properties[$env:USERNAME].Value }
    if ($userEntry -and $userEntry.blender_targets) {
      $Target = @($userEntry.blender_targets | ForEach-Object { $_.addon_dir })
    } else {
      Write-Error ("deploy.config.json has no 'blender_targets' for Windows user '$env:USERNAME'. " +
        "Add a per-user 'blender_targets' list (each { blender, addon_dir }) - see " +
        "deploy.config.example.json - or pass -Target <addon dir>.")
      exit 1
    }
  }
}
if (-not $Target -or $Target.Count -eq 0) {
  Write-Error ("No target. Add a 'blender_targets' list to deploy.config.json " +
    "(copy deploy.config.example.json) - or pass -Target <addon dir> " +
    "(e.g. ...\Blender\4.2\scripts\addons\overseer).")
  exit 1
}

# Mirror a directory in place with robocopy: unchanged (possibly locked)
# files are skipped instead of aborting mid-copy, so a lock can never leave
# the target half-empty like delete-then-copy did. Exit codes 0-7 = success.
function Mirror([string]$From, [string]$To) {
  robocopy $From $To /MIR /R:0 /W:0 /XD __pycache__ /NFL /NDL /NJH /NJS | Out-Null
  if ($LASTEXITCODE -ge 8) { throw "robocopy failed (exit $LASTEXITCODE) - a changed file is locked; close Blender and retry." }
  $global:LASTEXITCODE = 0
}

function Deploy-To([string]$Dir) {
  try {
    if (-not (Test-Path $Dir)) { New-Item -ItemType Directory -Force -Path $Dir | Out-Null }
    $probe = Join-Path $Dir ".write_probe"
    New-Item -ItemType File -Force -Path $probe | Out-Null
    Remove-Item -Force $probe
  } catch {
    Write-Output "  FAIL: cannot write to '$Dir' ($($_.Exception.Message))"
    Write-Output ("        If this is under Program Files, run an elevated PowerShell - or deploy to the " +
      "user config addons folder instead (no admin needed).")
    $script:failed = @("write probe -> $($_.Exception.Message)")
    return
  }

  $script:failed = @()
  function Step([string]$What, [scriptblock]$Do) {
    try { & $Do; Write-Output "  ok: $What" }
    catch { $script:failed += "$What -> $($_.Exception.Message)"; Write-Output "  FAIL: $What -> $($_.Exception.Message)" }
  }

  # Stamp the repo root so the addon knows where to mirror scene_report.json into
  # <repo>/var (read by webapi._export_dir; machine-local, lives only in the target).
  Step "dev_repo.txt" { Set-Content -Path (Join-Path $Dir "dev_repo.txt") -Value $repoRoot -Encoding utf8 }

  # Addon loader: src/blender_addon/__init__.py becomes <addon>/__init__.py.
  Step "__init__.py (addon loader)" { Copy-Item $addonLoader (Join-Path $Dir "__init__.py") -Force }

  # Extension manifest (Blender 4.2+/5.x extensions system). Harmless for a
  # legacy scripts/addons install (the legacy loader ignores it); REQUIRED when
  # the target is an extensions/<repo> dir (Blender 5.x dropped legacy add-ons).
  $manifest = Join-Path $src "blender_addon\blender_manifest.toml"
  if (Test-Path $manifest) {
    Step "blender_manifest.toml" { Copy-Item $manifest (Join-Path $Dir "blender_manifest.toml") -Force }
  }

  # Mirror the shared package recursively (core/, naming/, blender/, cinema/, ...).
  Step "overseer/" { Mirror (Join-Path $src "overseer") (Join-Path $Dir "overseer") }

  # Bundled third-party packages (Pillow, for high-quality texture resampling).
  # Optional: generate with: python .claude/skills/release/vendor_pillow.py
  # ASCII only in this file: PS 5.1 reads it as ANSI and chokes on fancy dashes.
  $vendorSrc = Join-Path $src "vendor"
  if (Test-Path $vendorSrc) {
    Step "vendor/ (Pillow)" { Mirror $vendorSrc (Join-Path $Dir "vendor") }
  } else {
    Write-Host "  WARN: no vendor/ - texture resize falls back to a lower-quality scaler" -ForegroundColor Yellow
  }

  # Mirror web bundle (Vite build output)
  $webSrc = Join-Path $src "web"
  if (Test-Path $webSrc) {
    Step "web/" { Mirror $webSrc (Join-Path $Dir "web") }
  } else {
    Write-Output "  WARN: no web/ bundle - run 'pnpm run build' in frontend/ first."
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
    Write-Output "(Locked files? Close Blender and retry.)"
  } else {
    Write-Output "Deployed to: $dir"
  }
  Write-Output ""
}

if ($anyFailed) { exit 1 }
Write-Output "All $($Target.Count) target(s) deployed."
Write-Output "In Blender: Edit > Preferences > Add-ons, enable 'Overseer' (Scene). Then View3D > Sidebar (N) > Overseer."
