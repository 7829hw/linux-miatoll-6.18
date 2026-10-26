param(
    [string]$Fastboot = 'fastboot',
    [string]$Port = '',
    [switch]$CaptureOnly
)
& (Join-Path $PSScriptRoot 'Test-Boot1.ps1') -Fastboot $Fastboot -Port $Port -CaptureOnly:$CaptureOnly -ReportName 'display1-report.json'
