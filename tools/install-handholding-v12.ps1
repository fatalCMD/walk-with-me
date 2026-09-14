param([string]$Destination = (Join-Path $PSScriptRoot '../../MODS/mods/Wayfarer'))
$ErrorActionPreference = 'Stop'
if (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { throw 'Close Skyrim before installing this update; its DLL is currently loaded.' }
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$target = (Resolve-Path -LiteralPath $Destination).Path
$staging = (Resolve-Path -LiteralPath (Join-Path $projectRoot 'build/handholding-v12-update')).Path
$manifest = Get-Content -LiteralPath (Join-Path $staging 'update-manifest.json') -Raw | ConvertFrom-Json
$before = @{}
foreach ($file in Get-ChildItem -LiteralPath $target -File -Recurse) {
    $before[$file.FullName.Substring($target.Length+1)] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash.ToLowerInvariant()
}
$backup = Join-Path $projectRoot ('backups/installed-pre-handholding-v12-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
Copy-Item -LiteralPath (Join-Path $target 'SKSE/Plugins/Wayfarer.dll') -Destination (Join-Path $backup 'Wayfarer.dll')
Copy-Item -LiteralPath (Join-Path $target 'SKSE/Plugins/Wayfarer.ini') -Destination (Join-Path $backup 'Wayfarer.ini')
Copy-Item -LiteralPath (Join-Path $target 'meshes/OpenAnimationReplacer/Walk With Me Signals') -Destination (Join-Path $backup 'Walk With Me Signals') -Recurse
$written = @{}
foreach ($entry in $manifest.files.PSObject.Properties) {
    $relative=$entry.Name.Replace('/','\')
    $source=Join-Path $staging $relative
    $output=[IO.Path]::GetFullPath((Join-Path $target $relative))
    if (-not $output.StartsWith($target+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Update path escaped installation' }
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw "Staging hash mismatch: $relative" }
    if (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { throw "Skyrim reopened; stop installation. Backup: $backup" }
    New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $output -Force
    if ((Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw "Installed hash mismatch: $relative" }
    $written[$relative]=$entry.Value
}
foreach ($relative in $before.Keys) {
    if (-not $written.ContainsKey($relative)) {
        if ((Get-FileHash -LiteralPath (Join-Path $target $relative) -Algorithm SHA256).Hash.ToLowerInvariant() -ne $before[$relative]) { throw "Unexpected change to $relative" }
    }
}
$receipt=@{ destination=$target; backup=$backup; files=$written; preservedFiles=$before.Count-($before.Keys | Where-Object {$written.ContainsKey($_)}).Count; time=(Get-Date -Format o) }
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backup 'install.json') -Encoding utf8
$receipt | ConvertTo-Json -Depth 5
