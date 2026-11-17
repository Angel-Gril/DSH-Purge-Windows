#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root = '', [ValidateSet('web','desktop')][string]$Surface = 'web',
      [ValidateSet('status','apply','revert','host-status','selfcheck')][string]$Action = 'status')
. (Join-Path $PSScriptRoot 'scripts\common.ps1')
$workbenchArgs = @('purge', '--surface', $Surface, '--purge-action', $Action)
if ($Root) { $workbenchArgs += @('--root', $Root) }
Invoke-Workbench -Arguments $workbenchArgs
