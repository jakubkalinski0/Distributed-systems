# Generuje stuby Java z idl/smarthome.ice do server-java/target/generated-sources/slice
# Wygenerowane pliki sa pozniej dolaczane do source path przez build-helper-maven-plugin.

$ErrorActionPreference = 'Stop'

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$slice       = Join-Path $projectRoot 'idl/smarthome.ice'
$outputDir   = Join-Path $projectRoot 'server-java/target/generated-sources/slice'

# Lokalizacja slice2java (instalacja ZeroC Ice 3.7.x)
$slice2java = $null
$cmd = Get-Command slice2java -ErrorAction SilentlyContinue
if ($cmd) { $slice2java = $cmd.Source }
if (-not $slice2java) {
    $candidate = 'C:\Program Files\ZeroC\Ice-3.7.11\bin\slice2java.exe'
    if (Test-Path $candidate) { $slice2java = $candidate }
}
if (-not $slice2java) { throw "Nie znaleziono slice2java. Zainstaluj ZeroC Ice 3.7 lub dodaj do PATH." }

if (-not (Test-Path $outputDir)) { New-Item -ItemType Directory -Path $outputDir -Force | Out-Null }

Write-Host "[gen-slice-java] $slice2java --output-dir $outputDir $slice" -ForegroundColor Cyan
& $slice2java --output-dir $outputDir $slice
if ($LASTEXITCODE -ne 0) { throw "slice2java zakonczyl sie kodem $LASTEXITCODE" }

Write-Host "[gen-slice-java] OK. Pliki w: $outputDir" -ForegroundColor Green
