param(
    [Parameter(Mandatory=$true)][string]$Url,
    [Parameter(Mandatory=$true)][string]$Dest,
    [Parameter(Mandatory=$true)][string]$Name
)

if (Test-Path $Dest) {
    Remove-Item $Dest -Force -ErrorAction SilentlyContinue
}

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$wc = New-Object System.Net.WebClient
$wc.Headers.Add('User-Agent', 'Mozilla/5.0')

try {
    $wc.OpenRead($Url).Close()
    $total = [int64]$wc.ResponseHeaders['Content-Length']
} catch {
    $total = 0
}

$sw = [System.Diagnostics.Stopwatch]::StartNew()
$script:last = 0

Register-ObjectEvent -InputObject $wc -EventName DownloadProgressChanged -Action {
    $p = $EventArgs.ProgressPercentage
    $rec = $EventArgs.BytesReceived
    $tot = $EventArgs.TotalBytesToReceive
    if ($tot -le 0) { $tot = $total }
    
    $now = $sw.ElapsedMilliseconds
    if ($now - $script:last -ge 150 -or $p -eq 100) {
        $mbRec = ($rec / 1MB).ToString('0.0')
        $mbTot = if ($tot -gt 0) { ($tot / 1MB).ToString('0.0') } else { '???' }
        $spd = if ($now -gt 0) { (($rec / 1KB) / ($now / 1000)).ToString('0') } else { '0' }
        
        $barWidth = 20
        $fill = [int](($p / 100) * $barWidth)
        $bar = '[' + ('=' * $fill) + (' ' * ($barWidth - $fill)) + ']'
        
        Write-Host -NoNewline ('`r  -> {0}: {1} {2,3}% ({3} MB / {4} MB) {5} KB/s   ' -f $Name, $bar, $p, $mbRec, $mbTot, $spd)
        $script:last = $now
    }
} | Out-Null

$wc.DownloadFileAsync((New-Object System.Uri($Url)), $Dest)

while ($wc.IsBusy) {
    Start-Sleep -Milliseconds 50
}

Write-Host ''
if (Test-Path $Dest) {
    exit 0
} else {
    exit 1
}
