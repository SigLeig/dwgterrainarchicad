# Run this from the project folder in PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\run_borddalen.ps1
#
# First-time setup:
#   py -m pip install -e .
#
# DWG files need ODA File Converter or another DWG-to-DXF converter.
# Download ODA File Converter if this script cannot find it:
#   https://www.opendesign.com/guestfiles/oda_file_converter

$InputFile = "C:\Users\Sigmund\Downloads\Filemail.com - Bordalen\t_fkb_borddalen_utm32.dwg"
$OutputDir = ".\borddalen-terrain"
$Layers = "KOTE*,TERRAIN*,HOYDE*"
$SampleDistance = 2

# Leave this empty to auto-detect ODA File Converter.
# If auto-detection fails, set this to the full .exe path, not just the folder.
# Example:
# $Converter = "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
$Converter = ""

function Find-OdaFileConverter {
    $command = Get-Command "ODAFileConverter.exe" -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidatePaths = @(
        "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe",
        "C:\Program Files\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe",
        "C:\Program Files\ODA\ODAFileConverter 26.8.0\ODAFileConverter.exe",
        "C:\Program Files\ODA\ODAFileConverter 25.12.0\ODAFileConverter.exe",
        "C:\Program Files\ODA\ODAFileConverter 25.8.0\ODAFileConverter.exe",
        "C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe"
    )

    foreach ($path in $candidatePaths) {
        if (Test-Path $path) {
            return $path
        }
    }

    $odaRoot = "C:\Program Files\ODA"
    if (Test-Path $odaRoot) {
        $found = Get-ChildItem $odaRoot -Recurse -Filter "ODAFileConverter.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($found) {
            return $found.FullName
        }
    }

    return ""
}

if (-not (Test-Path $InputFile)) {
    Write-Error "Finner ikke DWG-filen: $InputFile"
    exit 1
}

$Arguments = @(
    $InputFile,
    "--output-dir", $OutputDir,
    "--layers", $Layers,
    "--sample-distance", $SampleDistance
)

if ($Converter -eq "") {
    $Converter = Find-OdaFileConverter
}

if ($Converter -ne "") {
    if (-not (Test-Path $Converter)) {
        Write-Error "Finner ikke ODA File Converter: $Converter"
        Write-Host ""
        Write-Host "Sett `$Converter til hele EXE-stien, for eksempel:"
        Write-Host '  $Converter = "C:\Program Files\ODA\ODAFileConverter 26.12.0\ODAFileConverter.exe"'
        Write-Host ""
        Write-Host "Eller installer ODA File Converter fra:"
        Write-Host "  https://www.opendesign.com/guestfiles/oda_file_converter"
        exit 1
    }

    $Arguments += @("--converter", $Converter)
    Write-Host "Bruker ODA File Converter: $Converter"
}
else {
    Write-Host "Fant ikke ODA File Converter automatisk."
    Write-Host "Programmet kan fortsatt virke hvis ODAFileConverter.exe eller dwgread ligger i PATH."
}

dwg-terrain-archicad @Arguments

Write-Host ""
Write-Host "Ferdig. Importer *_archicad_surveyor.txt fra $OutputDir i Archicad som surveyor/mesh-data."
