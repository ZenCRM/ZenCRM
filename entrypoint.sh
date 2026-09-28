#!/bin/sh
set -e

# Ensure runtime directories exist
mkdir -p /app/instance /app/uploads/branding /app/uploads/avatars

# Ensure database tables exist
python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all()" 2>/dev/null || true

PORT="${PORT:-80}"
echo "[ZenCRM] Uruchamianie serwera na porcie ${PORT}..."
exec gunicorn --bind "0.0.0.0:${PORT}" --workers 2 --threads 4 --timeout 120 run:app
