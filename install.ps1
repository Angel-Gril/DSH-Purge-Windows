#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Root = '',
    [string]$DshHome = '',
    [string]$DesktopExe = '',
    [switch]$InstallDesktop,
    [switch]$WebOnly,
    [switch]$ApplyPurge,
    [switch]$InstallCapabilities,
    [switch]$WithIda,
    [switch]$WithPlaywright
)
. (Join-Path $PSScriptRoot 'scripts\common.ps1')
$workbenchArgs = @('install')
if ($Root) { $workbenchArgs += @('--root', $Root) }
if ($DshHome) { $workbenchArgs += @('--dsh-home', $DshHome) }
if ($DesktopExe) { $workbenchArgs += @('--desktop-exe', $DesktopExe) }
if ($InstallDesktop) { $workbenchArgs += '--install-desktop' }
if ($WebOnly) { $workbenchArgs += '--web-only' }
if ($ApplyPurge) { $workbenchArgs += '--apply-purge' }
if ($WithIda) { $workbenchArgs += '--with-ida' }
if ($WithPlaywright) { $workbenchArgs += '--with-playwright' }
Invoke-Workbench -Arguments $workbenchArgs
if ($InstallCapabilities) {
    $capabilityParameters = @{ Components = 'all' }
    if ($Root) { $capabilityParameters.Root = $Root }
    & (Join-Path $PSScriptRoot 'capabilities.ps1') @capabilityParameters
}
