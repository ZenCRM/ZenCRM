#!/usr/bin/env bash
# Start an image on a fresh volume and wait until the application is ready.
# Usage: container-smoke.sh <image> <container-name> <host-port>
set -euo pipefail

image="$1"
name="$2"
port="$3"

docker run -d --name "$name" -p "127.0.0.1:${port}:8080" \
  -e SECRET_KEY="$(openssl rand -hex 32)" \
  -e JWT_SECRET_KEY="$(openssl rand -hex 32)" \
  -e MAIL_POLLING_ENABLED=false \
  -v "${name}-data:/app/instance" \
  "$image" >/dev/null

for _ in $(seq 1 60); do
  if body="$(curl -fsS --max-time 5 "http://127.0.0.1:${port}/api/auth/setup-status" 2>/dev/null)"; then
    if [[ "$body" != *'"needs_setup":true'* && "$body" != *'"needs_setup": true'* ]]; then
      echo "Unexpected setup status: $body" >&2
      exit 1
    fi
    if docker logs "$name" 2>&1 | grep -q 'Traceback'; then
      docker logs "$name" >&2
      exit 1
    fi
    echo "Container $name is ready on port $port"
    exit 0
  fi
  sleep 1
done

echo "Container $name did not become ready" >&2
docker logs "$name" >&2
exit 1
