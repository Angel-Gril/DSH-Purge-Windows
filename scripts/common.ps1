#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
try {
    [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
    $OutputEncoding = [Console]::OutputEncoding
} catch { }
function Get-WorkbenchPython {
    $candidates = @()
    if ($env:WORKBENCH_PYTHON) { $candidates += $env:WORKBENCH_PYTHON }
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($pythonCommand) { $candidates += $pythonCommand.Source }
    if ($env:LOCALAPPDATA) {
        $candidates += @(Get-ChildItem -Path (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python*\python.exe') -ErrorAction SilentlyContinue | Sort-Object FullName -Descending | ForEach-Object FullName)
    }
    foreach ($candidate in $candidates | Select-Object -Unique) {
        if ($candidate -like '*WindowsApps*') { continue }
        $resolved = & $candidate -c 'import sys; print(sys.executable); sys.exit(0 if sys.version_info >= (3,11) else 1)' 2>$null
        if ($LASTEXITCODE -eq 0 -and $resolved) { return [string]$resolved }
    }
    throw 'Python 3.11+ is required. Install Python, reopen PowerShell, or set WORKBENCH_PYTHON.'
}
function Invoke-Workbench {
    param([string[]]$Arguments)
    $pythonExe = Get-WorkbenchPython
    $previousEncoding = $env:PYTHONIOENCODING
    try {
        $env:PYTHONIOENCODING = 'utf-8'
        & $pythonExe -u (Join-Path $PSScriptRoot 'workbench.py') @Arguments
        if ($LASTEXITCODE -ne 0) { throw "Workbench failed (exit $LASTEXITCODE)." }
    } finally { $env:PYTHONIOENCODING = $previousEncoding }
}
function Assert-WorkbenchGitCheckout {
    param([Parameter(Mandatory=$true)][string]$Directory)
    $top = & git -C $Directory rev-parse --show-toplevel 2>$null
    if ($LASTEXITCODE -ne 0 -or -not $top -or
        [IO.Path]::GetFullPath([string]$top).TrimEnd('\','/') -ne [IO.Path]::GetFullPath($Directory).TrimEnd('\','/')) {
        throw 'This folder needs its own workbench Git checkout; a parent repository will not be used. Clone DSH-Purge-Windows first.'
    }
    $origin = & git -C $Directory remote get-url origin 2>$null
    if ($LASTEXITCODE -ne 0 -or $origin -notmatch '^(https://github\.com/Angel-Gril/DSH-Purge-Windows(?:\.git)?|git@github\.com:Angel-Gril/DSH-Purge-Windows\.git)$') {
        throw 'Git origin is not the requested DSH-Purge-Windows repository; retained without pulling or packaging.'
    }
}
