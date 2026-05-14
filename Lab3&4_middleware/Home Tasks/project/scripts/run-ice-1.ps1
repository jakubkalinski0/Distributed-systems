# Uruchamia serwer Ice "building-1" na porcie 10000.
# Wymaga: zbudowanego uber-jara w server-java/target (mvn package).

$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$serverDir   = Join-Path $projectRoot 'server-java'

Push-Location $serverDir
try {
    $jar = Get-ChildItem (Join-Path $serverDir 'target') -Filter '*-all.jar' -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $jar) {
        Write-Host "[run-ice-1] Building uber-jar (mvn -q -DskipTests package) ..." -ForegroundColor Yellow
        & mvn -q -DskipTests package
        if ($LASTEXITCODE -ne 0) { throw "mvn package failed with $LASTEXITCODE" }
        $jar = Get-ChildItem (Join-Path $serverDir 'target') -Filter '*-all.jar' | Select-Object -First 1
    }
    Write-Host "[run-ice-1] Starting IceServerApp with config/building-1.properties" -ForegroundColor Cyan
    & java -cp $jar.FullName smarthome.ice.IceServerApp --config config/building-1.properties
} finally {
    Pop-Location
}
