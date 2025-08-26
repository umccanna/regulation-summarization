param(
    [switch]$Recreate,
    [string]$AdditionalTrustedRootCAThumbprint = "d72f47d87420e3f0f9bdcac6f03a566743c481b9"
)

$python = "python"
if (-Not (Test-Path .venv)) {
    Write-Host "Creating Virtual Environment"
    & $python -m venv .venv
} else {
    if ($Recreate) {
        Write-Host "Recreating Virtual Environment"
        Remove-Item -Path ".venv" -Recurse -Force
        
        & $python -m venv .venv
    } else {
        Write-Host "Virtual Environment already exists"
    }
}

if (-Not ("" -eq $AdditionalTrustedRootCAThumbprint)) {
    Write-Host "Configuring additional trusted root CA..."
    $CACert = Get-ChildItem -Path "Cert:\LocalMachine\Root" | Where-Object { $_.Thumbprint -eq $AdditionalTrustedRootCAThumbprint }
    if (-Not $CACert) {
        Write-Warning "$AdditionalTrustedRootCAThumbprint thumbprint not found in 'Cert:\LocalMachine\Root' store"
    } else {
        $TempBinaryFile = New-TemporaryFile
        Export-Certificate -Cert $CACert -FilePath $TempBinaryFile
        $BinaryContent = [System.IO.File]::ReadAllBytes($TempBinaryFile)
        $Base64Cert = [System.Convert]::ToBase64String($BinaryContent)
        $CACertPemPath = "$PSSCriptRoot/.venv/Lib/site-packages/certifi/cacert.pem"
        if (-Not (Test-Path $CACertPemPath)) {
            Write-Warning "Unable to update trusted root CA. $CACertPemPath not found"
        } else {
            $CACertContent = [System.IO.File]::ReadAllText($CACertPemPath)
            if ($CACertContent.Contains($Base64Cert)) {
                Write-Host "$CACertPemPath already contains the requested root CA cert"
            } else {
                Add-Content -Path $CACertPemPath -Value "-----BEGIN CERTIFICATE-----" -Encoding "utf8"
                Add-Content -Path $CACertPemPath -Value $Base64Cert -Encoding "utf8"
                Add-Content -Path $CACertPemPath -Value "-----END CERTIFICATE-----" -Encoding "utf8"
                Write-Host "$CACertPemPath updated with $AdditionalTrustedRootCAThumbprint"
            }
        }
    }    
}

Write-Host "Activating Environemnt"
& .venv/Scripts/activate.ps1

if (Test-Path "requirements.txt") {
    Write-Host "Installing Dependencies"
    & pip install -r requirements.txt
}