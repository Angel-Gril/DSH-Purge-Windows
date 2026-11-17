#Requires -Version 5.1
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$OutputZip)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts\common.ps1')
Assert-WorkbenchGitCheckout -Directory $PSScriptRoot
$resolved = [System.IO.Path]::GetFullPath($OutputZip)
if ((Test-Path -LiteralPath $resolved)) { throw 'Output already exists; choose a new archive path.' }
& git -C $PSScriptRoot archive --format=zip "--output=$resolved" HEAD
if ($LASTEXITCODE -ne 0) { throw 'git archive failed. Make a reviewed commit first.' }
Write-Host "Packaged committed workbench scripts only: $resolved"
Write-Host 'Source checkouts, tools, secrets and offline npm/pip dependencies are not included.'
