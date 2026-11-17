#Requires -Version 5.1
param([Parameter(Mandatory=$true)][string]$Installer)
$ErrorActionPreference = 'Stop'
$signature = Get-AuthenticodeSignature -LiteralPath $Installer
if ($signature.Status -ne 'Valid' -or -not $signature.SignerCertificate) {
    throw "Installer Authenticode verification failed: $($signature.Status)"
}
Write-Host "Verified installer signer: $($signature.SignerCertificate.Subject)"
