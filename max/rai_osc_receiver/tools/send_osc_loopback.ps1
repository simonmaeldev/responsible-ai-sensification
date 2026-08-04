[CmdletBinding()]
param(
    [string]$HostName = "127.0.0.1",
    [ValidateRange(1, 65535)]
    [int]$Port = 9000,
    [ValidateRange(0, 5000)]
    [int]$DelayMilliseconds = 30,
    [string]$OscQueryUrl = "http://127.0.0.1:5679/"
)

$ErrorActionPreference = "Stop"

function New-OscArgument {
    param(
        [Parameter(Mandatory = $true)]
        [ValidateSet("s", "i", "f")]
        [string]$Type,
        [Parameter(Mandatory = $true)]
        $Value
    )
    [pscustomobject]@{ Type = $Type; Value = $Value }
}

function Add-OscString {
    param(
        [System.Collections.Generic.List[byte]]$Buffer,
        [string]$Value
    )
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Value)
    $Buffer.AddRange($bytes)
    $Buffer.Add(0)
    while (($Buffer.Count % 4) -ne 0) {
        $Buffer.Add(0)
    }
}

function Add-OscInt32 {
    param(
        [System.Collections.Generic.List[byte]]$Buffer,
        [int]$Value
    )
    $bytes = [System.BitConverter]::GetBytes($Value)
    if ([System.BitConverter]::IsLittleEndian) {
        [Array]::Reverse($bytes)
    }
    $Buffer.AddRange($bytes)
}

function Add-OscFloat32 {
    param(
        [System.Collections.Generic.List[byte]]$Buffer,
        [single]$Value
    )
    $bytes = [System.BitConverter]::GetBytes($Value)
    if ([System.BitConverter]::IsLittleEndian) {
        [Array]::Reverse($bytes)
    }
    $Buffer.AddRange($bytes)
}

function New-OscPacket {
    param(
        [string]$Address,
        [object[]]$Arguments
    )
    $buffer = New-Object 'System.Collections.Generic.List[byte]'
    Add-OscString -Buffer $buffer -Value $Address
    Add-OscString -Buffer $buffer -Value ("," + (($Arguments | ForEach-Object { $_.Type }) -join ""))
    foreach ($argument in $Arguments) {
        switch ($argument.Type) {
            "s" { Add-OscString -Buffer $buffer -Value ([string]$argument.Value) }
            "i" { Add-OscInt32 -Buffer $buffer -Value ([int]$argument.Value) }
            "f" { Add-OscFloat32 -Buffer $buffer -Value ([single]$argument.Value) }
        }
    }
    $buffer.ToArray()
}

$client = New-Object System.Net.Sockets.UdpClient
$client.Connect($HostName, $Port)

function Send-OscMessage {
    param(
        [string]$Address,
        [object[]]$Arguments
    )
    $packet = New-OscPacket -Address $Address -Arguments $Arguments
    [void]$client.Send($packet, $packet.Length)
    Write-Host ("sent {0} ({1} bytes)" -f $Address, $packet.Length)
    if ($DelayMilliseconds -gt 0) {
        Start-Sleep -Milliseconds $DelayMilliseconds
    }
}

function Show-OscQuerySnapshot {
    param([string]$Stage)
    Start-Sleep -Milliseconds 200
    Write-Host ("--- OSCQuery snapshot: {0} ---" -f $Stage)
    try {
        $snapshot = Invoke-RestMethod -Uri $OscQueryUrl -Method Get
        $snapshot | ConvertTo-Json -Depth 30
    }
    catch {
        Write-Warning ("OSCQuery snapshot unavailable: {0}" -f $_.Exception.Message)
    }
}

$runId = "windows-loopback-v1"
$sequence = 1

try {
    Send-OscMessage "/rai/v1/run/start" @(
        (New-OscArgument s $runId),
        (New-OscArgument i 120),
        (New-OscArgument s "timed")
    )
    Send-OscMessage "/rai/v1/control/bpm" @((New-OscArgument i 120))
    Send-OscMessage "/rai/v1/control/mode" @((New-OscArgument s "timed"))
    Send-OscMessage "/rai/v1/control/loop" @((New-OscArgument i 0))
    Send-OscMessage "/rai/v1/control/tonality_enabled" @((New-OscArgument i 1))
    Send-OscMessage "/rai/v1/control/prompt_influence" @((New-OscArgument f ([single]0.25)))
    Send-OscMessage "/rai/v1/control/tonality_pitch_bias" @((New-OscArgument f ([single]0.5)))

    Send-OscMessage "/rai/v1/token" @(
        (New-OscArgument s $runId),
        (New-OscArgument i $sequence),
        (New-OscArgument i 4242),
        (New-OscArgument s "loopback token"),
        (New-OscArgument i 17)
    )
    Send-OscMessage "/rai/v1/note" @(
        (New-OscArgument s $runId),
        (New-OscArgument i $sequence),
        (New-OscArgument i 0),
        (New-OscArgument i 12345),
        (New-OscArgument f ([single]330.25)),
        (New-OscArgument f ([single]0.75)),
        (New-OscArgument i 2),
        (New-OscArgument s "pad")
    )
    Send-OscMessage "/rai/v1/note" @(
        (New-OscArgument s $runId),
        (New-OscArgument i $sequence),
        (New-OscArgument i 1),
        (New-OscArgument i 54321),
        (New-OscArgument f ([single]445.125)),
        (New-OscArgument f ([single]0.5)),
        (New-OscArgument i 7),
        (New-OscArgument s "bell")
    )
    Send-OscMessage "/rai/v1/tonality" @(
        (New-OscArgument s $runId),
        (New-OscArgument i $sequence),
        (New-OscArgument s "liminal amber"),
        (New-OscArgument f ([single]0.875)),
        (New-OscArgument f ([single]0.5))
    )
    Send-OscMessage "/rai/v1/token/end" @(
        (New-OscArgument s $runId),
        (New-OscArgument i $sequence),
        (New-OscArgument i 2)
    )
    Send-OscMessage "/rai/v1/run/done" @((New-OscArgument s $runId))

    Send-OscMessage "/rai/v1/control/bpm" @((New-OscArgument i 96))
    Send-OscMessage "/rai/v1/control/mode" @((New-OscArgument s "sustain"))
    Send-OscMessage "/rai/v1/control/loop" @((New-OscArgument i 1))
    Send-OscMessage "/rai/v1/control/tonality_enabled" @((New-OscArgument i 0))
    Send-OscMessage "/rai/v1/control/prompt_influence" @((New-OscArgument f ([single]0.625)))
    Send-OscMessage "/rai/v1/control/tonality_pitch_bias" @((New-OscArgument f ([single]0.375)))
    Show-OscQuerySnapshot "done (must not release voices)"

    Send-OscMessage "/rai/v1/future/unknown" @((New-OscArgument s "ignore me"))
    Send-OscMessage "/rai/v1/note" @(
        (New-OscArgument s $runId),
        (New-OscArgument i 999)
    )
    Show-OscQuerySnapshot "unknown and malformed input"

    Send-OscMessage "/rai/v1/run/silent" @((New-OscArgument s $runId))
    Show-OscQuerySnapshot "silent (all voices released)"

    Send-OscMessage "/rai/v1/run/stop" @((New-OscArgument s $runId))
    Show-OscQuerySnapshot "stop (all voices released; UDP still listening)"
}
finally {
    $client.Dispose()
}
