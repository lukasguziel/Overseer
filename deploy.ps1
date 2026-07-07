# Deployt das Scene-Organizer-Plugin in den C4D-2024-Plugin-Ordner.
# Aufruf:  powershell -File deploy.ps1
# Ziel = anwendungsweiter Program-Files-Plugin-Ordner (globale CLAUDE.md) -> BRAUCHT ADMIN.
# Skript in einer *elevated* PowerShell ausfuehren.
$src    = Join-Path $PSScriptRoot "src"
$target = "C:\Program Files\Maxon Cinema 4D 2024\plugins\SceneOrganizer"

if (-not (Test-Path $target)) { New-Item -ItemType Directory -Force -Path $target | Out-Null }

# Loader + Config-Vorlage (config.json des Users wird NICHT ueberschrieben)
Copy-Item -Path (Join-Path $src "scene_organizer.pyp")  -Destination $target -Force
Copy-Item -Path (Join-Path $src "config.example.json")  -Destination $target -Force

# config.json: NUR seeden, wenn im Ziel keine existiert (User-/Preset-Aenderungen
# im Plugin nie ueberschreiben). Fehlt sie, faellt das Plugin sonst auf Defaults
# zurueck (nur Cameras+Lights).
$cfgSrc = Join-Path $src "config.json"
$cfgDst = Join-Path $target "config.json"
if ((Test-Path $cfgSrc) -and (-not (Test-Path $cfgDst))) {
  Copy-Item -Path $cfgSrc -Destination $cfgDst -Force
  Write-Output "config.json geseedet (fehlte im Ziel)."
}

# Package (ohne __pycache__), sauber spiegeln
$pkgSrc = Join-Path $src "sceneorg"
$pkgDst = Join-Path $target "sceneorg"
if (Test-Path $pkgDst) { Remove-Item -Recurse -Force $pkgDst }
New-Item -ItemType Directory -Force -Path $pkgDst | Out-Null
Get-ChildItem -Path $pkgSrc -Filter *.py | Copy-Item -Destination $pkgDst -Force

# Presets (kuratierte Styles) spiegeln
$presetSrc = Join-Path $src "presets"
$presetDst = Join-Path $target "presets"
if (Test-Path $presetDst) { Remove-Item -Recurse -Force $presetDst }
if (Test-Path $presetSrc) { Copy-Item -Recurse -Path $presetSrc -Destination $presetDst -Force }

# Umstrukturierungs-Plaene (vom Skill geschrieben) mitnehmen, falls vorhanden.
# Der plans/-Ordner im Plugin wird NICHT geloescht (User-/Skill-Artefakte).
$planSrc = Join-Path $src "plans"
$planDst = Join-Path $target "plans"
if (Test-Path $planSrc) {
  if (-not (Test-Path $planDst)) { New-Item -ItemType Directory -Force -Path $planDst | Out-Null }
  Get-ChildItem -Path $planSrc -Filter *.json | Copy-Item -Destination $planDst -Force
}

# Web-Bundle (Vite-Build-Output) spiegeln
$webSrc = Join-Path $src "web"
$webDst = Join-Path $target "web"
if (Test-Path $webDst) { Remove-Item -Recurse -Force $webDst }
if (Test-Path $webSrc) { Copy-Item -Recurse -Path $webSrc -Destination $webDst -Force }
else { Write-Output "WARN: kein web/ Bundle - erst 'npm run build' im frontend/ ausfuehren." }

Write-Output "Deployed nach: $target"
Get-ChildItem $target -Recurse | Select-Object FullName, Length | Format-Table -AutoSize
