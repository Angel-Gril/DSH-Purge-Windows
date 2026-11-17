#Requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$Link,
      [Parameter(Mandatory=$true)][string]$Target)
$ErrorActionPreference = 'Stop'
if (Test-Path -LiteralPath $Link) { throw 'Dependency link already exists; retained.' }
if (-not (Test-Path -LiteralPath $Target -PathType Container)) { throw 'Managed dependency target is missing.' }
New-Item -ItemType Junction -Path $Link -Target $Target | Out-Null
