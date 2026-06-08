# Integration test helper — manipulates znode /a via zkCli in Docker
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("create-a", "delete-a", "add-child", "delete-child", "list", "full-test")]
    [string]$Action,
    [string]$ChildName = "child1"
)

$zkContainer = "zk1"
$zkServer = "localhost:2181"

function Invoke-ZkCli {
    param([string[]]$Commands)
    $input = ($Commands -join "`n") + "`n"
    $input | docker exec -i $zkContainer zkCli.sh -server $zkServer
}

switch ($Action) {
    "create-a" { Invoke-ZkCli @("create /a ''") }
    "delete-a" { Invoke-ZkCli @("delete /a") }
    "add-child" { Invoke-ZkCli @("create /a/$ChildName ''") }
    "delete-child" { Invoke-ZkCli @("delete /a/$ChildName") }
    "list" { Invoke-ZkCli @("ls /a", "get /a") }
    "full-test" {
        Write-Host "=== Full integration test ===" -ForegroundColor Cyan
        Invoke-ZkCli @("delete /a") 2>$null
        Start-Sleep -Seconds 2
        Write-Host "Creating /a..."
        Invoke-ZkCli @("create /a ''")
        Start-Sleep -Seconds 3
        Write-Host "Adding children..."
        Invoke-ZkCli @("create /a/child1 'data1'", "create /a/child2 'data2'")
        Start-Sleep -Seconds 2
        Invoke-ZkCli @("ls /a")
        Start-Sleep -Seconds 2
        Write-Host "Deleting child1..."
        Invoke-ZkCli @("delete /a/child1")
        Start-Sleep -Seconds 2
        Write-Host "Deleting remaining children and /a..."
        Invoke-ZkCli @("delete /a/child2", "delete /a")
        Write-Host "Done. Check http://localhost:8080 and http://localhost:9090" -ForegroundColor Green
    }
}
