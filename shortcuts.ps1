#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root = (Join-Path $env:LOCALAPPDATA 'DSH-Windows-Workbench'))
$ErrorActionPreference = 'Stop'
$active = Join-Path $Root 'active.json'
if (-not (Test-Path -LiteralPath $active)) { throw 'Install the workbench first.' }
$state = Get-Content -LiteralPath $active -Raw -Encoding UTF8 | ConvertFrom-Json
$desktopDirectory = [Environment]::GetFolderPath('Desktop')
$shell = New-Object -ComObject WScript.Shell
$entries = @($state.profiles | ForEach-Object { @{ Label = "DSH Workbench $_"; Script = "start-$_.ps1" } })
if ($state.modules -contains 'pi') {
    $entries += @{ Label = 'PI Coding'; Script = 'start-pi.ps1' }
    foreach ($module in @('seep','apk','exe')) {
        if ($state.modules -contains $module) {
            $entries += @{ Label = "PI Workbench $module"; Script = "start-$module.ps1" }
        }
    }
}
foreach ($entry in $entries) {
    $file = Join-Path $desktopDirectory ($entry.Label + '.lnk')
    if (Test-Path -LiteralPath $file) { Write-Host "Shortcut exists; retained: $file"; continue }
    $shortcut = $shell.CreateShortcut($file)
    $shortcut.TargetPath = (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe')
    $shortcut.Arguments = '-NoProfile -ExecutionPolicy Bypass -File "' + (Join-Path $PSScriptRoot $entry.Script) + '" -Root "' + $Root + '"'
    $shortcut.WorkingDirectory = $PSScriptRoot
    $shortcut.Save()
    Write-Host "Created: $file"
}
