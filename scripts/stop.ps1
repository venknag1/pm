Set-StrictMode -Version Latest

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$root\.."

try {
    docker rm -f pm-app | Out-Null
} catch {
}

Write-Host "Stopped pm-app container"
