param([ValidateSet("development", "production")][string]$Environment = "development")
$ErrorActionPreference = "Stop"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker is required." }
if ($Environment -eq "production" -and -not (Test-Path ".env")) { throw "Create .env from .env.example before production deployment." }
docker compose up --build --detach
docker compose ps
