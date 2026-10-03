"""Database-backed fixed-window limits shared by all application workers."""
import hashlib
import time
from functools import wraps
from flask import abort, request
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models.auth_security import AuthRateLimit


def auth_limit(limit, seconds=900):
    def decorate(func):
        @wraps(func)
        def limited(*args, **kwargs):
            now = int(time.time())
            window = now // seconds
            # Do not trust client-supplied X-Forwarded-For.
            identity = request.remote_addr or 'unknown'
            if request.endpoint == 'auth.login':
                data = request.get_json(silent=True) or {}
                email = data.get('email', '') if isinstance(data, dict) else ''
                identity = str(email).strip().lower()[:120] or identity
            key = hashlib.sha256(f'{request.endpoint}:{identity}:{window}'.encode()).hexdigest()
            AuthRateLimit.query.filter(AuthRateLimit.expires_at <= now).delete()
            if not db.session.get(AuthRateLimit, key):
                try:
                    with db.session.begin_nested():
                        db.session.add(AuthRateLimit(key=key, count=0, expires_at=(window + 1) * seconds))
                        db.session.flush()
                except IntegrityError:
                    pass
            changed = AuthRateLimit.query.filter_by(key=key).filter(AuthRateLimit.count < limit).update(
                {AuthRateLimit.count: AuthRateLimit.count + 1}, synchronize_session=False)
            db.session.commit()
            if not changed:
                abort(429)
            return func(*args, **kwargs)
        return limited
    return decorate
