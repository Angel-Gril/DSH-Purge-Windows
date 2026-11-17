#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root = '',
      [ValidateSet('aotopsy','web','android','scanners','all')][string[]]$Components = @('aotopsy'),
      [switch]$CheckOnly)
. (Join-Path $PSScriptRoot 'scripts\common.ps1')
$workbenchArgs = @('capabilities', '--components', ($Components -join ','))
if ($Root) { $workbenchArgs += @('--root', $Root) }
if ($CheckOnly) { $workbenchArgs += '--check-only' }
Invoke-Workbench -Arguments $workbenchArgs
