# Findet alle installierten Cinema-4D-Versionen und gibt sie als JSON aus.
# Pro Installation zwei moegliche Plugin-Ziele:
#   - prefs (User-Prefs-Ordner, KEIN Admin noetig) - bevorzugt
#   - app   (Program Files, braucht Admin)
# Output: JSON-Array [{name, location, plugin_dir, needs_admin}]
$ErrorActionPreference = "SilentlyContinue"
$found = @()

# Program-Files-Installationen (= die eigentlichen Cinema-Versionen)
foreach ($root in @("C:\Program Files", "C:\Program Files (x86)")) {
  Get-ChildItem -Path $root -Directory -Filter "*Cinema 4D*" | ForEach-Object {
    $found += [pscustomobject]@{
      name        = $_.Name
      location    = "app"
      plugin_dir  = Join-Path $_.FullName "plugins\Overseer"
      needs_admin = $true
    }
  }
}

# User-Prefs-Ordner (z.B. "Maxon Cinema 4D 2024_A5DBFF93")
$prefsRoot = Join-Path $env:APPDATA "Maxon"
Get-ChildItem -Path $prefsRoot -Directory -Filter "*Cinema 4D*" |
  Where-Object { $_.Name -notmatch "_p$" } | ForEach-Object {
  $found += [pscustomobject]@{
    name        = ($_.Name -replace "_[0-9A-F]{8}$", "") + " (user prefs)"
    location    = "prefs"
    plugin_dir  = Join-Path $_.FullName "plugins\Overseer"
    needs_admin = $false
  }
}

if (-not $found) {
  Write-Output "[]"
} else {
  ConvertTo-Json @($found)
}
