#!/bin/sh
set -e

# Ensure runtime directories exist
mkdir -p /app/instance /app/uploads/branding /app/uploads/avatars 2>/dev/null || true

# If container starts as root, automatically fix volume ownership for existing
# installations and drop privileges to the non-root 'zencrm' user.
if [ "$(id -u)" = "0" ]; then
    chown -R zencrm:zencrm /app/instance /app/uploads 2>/dev/null || true
    exec runuser -u zencrm -- "$0" "$@"
fi

# If a custom command is provided, execute it directly
if [ "$#" -gt 0 ]; then
    exec "$@"
fi

# Migrate the database once, before workers start (without creating a hardcoded admin).
python seed.py

PORT="${PORT:-8080}"
echo "[ZenCRM] Uruchamianie serwera na porcie ${PORT}..."
# Workers skip schema preparation; seed.py has just done it once.
export PREPARE_DATABASE=false
exec gunicorn --bind "0.0.0.0:${PORT}" --workers 2 --threads 4 --timeout 120 run:app
