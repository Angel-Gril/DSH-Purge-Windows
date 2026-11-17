#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root = '', [string]$Snapshot = '', [switch]$RevertPurge)
. (Join-Path $PSScriptRoot 'scripts\common.ps1')
$workbenchArgs = @('rollback')
if ($Root) { $workbenchArgs += @('--root', $Root) }
if ($Snapshot) { $workbenchArgs += @('--snapshot', $Snapshot) }
if ($RevertPurge) { $workbenchArgs += '--revert-purge' }
Invoke-Workbench -Arguments $workbenchArgs
