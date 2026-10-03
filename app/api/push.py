import base64
import hashlib
from urllib.parse import urlsplit
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.push import PushSubscription
from ..models.user import User
from ..services.push_service import public_key

push_bp = Blueprint('push', __name__)


def validate_subscription(data):
    if not isinstance(data, dict):
        raise ValueError('Nieprawidłowa subskrypcja.')
    endpoint = data.get('endpoint', '')
    if not isinstance(endpoint, str) or len(endpoint) > 4096 or endpoint != endpoint.strip() or any(ord(c) < 33 or c == '\\' for c in endpoint):
        raise ValueError('Nieprawidłowy adres usługi push.')
    try:
        url = urlsplit(endpoint)
        host = url.hostname or ''
        port = url.port
    except ValueError as exc:
        raise ValueError('Nieprawidłowy adres usługi push.') from exc
    if '%' in url.netloc or '@' in url.netloc or not url.path.startswith('/'):
        raise ValueError('Nieprawidłowy adres usługi push.')
    # Only browser push providers. Never allow arbitrary server-side HTTP requests.
    allowed = host == 'fcm.googleapis.com' or host == 'web.push.apple.com' or host.endswith('.push.apple.com') or host.endswith('.push.services.mozilla.com') or host.endswith('.notify.windows.com')
    if url.scheme != 'https' or not allowed or url.username or url.password or port not in (None, 443) or url.fragment:
        raise ValueError('Nieobsługiwana usługa powiadomień przeglądarki.')
    keys = data.get('keys') or {}
    if not isinstance(keys, dict):
        raise ValueError('Nieprawidłowe klucze subskrypcji.')
    for name, size in [('p256dh', 65), ('auth', 16)]:
        value = keys.get(name)
        if not isinstance(value, str) or len(value) > 120:
            raise ValueError('Nieprawidłowe klucze subskrypcji.')
        try:
            raw = base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)
            if len(raw) != size or (name == 'p256dh' and raw[0] != 4):
                raise ValueError()
        except (ValueError, TypeError):
            raise ValueError('Nieprawidłowe klucze subskrypcji.')
    return {'endpoint': endpoint, 'keys': {k: keys[k] for k in ('p256dh', 'auth')}}


@push_bp.before_request
@jwt_required()
def active_user():
    user = db.session.get(User, int(get_jwt_identity()))
    if not user or not user.is_active:
        return jsonify(error='Konto jest nieaktywne.'), 403


@push_bp.get('/config')
def config():
    return jsonify(enabled=current_app.config['PUSH_ENABLED'], public_key=public_key())


@push_bp.post('/subscriptions')
def subscribe():
    if not current_app.config['PUSH_ENABLED']:
        return jsonify(error='Powiadomienia push są wyłączone na serwerze.'), 503
    try:
        clean = validate_subscription(request.get_json(silent=True))
        digest = hashlib.sha256(clean['endpoint'].encode()).hexdigest()
        row = PushSubscription.query.filter_by(endpoint_hash=digest).first()
        uid = int(get_jwt_identity())
        if row and row.user_id != uid and row.subscription.get('keys') != clean['keys']:
            return jsonify(error='Subskrypcja należy do innego urządzenia.'), 403
        if not row:
            row = PushSubscription(endpoint_hash=digest)
            db.session.add(row)
        row.user_id = uid
        row.subscription = clean
        row.enabled = True
        db.session.commit()
        return jsonify(ok=True)
    except ValueError as error:
        return jsonify(error=str(error)), 400


@push_bp.delete('/subscriptions')
def unsubscribe():
    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint') if isinstance(data, dict) else None
    if not isinstance(endpoint, str):
        return jsonify(error='Brak subskrypcji.'), 400
    digest = hashlib.sha256(endpoint.encode()).hexdigest()
    row = PushSubscription.query.filter_by(endpoint_hash=digest, user_id=int(get_jwt_identity())).first()
    if row:
        row.enabled = False
        db.session.commit()
    return jsonify(ok=True)
