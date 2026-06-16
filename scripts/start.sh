#!/usr/bin/env sh
set -e

cd "$(dirname "$0")/.."

docker build -t pm-app .
docker rm -f pm-app >/dev/null 2>&1 || true
docker run -d --name pm-app -p 8000:8000 --env-file .env pm-app

echo "App started at http://localhost:8000"
