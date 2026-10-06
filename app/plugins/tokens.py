"""Narrow OAuth authorization-code/PKCE flow and revocable opaque bearer tokens."""
import base64
import hashlib
import hmac
import re
import secrets
import uuid
from datetime import datetime, timedelta
from flask import abort
from werkzeug.security import check_password_hash
from ..extensions import db
from ..utils.api_security import password_version
from .models import PluginCode, PluginToken, PluginGrant
from .policy import principal


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def challenge(verifier):
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode('ascii')).digest()).rstrip(b'=').decode()


def authorize_code(app, grant, user, data):
    if set(data) - {'response_type', 'redirect_uri', 'code_challenge', 'code_challenge_method', 'state'}:
        abort(400)
    redirect_uri = data.get('redirect_uri')
    proof = data.get('code_challenge')
    if data.get('response_type') != 'code' or redirect_uri not in app.manifest.get('redirect_uris', []):
        abort(400)
    if data.get('code_challenge_method') != 'S256' or not isinstance(proof, str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', proof):
        abort(400)
    state = data.get('state')
    if not isinstance(state, str) or not 16 <= len(state) <= 512:
        abort(400)
    code = secrets.token_urlsafe(32)
    db.session.add(PluginCode(code_hash=digest(code), grant_id=grant.id,
        redirect_uri=redirect_uri, challenge=proof, app_revision=app.revision,
        grant_revision=grant.revision, password_version=password_version(user),
        expires_at=datetime.utcnow() + timedelta(minutes=2)))
    db.session.commit()
    # Return to the trusted host UI; never redirect arbitrary unvalidated URLs.
    return {'code': code, 'state': state, 'redirect_uri': redirect_uri}


def issue(app, grant, user, *, family=None, refresh=True, expires=None, refresh_until=None):
    # Serialize the per-user/app quota before generating another credential.
    PluginGrant.query.filter_by(id=grant.id).update({'revision': PluginGrant.revision}, synchronize_session=False)
    now = datetime.utcnow()
    if PluginToken.query.filter_by(grant_id=grant.id, revoked=False).filter(
            (PluginToken.expires_at > now) | (PluginToken.refresh_expires_at > now)).count() >= 50:
        abort(429)
    access = 'zenapp_' + secrets.token_urlsafe(32)
    refresh_value = 'zenrefresh_' + secrets.token_urlsafe(32) if refresh else None
    until = expires or now + timedelta(minutes=15)
    row = PluginToken(access_hash=digest(access), refresh_hash=digest(refresh_value) if refresh else None,
        family=family or str(uuid.uuid4()), grant_id=grant.id, app_revision=app.revision,
        grant_revision=grant.revision, password_version=password_version(user), expires_at=until,
        refresh_expires_at=(refresh_until or now + timedelta(days=30)) if refresh else None)
    db.session.add(row)
    response = {'access_token': access, 'token_type': 'Bearer', 'expires_in': max(0, int((until - now).total_seconds())),
                'scope': ' '.join(sorted(set(grant.scopes) & set(app.approved_scopes)))}
    if refresh:
        response['refresh_token'] = refresh_value
    return response


def authenticate_client(app, secret):
    if not isinstance(secret, str) or len(secret) > 256 or not app.client_secret_hash or not check_password_hash(app.client_secret_hash, secret):
        abort(401)


def exchange_code(app, data):
    authenticate_client(app, data.get('client_secret'))
    raw = data.get('code')
    verifier = data.get('code_verifier')
    if not isinstance(raw, str) or len(raw) > 256 or not isinstance(verifier, str) or not re.fullmatch(r'[A-Za-z0-9._~-]{43,128}', verifier):
        abort(400)
    row = db.session.get(PluginCode, digest(raw))
    if not row or row.consumed or row.expires_at <= datetime.utcnow() or row.redirect_uri != data.get('redirect_uri') or not hmac.compare_digest(row.challenge, challenge(verifier)):
        abort(400)
    actual_app, grant, user = principal(row.grant_id, app_revision=row.app_revision,
        grant_revision=row.grant_revision, version=row.password_version)
    if actual_app.id != app.id:
        abort(400)
    changed = PluginCode.query.filter_by(code_hash=row.code_hash, consumed=False).update(
        {'consumed': True}, synchronize_session=False)
    if changed != 1:
        db.session.rollback()
        abort(400)
    response = issue(app, grant, user)
    db.session.commit()
    return response


def refresh_token(app, data):
    authenticate_client(app, data.get('client_secret'))
    raw = data.get('refresh_token')
    if not isinstance(raw, str) or not raw.startswith('zenrefresh_') or len(raw) > 256:
        abort(400)
    row = PluginToken.query.filter_by(refresh_hash=digest(raw)).first()
    if not row or not row.refresh_expires_at or row.refresh_expires_at <= datetime.utcnow():
        abort(400)
    actual_app, grant, user = principal(row.grant_id, app_revision=row.app_revision,
        grant_revision=row.grant_revision, version=row.password_version)
    if actual_app.id != app.id:
        abort(400)
    # Rotation and detection of reuse, including competing workers.
    changed = PluginToken.query.filter_by(access_hash=row.access_hash, refresh_used=False, revoked=False).update(
        {'refresh_used': True, 'revoked': True}, synchronize_session=False)
    if changed != 1:
        PluginToken.query.filter_by(family=row.family).update({'revoked': True}, synchronize_session=False)
        db.session.commit()
        abort(400)
    response = issue(app, grant, user, family=row.family, refresh_until=row.refresh_expires_at)
    db.session.commit()
    return response


def bearer(value):
    if not isinstance(value, str) or not value.startswith('Bearer zenapp_') or len(value) > 256:
        abort(401)
    row = db.session.get(PluginToken, digest(value[7:]))
    if not row or row.revoked or row.expires_at <= datetime.utcnow():
        abort(401)
    return principal(row.grant_id, app_revision=row.app_revision,
                     grant_revision=row.grant_revision, version=row.password_version)
