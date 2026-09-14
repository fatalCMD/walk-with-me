param([string]$Destination = (Join-Path $PSScriptRoot '../../MODS/mods/Wayfarer'))
$ErrorActionPreference = 'Stop'
if (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { throw 'Save and close Skyrim before installing; its old DLL is still loaded.' }
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$target = (Resolve-Path -LiteralPath $Destination).Path
$staging = (Resolve-Path -LiteralPath (Join-Path $projectRoot 'build/follower-dialogue-update')).Path
$manifest = Get-Content -LiteralPath (Join-Path $staging 'update-manifest.json') -Raw | ConvertFrom-Json
$entries = @($manifest.files.PSObject.Properties | Sort-Object @{Expression={if ($_.Name.EndsWith('.dll')) {1} else {0}}}, Name)

foreach ($entry in $entries) {
    $relative=$entry.Name.Replace('/','\')
    $source=[IO.Path]::GetFullPath((Join-Path $staging $relative))
    $output=[IO.Path]::GetFullPath((Join-Path $target $relative))
    if (-not $source.StartsWith($staging+'\',[StringComparison]::OrdinalIgnoreCase) -or
        -not $output.StartsWith($target+'\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Manifest path escaped the update directory' }
    if ($relative -eq 'SKSE\Plugins\Wayfarer.ini') { throw 'This update must preserve the installed settings' }
    if ((Get-FileHash -LiteralPath $source -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw "Staging hash mismatch: $relative" }
}
$backup = Join-Path $projectRoot ('backups/installed-pre-follower-dialogue-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
$ini=Join-Path $target 'SKSE/Plugins/Wayfarer.ini'
$iniHash=if(Test-Path -LiteralPath $ini){(Get-FileHash -LiteralPath $ini).Hash}else{$null}
if($iniHash){Copy-Item -LiteralPath $ini -Destination (Join-Path $backup 'Wayfarer.ini')}
$written=@{}
foreach ($entry in $entries) {
    if (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { throw "Skyrim reopened; installation stopped. Backup: $backup" }
    $relative=$entry.Name.Replace('/','\')
    $source=Join-Path $staging $relative
    $output=Join-Path $target $relative
    if (Test-Path -LiteralPath $output) {
        $prior=Join-Path $backup $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $prior) -Force | Out-Null
        Copy-Item -LiteralPath $output -Destination $prior
    }
    New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force | Out-Null
    Copy-Item -LiteralPath $source -Destination $output -Force
    if ((Get-FileHash -LiteralPath $output -Algorithm SHA256).Hash.ToLowerInvariant() -ne $entry.Value) { throw "Installed hash mismatch: $relative. Backup: $backup" }
    $written[$relative]=$entry.Value
}
if($iniHash -and (Get-FileHash -LiteralPath $ini).Hash -ne $iniHash){throw 'Installed settings changed unexpectedly'}
$receipt=@{destination=$target;backup=$backup;files=$written;settingsPreserved=$true;time=(Get-Date -Format o)}
$receipt | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backup 'install.json') -Encoding utf8
$receipt | ConvertTo-Json -Depth 5
