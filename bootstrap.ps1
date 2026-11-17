#Requires -Version 5.1
[CmdletBinding()]
param([string]$Checkout = (Join-Path $env:USERPROFILE 'DSH-Purge-Windows'),
      [string]$Root = '', [switch]$InstallPrerequisites, [switch]$InstallDesktop,
      [switch]$ApplyPurge, [switch]$InstallCapabilities,
      [string[]]$Modules = @(), [switch]$WithPi, [switch]$WebOnly)
$ErrorActionPreference = 'Stop'
if ($InstallPrerequisites) {
    $prerequisites = @(
        @{ Id = 'Git.Git'; Command = 'git.exe' },
        @{ Id = 'OpenJS.NodeJS.LTS'; Command = 'node.exe' },
        @{ Id = 'Python.Python.3.12'; Command = 'python.exe' },
        @{ Id = 'EclipseAdoptium.Temurin.17.JDK'; Command = 'java.exe' }
    )
    foreach ($item in $prerequisites) {
        $id = $item.Id
        $existing = Get-Command $item.Command -ErrorAction SilentlyContinue
        if ($existing -and $existing.Source -notlike '*WindowsApps*') {
            $sufficient = $false
            try {
                $versionText = (& $existing.Source --version 2>$null | Out-String)
                $match = [regex]::Match($versionText, '\d+(?:\.\d+){0,2}')
                if ($match.Success) {
                    $parts = @($match.Value -split '\.')
                    while ($parts.Count -lt 3) { $parts += '0' }
                    $version = [version]($parts -join '.')
                    $minimum = switch ($item.Command) {
                        'node.exe' { [version]'22.19.0' }
                        'python.exe' { [version]'3.11.0' }
                        'java.exe' { [version]'17.0.0' }
                        default { [version]'2.0.0' }
                    }
                    $sufficient = $LASTEXITCODE -eq 0 -and $version -ge $minimum
                }
            } catch { $sufficient = $false }
            if ($sufficient) { Write-Host "Found compatible $($item.Command)."; continue }
        }
        & winget install --id $id --exact --source winget --accept-source-agreements --accept-package-agreements --disable-interactivity
        if ($LASTEXITCODE -ne 0) { throw "winget failed for $id. Resolve it and rerun." }
    }
    # Refresh this process's PATH after installers; no machine environment rewrite.
    $env:PATH = [Environment]::GetEnvironmentVariable('Path','Machine') + ';' + [Environment]::GetEnvironmentVariable('Path','User')
}
if (Test-Path -LiteralPath $Checkout) { throw 'Checkout already exists. Use update.ps1 in that checkout.' }
& git clone https://github.com/Angel-Gril/DSH-Purge-Windows.git $Checkout
if ($LASTEXITCODE -ne 0) { throw 'Git clone failed.' }
$parameters = @{}
if ($Root) { $parameters.Root = $Root }
if ($InstallDesktop) { $parameters.InstallDesktop = $true }
if ($ApplyPurge) { $parameters.ApplyPurge = $true }
if ($InstallCapabilities) { $parameters.InstallCapabilities = $true }
if ($Modules) { $parameters.Modules = $Modules }
if ($WithPi) { $parameters.WithPi = $true }
if ($WebOnly) { $parameters.WebOnly = $true }
& (Join-Path $Checkout 'install.ps1') @parameters
