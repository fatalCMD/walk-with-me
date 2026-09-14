$ErrorActionPreference = 'Stop'
function Assert-GameClosed {
    if (Get-Process SkyrimSE -ErrorAction SilentlyContinue) { throw 'Skyrim must remain closed during installation.' }
}
function Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
Assert-GameClosed
$project = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$mods = (Resolve-Path -LiteralPath (Join-Path $project '../MODS/mods')).Path
$folder = Join-Path $project 'build/gesture-rest-v2'
$manifest = Get-Content -LiteralPath (Join-Path $folder 'update-manifest.json') -Raw | ConvertFrom-Json
$checked = @()
foreach ($entry in $manifest.files) {
    if ($entry.mod -notin @('Wayfarer','Pandora Output')) { throw 'Unexpected mod target' }
    $target = [IO.Path]::GetFullPath((Join-Path (Join-Path $mods $entry.mod) $entry.relative))
    $allowed = (Join-Path $mods $entry.mod) + '\'
    if (-not $target.StartsWith($allowed,[StringComparison]::OrdinalIgnoreCase)) { throw 'Target escaped mod directory' }
    if ((Hash $entry.source) -ne $entry.sha256 -or (Hash $target) -ne $entry.before) { throw "File changed since preparation: $target" }
    $checked += @{ entry=$entry; target=$target }
}
$snapshot = @{}
foreach ($mod in @('Wayfarer','Pandora Output')) {
    foreach ($file in Get-ChildItem -LiteralPath (Join-Path $mods $mod) -File -Recurse) { $snapshot[$file.FullName] = Hash $file.FullName }
}
$backup = Join-Path $project ('backups/installed-pre-gesture-rest-v2-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($item in $checked) {
    $saved = Join-Path (Join-Path $backup $item.entry.mod) $item.entry.relative
    New-Item -ItemType Directory -Path (Split-Path -Parent $saved) -Force | Out-Null
    Copy-Item -LiteralPath $item.target -Destination $saved
    if ((Hash $saved) -ne $item.entry.before) { throw 'Backup hash mismatch' }
    $item.backup=$saved
}
$written = @()
try {
    foreach ($item in $checked) {
        Assert-GameClosed
        Copy-Item -LiteralPath $item.entry.source -Destination $item.target -Force
        $written += $item
        if ((Hash $item.target) -ne $item.entry.sha256) { throw 'Installed hash mismatch' }
    }
    $targets=@($checked | ForEach-Object {$_.target})
    foreach ($path in $snapshot.Keys) {
        if ($path -notin $targets -and (Hash $path) -ne $snapshot[$path]) { throw "Unrelated file changed: $path" }
    }
} catch {
    foreach ($item in $written) { Copy-Item -LiteralPath $item.backup -Destination $item.target -Force }
    throw
}
$receipt=@{installedAt=(Get-Date -Format o); backup=$backup; files=@($checked | ForEach-Object {@{destination=$_.target;backup=$_.backup;before=$_.entry.before;sha256=$_.entry.sha256}}); preservedFiles=$snapshot.Count-$checked.Count; liveGameVerified=$false}
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $folder 'install.json') -Encoding utf8
$receipt | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $backup 'install.json') -Encoding utf8
$receipt | ConvertTo-Json -Depth 6
