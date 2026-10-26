param(
    [string]$Fastboot = 'fastboot',
    [string]$Port = '',
    [switch]$CaptureOnly,
    [string]$ReportName = 'boot1-report.json'
)
$ErrorActionPreference = 'Stop'
$bootReport = Get-Content -LiteralPath (Join-Path $PSScriptRoot $ReportName) -Raw -Encoding UTF8 | ConvertFrom-Json
$bootImage = Join-Path $PSScriptRoot $bootReport.image
$testName = 'boot1'
$probeCommand = 'boot-probe'
$probeEnd = 'BOOT1_PROBE_END'
if ($bootReport.boot_profile -match '^(display[12])-ram-only$') {
    $testName = $Matches[1]
    $probeCommand = 'display-probe'
    $probeEnd = $testName.ToUpperInvariant() + '_PROBE_END'
} elseif ($bootReport.boot_profile -ne 'boot1-ram-only') {
    throw 'Unknown RAM boot profile.'
}
$bootHash = (Get-FileHash -LiteralPath $bootImage -Algorithm SHA256).Hash.ToLowerInvariant()
if ($bootHash -ne $bootReport.image_sha256) { throw 'Image SHA256 does not match the report.' }
$fastbootExe = $null
if (-not $CaptureOnly) { $fastbootExe = (Get-Command $Fastboot -ErrorAction Stop).Source }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$fastbootLog = Join-Path $PSScriptRoot "$testName-fastboot-$stamp.txt"
$serialLog = Join-Path $PSScriptRoot "$testName-serial-$stamp.txt"

function Invoke-Boot1Fastboot([string[]]$CommandArguments) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $commandOutput = & $fastbootExe @CommandArguments 2>&1
        $commandExit = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    $commandText = ($commandOutput | ForEach-Object { $_.ToString() }) -join "`n"
    Add-Content -LiteralPath $fastbootLog -Value (('fastboot ' + ($CommandArguments -join ' ')) + "`n" + $commandText) -Encoding UTF8
    Write-Host $commandText
    if ($commandExit -ne 0) { throw "fastboot failed ($commandExit). No automatic boot retry. Log: $fastbootLog" }
    return $commandText
}

if (-not $CaptureOnly) {
$deviceOutput = Invoke-Boot1Fastboot -CommandArguments @('devices')
$deviceEntries = [regex]::Matches($deviceOutput, '(?m)^(\S+)\s+fastboot\s*$')
if ($deviceEntries.Count -ne 1) { throw 'Connect exactly one curtana in bootloader fastboot mode (Power + Volume Down).' }
$deviceSerial = $deviceEntries[0].Groups[1].Value
$productOutput = Invoke-Boot1Fastboot -CommandArguments @('-s', $deviceSerial, 'getvar', 'product')
if ($productOutput -notmatch 'product:\s*curtana\b') { throw 'Expected product curtana. Keep the log and stop here.' }

# Start a fresh bootloader session; this command does not flash a partition.
Write-Host 'Restarting the bootloader for a fresh Fastboot session. No partition is written.'
$null = Invoke-Boot1Fastboot -CommandArguments @('-s', $deviceSerial, 'reboot', 'bootloader')
$reconnectDeadline = [DateTime]::UtcNow.AddSeconds(40)
do {
    Start-Sleep -Seconds 2
    $deviceOutput = Invoke-Boot1Fastboot -CommandArguments @('devices')
    $reconnected = $deviceOutput -match ('(?m)^' + [regex]::Escape($deviceSerial) + '\s+fastboot\s*$')
} while (-not $reconnected -and [DateTime]::UtcNow -lt $reconnectDeadline)
if (-not $reconnected) { throw "Bootloader did not reconnect. Log: $fastbootLog" }

# Exactly one RAM boot request. No flash, erase, format, unlock or set_active.
Write-Host 'Sending the image once with fastboot boot for RAM execution. This does not flash it.'
$null = Invoke-Boot1Fastboot -CommandArguments @('-s', $deviceSerial, 'boot', $bootImage)
}
Write-Host 'Waiting for the Linux USB serial device...'
$portDeadline = [DateTime]::UtcNow.AddSeconds(100)
while (-not $Port -and [DateTime]::UtcNow -lt $portDeadline) {
    $serialDevices = @(Get-CimInstance Win32_SerialPort | Where-Object { $_.PNPDeviceID -match 'VID_1D6B&PID_0104' })
    if ($serialDevices.Count -eq 1) { $Port = $serialDevices[0].DeviceID; break }
    if ($serialDevices.Count -gt 1) { throw 'Multiple Linux COM ports; rerun only a serial capture with the correct port, not another boot request.' }
    Start-Sleep -Seconds 1
}
if (-not $Port) { throw "No Linux COM port after 100 seconds. Record the screen and return $fastbootLog. Do not resend the image in this session." }

