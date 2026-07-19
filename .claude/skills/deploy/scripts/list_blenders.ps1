# Lists installable Blender addon/extension targets on this machine as JSON.
#
# Blender twin of list_cinemas.ps1. For every Blender user-config version dir
# under %APPDATA%\Blender Foundation\Blender\<ver>\ (and any version found only
# in Program Files but not yet launched), it emits BOTH candidate target dirs:
#   - extension : <cfg>\<ver>\extensions\user_default\overseer   (Blender 4.2+/5.x)
#   - legacy    : <cfg>\<ver>\scripts\addons\overseer            (<= 4.x add-ons)
# The addon_dir is the "overseer" folder itself (what deploy_blender.ps1 -Target
# expects). None need admin (user config dir).
#
# Output: JSON array [{ blender, kind, addon_dir, exists }].
$ErrorActionPreference = "Stop"

$cfgRoot = Join-Path $env:APPDATA "Blender Foundation\Blender"
$versions = @{}

# Versions that already have a user-config dir (launched at least once).
if (Test-Path $cfgRoot) {
  Get-ChildItem $cfgRoot -Directory | Where-Object { $_.Name -match '^\d+\.\d+$' } | ForEach-Object {
    $versions[$_.Name] = $true
  }
}
# Versions installed in Program Files (may not have been launched yet).
foreach ($base in @("$env:ProgramFiles\Blender Foundation", "${env:ProgramFiles(x86)}\Blender Foundation")) {
  if (Test-Path $base) {
    Get-ChildItem $base -Directory | Where-Object { $_.Name -match 'Blender\s+(\d+)\.(\d+)' } | ForEach-Object {
      if ($_.Name -match '(\d+)\.(\d+)') { $versions["$($matches[1]).$($matches[2])"] = $true }
    }
  }
}

$out = @()
foreach ($ver in ($versions.Keys | Sort-Object { [version]$_ } -Descending)) {
  $verMajor = [int]($ver.Split('.')[0])
  $verNum = [version]$ver
  # Extension path is the modern route (4.2+); legacy scripts/addons for older
  # (and as a fallback on 4.x). Recommend extension for >= 4.2.
  $ext = Join-Path $cfgRoot "$ver\extensions\user_default\overseer"
  $legacy = Join-Path $cfgRoot "$ver\scripts\addons\overseer"
  if ($verNum -ge [version]"4.2") {
    $out += [pscustomobject]@{ blender = "Blender $ver (extension)"; kind = "extension"; addon_dir = $ext; exists = (Test-Path $ext) }
  }
  if ($verMajor -lt 5) {
    $out += [pscustomobject]@{ blender = "Blender $ver (legacy add-on)"; kind = "legacy"; addon_dir = $legacy; exists = (Test-Path $legacy) }
  }
}

# PS 5.1 has no -AsArray: a single object would serialize as an object, so wrap.
$json = $out | ConvertTo-Json -Depth 4
if ($out.Count -le 1) { $json = "[" + $json + "]" }
$json
