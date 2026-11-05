"""Separate application-token authentication boundary, never a blanket /api exception."""
import hashlib
import time
from flask import Blueprint, abort, g, jsonify, request
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models.auth_security import AuthRateLimit
from ..utils.auth_limits import auth_limit
from .models import PluginApp, PluginGrant, PluginSubscription
from .policy import require_enabled, app_or_404, require_scope
from .tokens import bearer, exchange_code, refresh_token
from .api import data, http_error, conflict
from werkzeug.exceptions import HTTPException
from sqlalchemy.orm.exc import StaleDataError
from .operations import invoke
from .manifest import EVENTS

integration_bp = Blueprint('plugin_integration', __name__)
integration_bp.register_error_handler(HTTPException, http_error)
integration_bp.register_error_handler(IntegrityError, conflict)
integration_bp.register_error_handler(StaleDataError, conflict)
# Exact endpoints and methods; unknown URLs still pass through the standard CRM guard.
INTEGRATION_ENDPOINTS = {
    'plugin_integration.token': {'POST'}, 'plugin_integration.rpc': {'POST'},
    'plugin_integration.subscriptions': {'POST', 'DELETE'},
}


def authenticate_integration():
    require_enabled()
    if request.endpoint != 'plugin_integration.token':
        g.plugin_principal = bearer(request.headers.get('Authorization'))
        enforce_quota(g.plugin_principal[1].id)
        # The quota commits: validate again in the new transaction before invoking.
        g.plugin_principal = bearer(request.headers.get('Authorization'))


def enforce_quota(grant_id):
    now = int(time.time())
    key = hashlib.sha256(f'plugin-api:{grant_id}:{now // 60}'.encode()).hexdigest()
    if not db.session.get(AuthRateLimit, key):
        try:
            with db.session.begin_nested():
                db.session.add(AuthRateLimit(key=key, count=0, expires_at=(now // 60 + 1) * 60))
                db.session.flush()
        except IntegrityError:
            pass
    changed = AuthRateLimit.query.filter_by(key=key).filter(AuthRateLimit.count < 120).update(
        {'count': AuthRateLimit.count + 1}, synchronize_session=False)
    AuthRateLimit.query.filter(AuthRateLimit.expires_at <= now).delete()
    db.session.commit()
    if not changed:
        abort(429)


@integration_bp.errorhandler(ValueError)
def invalid(error):
    db.session.rollback()
    return jsonify(error=str(error)), 400


@integration_bp.post('/oauth/token')
@auth_limit(30, seconds=60)
def token():
    # OAuth confidential clients use client_secret_post and S256 PKCE.
    if request.content_length is not None and request.content_length > 65536:
        abort(413)
    if request.mimetype == 'application/x-www-form-urlencoded' and any(len(request.form.getlist(key)) != 1 for key in request.form):
        abort(400)
    payload = request.form.to_dict() if request.mimetype == 'application/x-www-form-urlencoded' else data()
    app = app_or_404(payload.get('client_id'))
    grant_type = payload.get('grant_type')
    if grant_type == 'authorization_code':
        result = exchange_code(app, payload)
    elif grant_type == 'refresh_token':
        result = refresh_token(app, payload)
    else:
        return jsonify(error='unsupported_grant_type'), 400
    return jsonify(result)


@integration_bp.post('/call')
def rpc():
    app, grant, user = g.plugin_principal
    payload = data()
    if set(payload) - {'operation', 'params'}:
        abort(400)
    return jsonify(invoke(app, grant, user, payload.get('operation'), payload.get('params', {})))


@integration_bp.route('/subscriptions', methods=['POST', 'DELETE'])
def subscriptions():
    app, grant, user = g.plugin_principal
    require_scope(app, grant, 'events.clients')
    require_scope(app, grant, 'clients.read')
    if not app.manifest.get('event_url') or not app.signing_secret_encrypted:
        abort(400)
    payload = data()
    kind = payload.get('event')
    if set(payload) != {'event'} or not isinstance(kind, str) or kind not in EVENTS:
        abort(400)
    row = PluginSubscription.query.filter_by(grant_id=grant.id, kind=kind).first()
    if request.method == 'DELETE':
        if row:
            db.session.delete(row)
    elif not row:
        PluginApp.query.filter_by(id=app.id).update({'revision': PluginApp.revision}, synchronize_session=False)
        grant_ids = db.select(PluginGrant.id).where(PluginGrant.app_id == app.id)
        if PluginSubscription.query.filter(PluginSubscription.grant_id.in_(grant_ids)).count() >= 300:
            abort(429)
        db.session.add(PluginSubscription(grant_id=grant.id, kind=kind))
    db.session.commit()
    return jsonify(ok=True)
