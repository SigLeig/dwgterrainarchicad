$ErrorActionPreference = "Stop"

Set-Location -Path $PSScriptRoot

$python = Get-Command py -ErrorAction SilentlyContinue
if ($python) {
    & py -3 -m pip install --user -e .
} else {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Error "Could not find Python. Install Python 3.9 or newer first."
    }
    & python -m pip install --user -e .
}

Write-Host ""
Write-Host "Installed step-to-ifc for the current user."
Write-Host "Test it with:"
Write-Host "  step-to-ifc --help"
Write-Host ""
Write-Host "If 'step-to-ifc' is not found, add Python's Scripts folder to PATH."
Write-Host "You still need FreeCAD installed for real STEP to IFC conversion."
