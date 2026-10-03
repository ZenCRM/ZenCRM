"""Installation-specific signing keys, persisted across worker restarts."""
import os
import secrets
import sqlite3
from pathlib import Path


def configure_secrets(app):
    insecure = {None, '', 'dev-secret', 'jwt-dev-secret',
                'twoj-sekret', 'twoj-jwt-sekret',
                'zmien-mnie-na-bezpieczny-losowy-ciag',
                'zmien-mnie-na-bezpieczny-jwt-secret'}
    missing = [key for key in ('SECRET_KEY', 'JWT_SECRET_KEY')
               if not isinstance(app.config.get(key), str)
               or len(app.config[key]) < 32 or app.config[key] in insecure]
    if not missing:
        return
    if app.testing:
        for key in missing:
            app.config[key] = secrets.token_hex(32)
        return
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    path = Path(app.instance_path) / 'security.sqlite'
    conn = sqlite3.connect(str(path))
    try:
        if os.name != 'nt':
            try:
                path.chmod(0o600)
            except OSError:
                pass
        conn.execute('CREATE TABLE IF NOT EXISTS secrets (name TEXT PRIMARY KEY, value TEXT NOT NULL)')
        for key in missing:
            conn.execute('INSERT OR IGNORE INTO secrets VALUES (?, ?)', (key, secrets.token_hex(32)))
            app.config[key] = conn.execute('SELECT value FROM secrets WHERE name = ?', (key,)).fetchone()[0]
        conn.commit()
    finally:
        conn.close()
