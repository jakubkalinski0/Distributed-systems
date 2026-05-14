# Generuje stuby Python z idl/smarthome.ice do client-python/generated
# Wygenerowane pliki sa nastepnie importowane przez ice_client.py.

$ErrorActionPreference = 'Stop'

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$slice       = Join-Path $projectRoot 'idl/smarthome.ice'
$outputDir   = Join-Path $projectRoot 'client-python/generated'

$slice2py = $null
$cmd = Get-Command slice2py -ErrorAction SilentlyContinue
if ($cmd) { $slice2py = $cmd.Source }
if (-not $slice2py) {
    $candidate = 'C:\Program Files\ZeroC\Ice-3.7.11\bin\slice2py.exe'
    if (Test-Path $candidate) { $slice2py = $candidate }
}
if (-not $slice2py) { throw "Nie znaleziono slice2py. Zainstaluj ZeroC Ice 3.7 lub dodaj do PATH." }

if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir -Force | Out-Null }

Write-Host "[gen-slice-py] $slice2py --output-dir $outputDir $slice" -ForegroundColor Cyan
& $slice2py --output-dir $outputDir $slice
if ($LASTEXITCODE -ne 0) { throw "slice2py zakonczyl sie kodem $LASTEXITCODE" }

Write-Host "[gen-slice-py] OK. Pliki w: $outputDir" -ForegroundColor Green
