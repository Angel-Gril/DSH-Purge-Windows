#Requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$SeepRoot,
      [Parameter(Mandatory=$true)][string]$ToolboxRoot,
      [Parameter(Mandatory=$true)][string]$ComponentsCsv,
      [switch]$CheckOnly)
$ErrorActionPreference = 'Stop'
$components = @($ComponentsCsv -split ',')
$env:SEEP_ANDROID_TOOLBOX = $ToolboxRoot
$env:SEEP_WEB_TOOLBOX = $ToolboxRoot
if (-not $CheckOnly) {
    # In-process array binding is necessary under Windows PowerShell 5.1.
    & (Join-Path $SeepRoot 'setup\install-capabilities.ps1') -Only $components -ToolboxRoot $ToolboxRoot -SkipPath
    # Upstream aggregates optional groups and can return zero after a component failed.
    # Validate only the explicitly selected tools ourselves, below.
}
. (Join-Path $SeepRoot 'Tool\scripts\lib\AndroidToolbox.ps1')
. (Join-Path $SeepRoot 'Tool\scripts\lib\WebToolbox.ps1')
$required = @()
if ($components -contains 'aotopsy') { $required += 'aotopsy' }
if ($components -contains 'android') { $required += @('frida','objection','frida-dexdump','apkid') }
if ($components -contains 'web') { $required += @('ffmpeg','ffprobe') }
if ($components -contains 'scanners') { $required += @('nuclei','ffuf') }
$missing = @()
foreach ($tool in $required | Select-Object -Unique) {
    $found = if ($tool -in @('aotopsy','frida','objection','frida-dexdump','apkid')) {
        Resolve-AndroidTool -Name $tool
    } else { Resolve-WebTool -Name $tool }
    if (-not $found) { $missing += $tool; Write-Host "[MISSING] $tool" }
    else { Write-Host "[FOUND] $tool : $found (run doctor -Deep for capability validation)" }
}
if ($missing.Count) { throw ('Selected tools are missing: ' + ($missing -join ', ')) }
