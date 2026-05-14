# Uruchamia serwer gRPC z wlaczonym ProtoReflectionService na porcie 50051.

$ErrorActionPreference = 'Stop'
$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$serverDir   = Join-Path $projectRoot 'server-java'

Push-Location $serverDir
try {
    $jar = Get-ChildItem (Join-Path $serverDir 'target') -Filter '*-all.jar' -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $jar) {
        Write-Host "[run-grpc] Building uber-jar (mvn -q -DskipTests package) ..." -ForegroundColor Yellow
        & mvn -q -DskipTests package
        if ($LASTEXITCODE -ne 0) { throw "mvn package failed with $LASTEXITCODE" }
        $jar = Get-ChildItem (Join-Path $serverDir 'target') -Filter '*-all.jar' | Select-Object -First 1
    }
    Write-Host "[run-grpc] Starting GrpcServerApp on :50051" -ForegroundColor Cyan
    & java -cp $jar.FullName smarthome.grpc.GrpcServerApp --port 50051
} finally {
    Pop-Location
}
