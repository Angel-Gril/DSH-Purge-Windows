#Requires -Version 5.1
[CmdletBinding()]
param([string]$Root = '', [switch]$ApplyPurge, [switch]$SkipGitPull)
. (Join-Path $PSScriptRoot 'scripts\common.ps1')
if (-not $SkipGitPull) {
    Assert-WorkbenchGitCheckout -Directory $PSScriptRoot
    $changes = & git -C $PSScriptRoot status --porcelain
    if ($LASTEXITCODE -ne 0 -or $changes) { throw 'Workbench repository must be clean before update.' }
    & git -C $PSScriptRoot pull --ff-only
    if ($LASTEXITCODE -ne 0) { throw 'git pull failed. Installation was not changed.' }
}
$workbenchArgs = @('install')
if ($Root) { $workbenchArgs += @('--root', $Root) }
$stateRoot = if ($Root) { $Root } else { Join-Path $env:LOCALAPPDATA 'DSH-Windows-Workbench' }
$active = Join-Path $stateRoot 'active.json'
if (-not (Test-Path -LiteralPath $active)) { throw 'No existing deployment. Run install.ps1 first.' }
$state = Get-Content -LiteralPath $active -Raw -Encoding UTF8 | ConvertFrom-Json
if ($state.profiles -notcontains 'desktop') { $workbenchArgs += '--web-only' }
if ($state.desktopExe) { $workbenchArgs += @('--desktop-exe', [string]$state.desktopExe) }
if ($state.options.with_ida) { $workbenchArgs += '--with-ida' }
if ($state.options.with_playwright) { $workbenchArgs += '--with-playwright' }
if ($ApplyPurge) { $workbenchArgs += '--apply-purge' }
Invoke-Workbench -Arguments $workbenchArgs
