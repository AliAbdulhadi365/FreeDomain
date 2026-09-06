$ErrorActionPreference = "Stop"
Invoke-RestMethod "http://localhost:5000/health" | ConvertTo-Json
docker compose ps
