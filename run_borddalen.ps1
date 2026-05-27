# Run this from the project folder in PowerShell:
#   powershell -ExecutionPolicy Bypass -File .\run_borddalen.ps1
#
# If this is the first run, install the program first:
#   py -m pip install -e .

$InputFile = "C:\Users\Sigmund\Downloads\Filemail.com - Bordalen\t_fkb_borddalen_utm32.dwg"
$OutputDir = ".\borddalen-terrain"
$Layers = "KOTE*,TERRAIN*,HOYDE*"
$SampleDistance = 2

# If ODA File Converter is not on PATH, set the path here.
# Example:
# $Converter = "C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"
$Converter = ""

$Arguments = @(
    $InputFile,
    "--output-dir", $OutputDir,
    "--layers", $Layers,
    "--sample-distance", $SampleDistance
)

if ($Converter -ne "") {
    $Arguments += @("--converter", $Converter)
}

dwg-terrain-archicad @Arguments

Write-Host ""
Write-Host "Done. Import *_archicad_surveyor.txt from $OutputDir into Archicad as surveyor/mesh data."
