#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\scripts\common.ps1')
$errorsFound = @()
$repoRoot = Split-Path $PSScriptRoot -Parent
foreach ($file in Get-ChildItem -LiteralPath $repoRoot -Recurse -Filter '*.ps1' | Where-Object { $_.FullName -notlike '*node_modules*' -and $_.FullName -notlike '*\.workbench\*' }) {
    $tokens = $null
    $parseErrors = $null
    [System.Management.Automation.Language.Parser]::ParseFile($file.FullName, [ref]$tokens, [ref]$parseErrors) | Out-Null
    $errorsFound += $parseErrors
}
if ($errorsFound.Count) { throw ($errorsFound | Out-String) }
& (Join-Path $PSScriptRoot 'git-boundaries.ps1')
$pythonExe = Get-WorkbenchPython
$env:PYTHONIOENCODING = 'utf-8'
& $pythonExe -m unittest discover -s (Join-Path $PSScriptRoot '.') -p 'test_*.py' -v
if ($LASTEXITCODE -ne 0) { throw 'Python tests failed.' }
& node --test (Join-Path $PSScriptRoot 'pi-workbench.test.mjs')
if ($LASTEXITCODE -ne 0) { throw 'PI extension tests failed.' }
Write-Host 'PowerShell syntax and workbench regression tests passed.'
