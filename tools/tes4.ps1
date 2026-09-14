



param(
    [Parameter(Mandatory=$true)][string]$Path,
    [string]$List = '',
    [string]$Dump = '',
    [string]$Grep = '',
    [string]$OnlyGroup = '',
    [int]$MaxRecords = 400
)

$ErrorActionPreference = 'Stop'
$bytes = [System.IO.File]::ReadAllBytes($Path)
Write-Host "file: $Path ($($bytes.Length) bytes)"

function Get-U32([byte[]]$b, [int]$o) { [BitConverter]::ToUInt32($b, $o) }
function Get-U16([byte[]]$b, [int]$o) { [BitConverter]::ToUInt16($b, $o) }
function Get-Sig([byte[]]$b, [int]$o) { [System.Text.Encoding]::ASCII.GetString($b, $o, 4) }

function Expand-Zlib([byte[]]$data) {
    
    $ms = New-Object System.IO.MemoryStream(,$data[2..($data.Length-1)])
    $ds = New-Object System.IO.Compression.DeflateStream($ms, [System.IO.Compression.CompressionMode]::Decompress)
    $out = New-Object System.IO.MemoryStream
    $ds.CopyTo($out)
    $ds.Dispose(); $ms.Dispose()
    return $out.ToArray()
}

function Get-RecordData([byte[]]$b, [int]$off, [uint32]$dataSize, [uint32]$flags) {
    $payload = $b[($off+24)..($off+24+$dataSize-1)]
    if ($flags -band 0x00040000) {
        $decompSize = [BitConverter]::ToUInt32($payload, 0)
        $comp = $payload[4..($payload.Length-1)]
        try { return Expand-Zlib $comp } catch { Write-Host "  !! inflate failed"; return @() }
    }
    return $payload
}

function Get-Subrecords([byte[]]$data) {
    $subs = @()
    $i = 0
    $carryOver = 0
    while ($i + 6 -le $data.Length) {
        $sig = [System.Text.Encoding]::ASCII.GetString($data, $i, 4)
        $size = [BitConverter]::ToUInt16($data, $i+4)
        $i += 6
        if ($sig -eq 'XXXX') {
            $carryOver = [BitConverter]::ToUInt32($data, $i)
            $i += $size
            continue
        }
        if ($carryOver -gt 0) { $size = $carryOver; $carryOver = 0 }
        if ($i + $size -gt $data.Length) { break }
        $subs += [pscustomobject]@{ Sig = $sig; Size = $size; Offset = $i; Data = $data[$i..($i+[Math]::Max($size,1)-1)] }
        $i += $size
    }
    return $subs
}

function Get-EDID($subs) {
    $e = $subs | Where-Object { $_.Sig -eq 'EDID' } | Select-Object -First 1
    if ($e) { return ([System.Text.Encoding]::ASCII.GetString($e.Data)).TrimEnd([char]0) }
    return ''
}

$records = @()

function Walk([int]$start, [int]$end, [int]$depth) {
    $off = $start
    while ($off + 24 -le $end) {
        $sig = Get-Sig $bytes $off
        if ($sig -eq 'GRUP') {
            $gsize = Get-U32 $bytes ($off+4)
            if ($gsize -lt 24) { break }
            
            $skip = $false
            if ($depth -eq 0 -and $OnlyGroup) {
                $label = Get-Sig $bytes ($off+8)
                if ($label -ne $OnlyGroup) { $skip = $true }
            }
            if (-not $skip) { Walk ($off+24) ($off+$gsize) ($depth+1) }
            $off += $gsize
        } else {
            $dsize = Get-U32 $bytes ($off+4)
            $flags = Get-U32 $bytes ($off+8)
            $formid = Get-U32 $bytes ($off+12)
            $script:records += [pscustomobject]@{ Sig=$sig; Off=$off; DataSize=$dsize; Flags=$flags; FormID=$formid }
            $off += 24 + $dsize
        }
    }
}

Walk 0 $bytes.Length 0
Write-Host "records: $($records.Count)"
Write-Host ("signatures: " + (($records | Group-Object Sig | Sort-Object Count -Descending | ForEach-Object { "$($_.Name)=$($_.Count)" }) -join ' '))

if ($List) {
    $sel = $records | Where-Object { $_.Sig -eq $List } | Select-Object -First $MaxRecords
    Write-Host "`n=== $List records ($($sel.Count)) ==="
    foreach ($r in $sel) {
        $data = Get-RecordData $bytes $r.Off $r.DataSize $r.Flags
        if ($data.Length -eq 0) { continue }
        $subs = Get-Subrecords $data
        $edid = Get-EDID $subs
        if ($Grep -and $edid -notmatch $Grep) { continue }
        Write-Host ("{0:X8}  {1,-52} subs={2}" -f $r.FormID, $edid, $subs.Count)
    }
}

if ($Dump) {
    $target = [Convert]::ToUInt32($Dump, 16)
    $r = $records | Where-Object { $_.FormID -eq $target } | Select-Object -First 1
    if (-not $r) { Write-Host "formid $Dump not found"; exit 1 }
    $data = Get-RecordData $bytes $r.Off $r.DataSize $r.Flags
    $subs = Get-Subrecords $data
    Write-Host "`n=== $($r.Sig) $($Dump) : $(Get-EDID $subs) ($($data.Length) bytes, $($subs.Count) subrecords) ==="
    foreach ($s in $subs) {
        $hex = ($s.Data | Select-Object -First 24 | ForEach-Object { '{0:X2}' -f $_ }) -join ' '
        $txt = ''
        if ($s.Sig -in @('EDID','FULL','ALID','ITXT')) { $txt = '  "' + (([System.Text.Encoding]::ASCII.GetString($s.Data)).TrimEnd([char]0)) + '"' }
        elseif ($s.Size -eq 4) { $txt = '  = 0x{0:X8}' -f ([BitConverter]::ToUInt32($s.Data,0)) }
        Write-Host ("  {0} [{1,5}] {2}{3}" -f $s.Sig, $s.Size, $hex, $txt)
    }
}
