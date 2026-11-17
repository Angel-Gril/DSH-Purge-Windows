#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root = '', [switch]$ProbeMcp, [switch]$Deep)
. (Join-Path $PSScriptRoot 'scripts\common.ps1')
$workbenchArgs = @('doctor')
if ($Root) { $workbenchArgs += @('--root', $Root) }
if ($ProbeMcp) { $workbenchArgs += '--probe-mcp' }
if ($Deep) { $workbenchArgs += '--deep' }
Invoke-Workbench -Arguments $workbenchArgs
