#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root = '', [string[]]$AppArgs = @())
. (Join-Path $PSScriptRoot 'scripts\common.ps1')
$workbenchArgs = @('start', '--surface', 'web')
if ($Root) { $workbenchArgs += @('--root', $Root) }
if ($AppArgs.Count) { $workbenchArgs += '--'; $workbenchArgs += $AppArgs }
Invoke-Workbench -Arguments $workbenchArgs
