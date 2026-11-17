#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root = '', [string]$Project = '', [string[]]$PiArgs = @())
& (Join-Path $PSScriptRoot 'start-pi.ps1') -Root $Root -Mode exe -Project $Project -PiArgs $PiArgs
