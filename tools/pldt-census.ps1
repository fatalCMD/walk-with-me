

param([Parameter(Mandatory=$true)][string]$Path)

$ErrorActionPreference = 'Stop'
$bytes = [System.IO.File]::ReadAllBytes($Path)

function Get-U32([byte[]]$b,[int]$o){ [BitConverter]::ToUInt32($b,$o) }
function Get-Sig([byte[]]$b,[int]$o){ [System.Text.Encoding]::ASCII.GetString($b,$o,4) }

function Expand-Zlib([byte[]]$data){
    $ms = New-Object System.IO.MemoryStream(,$data[2..($data.Length-1)])
    $ds = New-Object System.IO.Compression.DeflateStream($ms,[System.IO.Compression.CompressionMode]::Decompress)
    $out = New-Object System.IO.MemoryStream
    $ds.CopyTo($out); $ds.Dispose(); $ms.Dispose(); return $out.ToArray()
}

$recs = @()
function Walk([int]$start,[int]$end,[int]$depth){
    $off=$start
    while($off+24 -le $end){
        $sig = Get-Sig $bytes $off
        if($sig -eq 'GRUP'){
            $g = Get-U32 $bytes ($off+4); if($g -lt 24){break}
            $skip=$false
            if($depth -eq 0){ if((Get-Sig $bytes ($off+8)) -ne 'PACK'){$skip=$true} }
            if(-not $skip){ Walk ($off+24) ($off+$g) ($depth+1) }
            $off += $g
        } else {
            $d = Get-U32 $bytes ($off+4)
            $script:recs += ,@($off,$d,(Get-U32 $bytes ($off+8)))
            $off += 24 + $d
        }
    }
}
Walk 0 $bytes.Length 0
Write-Host "PACK records: $($recs.Count)"

$byType = @{}
foreach($r in $recs){
    $off=$r[0]; $dsize=$r[1]; $flags=$r[2]
    $payload = $bytes[($off+24)..($off+24+$dsize-1)]
    if($flags -band 0x00040000){ try{ $payload = Expand-Zlib $payload[4..($payload.Length-1)] }catch{ continue } }
    $i=0
    while($i+6 -le $payload.Length){
        $sig=[System.Text.Encoding]::ASCII.GetString($payload,$i,4)
        $size=[BitConverter]::ToUInt16($payload,$i+4)
        $i+=6
        if($i+$size -gt $payload.Length){break}
        if($sig -eq 'PLDT' -and $size -ge 12){
            $t=[BitConverter]::ToInt32($payload,$i)
            $v=[BitConverter]::ToUInt32($payload,$i+4)
            if(-not $byType.ContainsKey($t)){ $byType[$t]=@{Count=0;Samples=@()} }
            $byType[$t].Count++
            if($byType[$t].Samples.Count -lt 12 -and $byType[$t].Samples -notcontains $v){ $byType[$t].Samples += $v }
        }
        $i+=$size
    }
}

Write-Host "`n=== PLDT target types observed ==="
foreach($k in ($byType.Keys | Sort-Object)){
    $s = ($byType[$k].Samples | ForEach-Object { '0x{0:X}' -f $_ }) -join ', '
    Write-Host ("type {0,2}  count={1,-6} values: {2}" -f $k, $byType[$k].Count, $s)
}
