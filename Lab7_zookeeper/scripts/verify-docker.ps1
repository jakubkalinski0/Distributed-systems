# Pre-flight checks for Docker-based ZooKeeper lab
$ErrorActionPreference = "Continue"
$failed = $false

Write-Host "=== Docker Pre-flight Checks ===" -ForegroundColor Cyan

function Test-Command($name, $cmd) {
    try {
        $out = Invoke-Expression $cmd 2>&1
        Write-Host "[OK] $name" -ForegroundColor Green
        Write-Host "     $out"
        return $true
    } catch {
        Write-Host "[FAIL] $name" -ForegroundColor Red
        Write-Host "     $_"
        return $false
    }
}

if (-not (Test-Command "Docker CLI" "docker --version")) { $failed = $true }
if (-not (Test-Command "Docker Compose" "docker compose version")) { $failed = $true }

$info = docker info 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] Docker daemon is not running" -ForegroundColor Red
    Write-Host "     Start Docker Desktop and retry."
    $failed = $true
} else {
    Write-Host "[OK] Docker daemon is running" -ForegroundColor Green
}

$ports = @(2181, 2182, 2183, 8080, 9090)
foreach ($port in $ports) {
    $inUse = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    if ($inUse) {
        Write-Host "[WARN] Port $port is in use" -ForegroundColor Yellow
    } else {
        Write-Host "[OK] Port $port is free" -ForegroundColor Green
    }
}

if ($failed) {
    Write-Host "`nSome checks failed. Fix issues before running docker compose." -ForegroundColor Red
    exit 1
}

Write-Host "`nAll checks passed." -ForegroundColor Green
exit 0