$serialConnection = [System.IO.Ports.SerialPort]::new($Port, 115200, [System.IO.Ports.Parity]::None, 8, [System.IO.Ports.StopBits]::One)
$serialConnection.NewLine = "`n"
$serialConnection.DtrEnable = $true
$serialConnection.RtsEnable = $true
$serialConnection.WriteTimeout = 3000
$capturedText = ''
try {
    $serialConnection.Open()
    Start-Sleep -Seconds 2
    $serialConnection.WriteLine('')
    $serialConnection.WriteLine('uname -r')
    $serialConnection.WriteLine($probeCommand)
    # The first tested RAMdisk omitted /bin/dmesg; BusyBox contains the applet.
    # This also works with that already running image, without another boot.
    $serialConnection.WriteLine('/bin/busybox dmesg; printf "\nBOOT1_KERNELLOG_EXIT=%s\n" "$?"')
    $captureDeadline = [DateTime]::UtcNow.AddSeconds(90)
    while ([DateTime]::UtcNow -lt $captureDeadline) {
        $chunk = $serialConnection.ReadExisting()
        if ($chunk.Length -gt 0) {
            $capturedText += $chunk
            [System.IO.File]::AppendAllText($serialLog, $chunk, [System.Text.Encoding]::UTF8)
        }
        # Match a result line, never the command echoed by the interactive shell.
        if ($capturedText -match '(?m)^BOOT1_KERNELLOG_EXIT=\d+\r?$') { break }
        if ($capturedText.Length -gt 8388608) { throw 'Serial output exceeded 8 MiB; keep the captured log.' }
        Start-Sleep -Milliseconds 200
    }
} finally {
    if ($serialConnection.IsOpen) { $serialConnection.Close() }
    $serialConnection.Dispose()
}
$releasePattern = [regex]::Escape($bootReport.kernel_release)
if ($capturedText -match $releasePattern -and $capturedText.Contains($bootReport.boot_profile) -and $capturedText.Contains($probeEnd)) {
    if ($testName -match '^display[12]$') {
        $captureTag = $testName.ToUpperInvariant() + '_LOG_CAPTURED'
        Write-Host "${captureTag}: $($bootReport.kernel_release) reached the USB shell. Report whether the screen shows the test banner."
    } else {
        Write-Host "BOOT1_CONFIRMED: $($bootReport.kernel_release) reached a RAM userspace and USB shell."
    }
} else {
    Write-Host 'Boot is not confirmed. Return the logs for inspection.'
}
if ($capturedText -match '(?m)^BOOT1_KERNELLOG_EXIT=0\r?$') {
    Write-Host 'Kernel log collected using the BusyBox dmesg applet.'
} else {
    Write-Host 'Kernel log collection is incomplete; boot confirmation above is separate.'
}
if (Test-Path -LiteralPath $fastbootLog) { Write-Host "Fastboot log: $fastbootLog" }
Write-Host "Serial log: $serialLog"
Write-Host 'The installed OS was not flashed. Hold Power to leave this RAM session when finished.'
