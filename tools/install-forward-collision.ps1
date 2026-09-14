param([string]$Destination = (Join-Path $PSScriptRoot '../../MODS/mods/Wayfarer'))
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$target = (Resolve-Path -LiteralPath $Destination).Path
$staging = Join-Path $projectRoot 'build/forward-collision-update'
$manifest = Get-Content -LiteralPath (Join-Path $staging 'update-manifest.json') -Raw | ConvertFrom-Json
$source = Join-Path $staging 'SKSE/Plugins/Wayfarer.dll'
$output = Join-Path $target 'SKSE/Plugins/Wayfarer.dll'
if ((Get-FileHash -LiteralPath $source).Hash -ne $manifest.dllSha256) { throw 'Staged DLL hash mismatch' }
if (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { throw 'Save and close Skyrim before installing the prepared update.' }

$backup = Join-Path $projectRoot ('backups/installed-pre-forward-collision-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
Copy-Item -LiteralPath $output -Destination (Join-Path $backup 'Wayfarer.dll')
$ini = Join-Path $target 'SKSE/Plugins/Wayfarer.ini'
if (Test-Path -LiteralPath $ini) { Copy-Item -LiteralPath $ini -Destination (Join-Path $backup 'Wayfarer.ini') }
$preserved = @{}
foreach ($file in Get-ChildItem -LiteralPath $target -File -Recurse) {
    if ($file.FullName -ne $output) { $preserved[$file.FullName] = (Get-FileHash -LiteralPath $file.FullName).Hash }
}
if (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { throw "Skyrim reopened; installation stopped. Backup: $backup" }
Copy-Item -LiteralPath $source -Destination $output -Force
if ((Get-FileHash -LiteralPath $output).Hash -ne $manifest.dllSha256) { throw "Installed DLL hash mismatch. Backup: $backup" }
foreach ($file in $preserved.Keys) {
    if ((Get-FileHash -LiteralPath $file).Hash -ne $preserved[$file]) { throw "Unexpected asset/settings change: $file" }
}
$receipt = @{
    feature = $manifest.feature
    installedAt = (Get-Date -Format o)
    destination = $output
    dllSha256 = $manifest.dllSha256
    backup = $backup
    preservedFiles = $preserved.Count
    settingsAndAssetsPreserved = $true
    handHoldingRevision = '11'
}
$json = $receipt | ConvertTo-Json -Depth 5
$json | Set-Content -LiteralPath (Join-Path $backup 'install.json') -Encoding utf8
$json | Set-Content -LiteralPath (Join-Path $projectRoot 'build/forward-collision-install.json') -Encoding utf8
$json
