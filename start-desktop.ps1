#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root = '')
. (Join-Path $PSScriptRoot 'scripts\common.ps1')
$workbenchArgs = @('start', '--surface', 'desktop')
if ($Root) { $workbenchArgs += @('--root', $Root) }
Invoke-Workbench -Arguments $workbenchArgs
