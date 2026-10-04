"""Database-backed fixed-window limits shared by all application workers."""
import hashlib
import time
from functools import wraps
from flask import abort, request
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models.auth_security import AuthRateLimit


def auth_limit(limit, seconds=900, by_user=False, scope=None):
    def decorate(func):
        @wraps(func)
        def limited(*args, **kwargs):
            now = int(time.time())
            window = now // seconds
            # Key by client address only: X-Forwarded-For is honoured solely through
            # ProxyFix (TRUSTED_PROXY_HOPS), and a body-supplied key such as the login
            # email would let anyone lock a known account out from another address.
            identity = request.remote_addr or 'unknown'
            if by_user:
                from .deletion import current_user
                identity = 'user:' + str(current_user().id)
            key = hashlib.sha256(f'{scope or request.endpoint}:{identity}:{window}'.encode()).hexdigest()
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
