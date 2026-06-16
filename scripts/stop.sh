#!/usr/bin/env sh
set -e

cd "$(dirname "$0")/.."

docker rm -f pm-app >/dev/null 2>&1 || true

echo "Stopped pm-app container"
