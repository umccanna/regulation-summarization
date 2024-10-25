param(
    [switch]$Recreate,
    [string]$PythonVersion = "3.11"
)

$python = "python$PythonVersion"
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

Write-Host "Activating Environemnt"
& .venv/Scripts/activate.ps1

$environmentPythonVersion = & python --version

if (-Not ($environmentPythonVersion.StartsWith("Python $PythonVersion"))) {
    & deactivate
    Write-Warning "Python Version required for functions is $PythonVersion.x found $environmentPythonVersion.  Please ensure you have $PythonVersion.x installed on your machine"
    return
}

if (Test-Path "requirements.txt") {
    Write-Host "Installing Dependencies"
    & pip install -r requirements.txt
}