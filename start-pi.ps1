#Requires -Version 5.1
[CmdletBinding()]
param(
    [string]$Root = '',
    [ValidateSet('coding','seep','apk','exe','all')][string]$Mode = 'coding',
    [string]$Project = '',
    [string[]]$PiArgs = @()
)
. (Join-Path $PSScriptRoot 'scripts\common.ps1')
$workbenchArgs = @('start-pi', '--pi-mode', $Mode)
if ($Root) { $workbenchArgs += @('--root', $Root) }
if ($Project) { $workbenchArgs += @('--project', $Project) }
if ($PiArgs.Count) { $workbenchArgs += '--'; $workbenchArgs += $PiArgs }
Invoke-Workbench -Arguments $workbenchArgs
