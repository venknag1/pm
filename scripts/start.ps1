Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$root\.."

docker build -t pm-app .
try {
    docker rm -f pm-app | Out-Null
} catch {
}

docker run -d --name pm-app -p 8000:8000 --env-file .env pm-app
Write-Host "App started at http://localhost:8000"
