#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root = (Join-Path $env:LOCALAPPDATA 'DSH-Windows-Workbench'))
$ErrorActionPreference = 'Stop'
$active = Join-Path $Root 'active.json'
if (-not (Test-Path -LiteralPath $active)) { throw 'Install the workbench first.' }
$state = Get-Content -LiteralPath $active -Raw -Encoding UTF8 | ConvertFrom-Json
$desktopDirectory = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
foreach ($surface in $state.profiles) {
    $file = Join-Path $desktopDirectory "DSH Workbench $surface.lnk"
    if (Test-Path -LiteralPath $file) { throw "Shortcut exists; retained: $file" }
    $shortcut = $shell.CreateShortcut($file)
    $shortcut.TargetPath = (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe')
    $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $PSScriptRoot "start-$surface.ps1") + '" -Root "' + $Root + '"'
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Save()
    Write-Host "Created: $file"
}
