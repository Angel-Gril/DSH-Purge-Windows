#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\scripts\common.ps1')
$testRoot = Join-Path ([IO.Path]::GetTempPath()) ('DSH-git-boundary-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
try {
    & git init --quiet $testRoot
    if ($LASTEXITCODE -ne 0) { throw 'Could not create isolated Git fixture.' }
    $nested = Join-Path $testRoot 'archive-without-dotgit'
    New-Item -ItemType Directory -Path $nested | Out-Null
    $rejected = $false
    try { Assert-WorkbenchGitCheckout -Directory $nested } catch { $rejected = $true }
    if (-not $rejected) { throw 'A nested archive incorrectly selected its parent repository.' }
    & git -C $testRoot remote add origin https://github.com/example/unrelated.git
    $rejected = $false
    try { Assert-WorkbenchGitCheckout -Directory $testRoot } catch { $rejected = $true }
    if (-not $rejected) { throw 'An unrelated origin was incorrectly accepted.' }
    & git -C $testRoot remote set-url origin https://github.com/Angel-Gril/DSH-Purge-Windows.git
    Assert-WorkbenchGitCheckout -Directory $testRoot
    Write-Host 'Git boundaries: parent rejected, wrong origin rejected, expected checkout accepted.'
} finally {
    # Only remove the exact newly created temporary fixture; use one shell.
    $resolved = [IO.Path]::GetFullPath($testRoot)
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
    if (-not $resolved.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -or
        [IO.Path]::GetFileName($resolved) -notlike 'DSH-git-boundary-*') { throw 'Invalid temporary fixture path.' }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}
