param([string]$OutputDirectory = "backups")
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path $OutputDirectory | Out-Null
$source = "data\freedomain.db"
if (-not (Test-Path $source)) { throw "Database not found at $source." }
$target = Join-Path $OutputDirectory ("freedomain-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".db")
Copy-Item $source $target
Write-Host "Backup written to $target"
