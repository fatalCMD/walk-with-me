param([string]$Destination = "$PSScriptRoot\..\MODS\mods\Wayfarer")
$ErrorActionPreference = 'Stop'
if (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { throw 'Close Skyrim before replacing the DLL and scripts.' }
$source = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'package')).Path
$target = (Resolve-Path -LiteralPath $Destination).Path
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = Join-Path $PSScriptRoot "backups\installed-pre-update-$stamp"
Copy-Item -LiteralPath $target -Destination $backup -Recurse


foreach ($legacy in @('Interface\Wayfarer','Interface\WalkWithMe','SKSE\Plugins\Fonts\WayfarerInscription.ttf','docs')) {
    $old = Join-Path $target $legacy
    if (Test-Path -LiteralPath $old) {
        $resolved = (Resolve-Path -LiteralPath $old).Path
        if (-not $resolved.StartsWith($target + '\',[StringComparison]::OrdinalIgnoreCase)) { throw 'Retired path escaped the mod directory' }
        $retired = Join-Path $backup ('retired\' + $legacy)
        New-Item -ItemType Directory -Path (Split-Path -Parent $retired) -Force | Out-Null
        Move-Item -LiteralPath $resolved -Destination $retired
    }
}
foreach ($file in Get-ChildItem -LiteralPath $source -File -Recurse) {
    $relative = $file.FullName.Substring($source.Length + 1)
    if ($file.Extension -eq '.bak') { continue }
    $output = Join-Path $target $relative
    
    if ($relative -eq 'SKSE\Plugins\Wayfarer.ini' -and (Test-Path -LiteralPath $output)) { continue }
    New-Item -ItemType Directory -Path (Split-Path -Parent $output) -Force | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $output -Force
    if ((Get-FileHash -LiteralPath $file.FullName).Hash -ne (Get-FileHash -LiteralPath $output).Hash) {
        throw "Deployed file failed hash verification: $relative. Backup: $backup"
    }
}
Write-Output "Installed and hash-verified: $target"
Write-Output "Previous installation preserved: $backup"
