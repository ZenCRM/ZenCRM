"""Reviewed Google Drive connector: fixed endpoints, per-grant encrypted credentials, narrow scope."""
import hashlib
import hmac
import json
import re
import secrets
import time
from urllib.parse import urlencode, urlsplit
import requests
from cryptography.fernet import InvalidToken
from flask import abort, current_app, request
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..utils.secret_storage import seal, unseal
from ..utils.api_security import password_version
from ..utils.urls import public_base_url
from .bundled import bundled_metadata
from .models import PluginStorage
from .policy import principal, require_scope, audit
from .tokens import challenge

APP_ID = 'zencrm-google-drive'
SCOPE = 'https://www.googleapis.com/auth/drive.file'
CALLBACK = '/api/plugins/google-drive/callback'
COOKIE = 'zencrm_drive_state'
CONNECTION = '_drive.connection'
STATE_PREFIX = '_drive.state.'
FILES = 'https://www.googleapis.com/drive/v3/files'
UPLOAD = 'https://www.googleapis.com/upload/drive/v3/files'
TOKEN = 'https://oauth2.googleapis.com/token'
REVOKE = 'https://oauth2.googleapis.com/revoke'
MAX_UPLOAD = 10 * 1024 * 1024
FILE_FIELDS = 'id,name,mimeType,size,modifiedTime'
FOLDER_TYPE = 'application/vnd.google-apps.folder'
OAUTH_SETTING = 'plugin_google_drive_oauth'


def stored_oauth():
    from ..models.setting import Setting
    row = Setting.query.filter_by(key=OAUTH_SETTING).first()
    if row is None:
        return None, None
    try:
        value = json.loads(unseal(row.value))
        if not isinstance(value, dict) or not all(isinstance(value.get(key), str) for key in ('client_id', 'client_secret')):
            raise ValueError
        return row, value
    except (ValueError, TypeError, InvalidToken):
        return row, {'client_id': '', 'client_secret': ''}


def oauth_config():
    base = public_base_url()
    parts = urlsplit(base)
    valid = parts.scheme == 'https' or (parts.scheme == 'http' and parts.hostname in ('localhost', '127.0.0.1', '::1'))
    client_id = current_app.config.get('GOOGLE_DRIVE_CLIENT_ID', '')
    secret = current_app.config.get('GOOGLE_DRIVE_CLIENT_SECRET', '')
    row, stored = stored_oauth()
    if row is not None:
        client_id, secret = stored['client_id'], stored['client_secret']
    strong_key = len(current_app.config.get('SECRET_KEY', '')) >= 32
    return {'configured': bool(client_id and secret and base and valid and strong_key),
            'client_id': client_id, 'client_secret': secret, 'redirect_uri': base + CALLBACK if base and valid else ''}


def admin_settings():
    row, _ = stored_oauth()
    config = oauth_config()
    revision = hashlib.sha256((row.value if row else config_stamp()).encode()).hexdigest()
    return {'client_id': config['client_id'], 'secret_set': bool(config['client_secret']),
            'configured': config['configured'], 'redirect_uri': config['redirect_uri'],
            'encryption_ready': len(current_app.config.get('SECRET_KEY', '')) >= 32,
            'revision': revision, 'source': 'settings' if row else 'environment'}


def save_admin_settings(payload):
    from ..models.setting import Setting
    if set(payload) != {'client_id', 'client_secret', 'revision'} or not all(isinstance(value, str) for value in payload.values()):
        abort(400)
    if len(current_app.config.get('SECRET_KEY', '')) < 32:
        abort(409, description='Serwer wymaga stałego SECRET_KEY o długości minimum 32 znaków.')
    if payload['revision'] != admin_settings()['revision']:
        abort(409)
    client_id, secret = payload['client_id'].strip(), payload['client_secret'].strip()
    if not re.fullmatch(r'[A-Za-z0-9._-]{1,512}\.apps\.googleusercontent\.com', client_id):
        abort(400, description='Podaj poprawny identyfikator klienta OAuth Google.')
    if not secret:
        existing = oauth_config()
        if client_id != existing['client_id'] or not existing['client_secret']:
            abort(400, description='Podaj sekret dla tego klienta OAuth Google.')
        secret = existing['client_secret']
    if len(secret) > 4096 or any(ord(char) < 33 or ord(char) > 126 for char in secret):
        abort(400, description='Podaj poprawny sekret klienta OAuth Google.')
    row, _ = stored_oauth()
    encrypted = seal(json.dumps({'client_id': client_id, 'client_secret': secret}))
    if row is None:
        db.session.add(Setting(key=OAUTH_SETTING, value=encrypted, category='plugins'))
    elif not Setting.query.filter_by(id=row.id, value=row.value).update({'value': encrypted}, synchronize_session=False):
        abort(409)
    db.session.commit()
    db.session.expire_all()
    return admin_settings()


def config_stamp():
    config = oauth_config()
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()


def drive_principal(grant_id):
    app, grant, user = principal(grant_id)
    if app.id != APP_ID or not bundled_metadata(app)['bundled']:
        abort(403)
    require_scope(app, grant, 'drive.files')
    return app, grant, user


def binding(grant_id):
    app, grant, user = drive_principal(grant_id)
    return {'app_revision': app.revision, 'grant_revision': grant.revision,
            'password_version': password_version(user), 'config_stamp': config_stamp()}


def read_value(row):
    try:
        value = json.loads(unseal(row.value['encrypted']))
        if not isinstance(value, dict):
            raise ValueError
        return value
    except (ValueError, KeyError, TypeError, InvalidToken):
        # Never include decryption or provider payloads in a response.
        abort(409, description='Połączenie Google Drive wymaga ponownej autoryzacji.')


def write_connection(grant_id, value, expected_revision=None):
    row = PluginStorage.query.filter_by(grant_id=grant_id, key=CONNECTION).first()
    encrypted = {'encrypted': seal(json.dumps(value))}
    if row:
        revision = row.revision if expected_revision is None else expected_revision
        changed = PluginStorage.query.filter_by(id=row.id, revision=revision).update(
            {'value': encrypted, 'revision': revision + 1}, synchronize_session=False)
        if not changed:
            abort(409)
    else:
        if expected_revision is not None:
            abort(409)
        db.session.add(PluginStorage(grant_id=grant_id, key=CONNECTION, value=encrypted, revision=secrets.randbelow(2 ** 52) + 1))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback(); abort(409)
    db.session.expire_all()


def connection(grant_id):
    expected = binding(grant_id)
    row = PluginStorage.query.filter_by(grant_id=grant_id, key=CONNECTION).first()
    if not row:
        return None, None
    value = read_value(row)
    if any(value.get(key) != item for key, item in expected.items()):
        PluginStorage.query.filter_by(id=row.id).delete(); db.session.commit()
        return None, None
    return row, value


def status(grant_id):
    _, value = connection(grant_id)
    config = oauth_config()
    return {'configured': config['configured'], 'connected': bool(value), 'scope': 'drive.file',
            'upload_limit': MAX_UPLOAD, 'callback_uri': config['redirect_uri']}


def google_request(method, url, **kwargs):
    # Every caller supplies a fixed Google URL, never a URL from the browser/provider.
    if url not in (TOKEN, REVOKE, FILES, UPLOAD):
        abort(400)
    try:
        with requests.Session() as session:
            session.trust_env = False
            with session.request(method, url, timeout=(5, 20), allow_redirects=False, stream=True, **kwargs) as response:
                raw = bytearray()
                for chunk in response.iter_content(16384):
                    raw.extend(chunk)
                    if len(raw) > 256 * 1024:
                        abort(502, description='Nieprawidłowa odpowiedź Google Drive.')
                if url == REVOKE and response.status_code in (200, 400):
                    return {}
                if response.status_code in (400, 401):
                    abort(409, description='Połączenie Google Drive wymaga ponownej autoryzacji.')
                if response.status_code == 403:
                    abort(403, description='Google Drive odmówił dostępu do tej operacji.')
                if response.status_code == 429 or response.status_code >= 500:
                    abort(503, description='Google Drive jest chwilowo niedostępny. Spróbuj później.')
                if not 200 <= response.status_code < 300:
                    abort(502, description='Nieprawidłowa odpowiedź Google Drive.')
                value = json.loads(raw)
                if not isinstance(value, dict):
                    raise ValueError
                return value
    except (requests.RequestException, ValueError):
        abort(502, description='Nie udało się połączyć z Google Drive.')


def token_value(result, old_refresh=None):
    access = result.get('access_token')
    refresh = result.get('refresh_token') or old_refresh
    expires = result.get('expires_in')
    scopes = result.get('scope', SCOPE)
    if not isinstance(scopes, str) or set(scopes.split()) != {SCOPE} or not isinstance(result.get('token_type'), str) or result['token_type'].lower() != 'bearer':
        abort(502, description='Google zwrócił nieprawidłowy zakres dostępu.')
    if not isinstance(access, str) or not 1 <= len(access) <= 8192 or not isinstance(refresh, str) or not 1 <= len(refresh) <= 8192 or type(expires) is not int or not 1 <= expires <= 86400:
        abort(502, description='Google nie zwrócił poprawnych danych połączenia.')
    if any(ord(char) < 33 or char.isspace() for char in access + refresh):
        abort(502, description='Google nie zwrócił poprawnych danych połączenia.')
    return {'access_token': access, 'refresh_token': refresh, 'expires_at': time.time() + expires}


def begin_connect(grant_id):
    config = oauth_config()
    expected = binding(grant_id)
    if not config['configured']:
        abort(409, description='Administrator musi skonfigurować integrację Google Drive.')
    if connection(grant_id)[1]:
        abort(409, description='Najpierw odłącz obecne konto Google.')
    state, verifier = secrets.token_urlsafe(32), secrets.token_urlsafe(48)
    value = {**expected, 'verifier': verifier, 'expires_at': time.time() + 600}
    PluginStorage.query.filter_by(grant_id=grant_id).filter(PluginStorage.key.startswith(STATE_PREFIX)).delete(synchronize_session=False)
    db.session.add(PluginStorage(grant_id=grant_id, key=STATE_PREFIX + hashlib.sha256(state.encode()).hexdigest(),
                                value={'encrypted': seal(json.dumps(value))}))
    db.session.commit()
    url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
        'client_id': config['client_id'], 'redirect_uri': config['redirect_uri'], 'response_type': 'code',
        'scope': SCOPE, 'access_type': 'offline', 'prompt': 'consent select_account', 'include_granted_scopes': 'false',
        'state': state, 'code_challenge': challenge(verifier), 'code_challenge_method': 'S256'})
    return url, state


def finish_connect():
    state = request.args.get('state', '')
    cookie = request.cookies.get(COOKIE, '')
    if any(len(request.args.getlist(key)) != 1 for key in request.args) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', state) or not re.fullmatch(r'[A-Za-z0-9_-]{43}', cookie) or not hmac.compare_digest(state, cookie):
        abort(400)
    row = PluginStorage.query.filter_by(key=STATE_PREFIX + hashlib.sha256(state.encode()).hexdigest()).first()
    if not row:
        abort(400)
    value, grant_id = read_value(row), row.grant_id
    if value.get('expires_at', 0) < time.time() or any(value.get(key) != item for key, item in binding(grant_id).items()):
        abort(400)
    if not PluginStorage.query.filter_by(id=row.id, revision=row.revision).delete(synchronize_session=False):
        abort(400)
    db.session.commit()  # Single-use even when Google rejects the authorization code.
    db.session.expunge(row)
    if request.args.get('error'):
        return 'denied'
    code = request.args.get('code', '')
    if not code or len(code) > 4096:
        abort(400)
    config = oauth_config()
    result = google_request('POST', TOKEN, data={'client_id': config['client_id'], 'client_secret': config['client_secret'],
        'code': code, 'code_verifier': value['verifier'], 'grant_type': 'authorization_code', 'redirect_uri': config['redirect_uri']})
    credentials = token_value(result)
    # Re-check revocation/password/config after the external exchange, before persisting credentials.
    db.session.expire_all()
    if any(value.get(key) != item for key, item in binding(grant_id).items()):
        abort(403)
    write_connection(grant_id, {**binding(grant_id), **credentials})
    app, grant, user = drive_principal(grant_id); audit(app.id, user.id, 'drive.connect'); db.session.commit()
    return 'connected'


def access_token(grant_id):
    row, value = connection(grant_id)
    if not value:
        abort(409, description='Połącz najpierw konto Google Drive.')
    if value['expires_at'] > time.time() + 60:
        return value['access_token']
    config = oauth_config()
    original_revision = row.revision
    result = google_request('POST', TOKEN, data={'client_id': config['client_id'], 'client_secret': config['client_secret'],
        'refresh_token': value['refresh_token'], 'grant_type': 'refresh_token'})
    expected = {key: value[key] for key in binding(grant_id)}
    db.session.expire_all()
    if expected != binding(grant_id):
        abort(403)
    updated = {**value, **token_value(result, value['refresh_token'])}
    write_connection(grant_id, updated, original_revision)
    return updated['access_token']


def file_tag(grant_id):
    return hmac.new(current_app.config['SECRET_KEY'].encode(), f'drive-grant:{grant_id}'.encode(), hashlib.sha256).hexdigest()


def file_data(value):
    file_id = value.get('id', '')
    if not isinstance(file_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', file_id):
        abort(502)
    return {key: str(value.get(key, ''))[:500] for key in ('id', 'name', 'mimeType', 'size', 'modifiedTime')} | {
        'url': ('https://drive.google.com/drive/folders/' if value.get('mimeType') == FOLDER_TYPE else 'https://drive.google.com/file/d/') + file_id + ('' if value.get('mimeType') == FOLDER_TYPE else '/view')}


def list_files(grant_id, search='', page_token=''):
    if not isinstance(search, str) or len(search) > 120 or not isinstance(page_token, str) or len(page_token) > 2048:
        abort(400)
    query = "trashed = false and appProperties has { key='zencrm_scope' and value='" + file_tag(grant_id) + "' }"
    if search:
        query += " and name contains '" + search.replace('\\', '\\\\').replace("'", "\\'") + "'"
    value = google_request('GET', FILES, headers={'Authorization': 'Bearer ' + access_token(grant_id)}, params={
        'q': query, 'spaces': 'drive', 'pageSize': 25, 'pageToken': page_token, 'orderBy': 'modifiedTime desc',
        'fields': 'nextPageToken,files(' + FILE_FIELDS + ')'})
    db.session.expire_all()
    drive_principal(grant_id)
    items = value.get('files', [])
    if not isinstance(items, list) or len(items) > 100 or not all(isinstance(item, dict) for item in items):
        abort(502)
    next_page = value.get('nextPageToken', '')
    if not isinstance(next_page, str) or len(next_page) > 2048:
        abort(502)
    return {'files': [file_data(item) for item in items], 'next_page': next_page}


def upload_file(grant_id, filename, content):
    if not isinstance(filename, str) or not filename.strip() or len(filename) > 180 or any(ord(c) < 32 for c in filename) or '/' in filename or '\\' in filename:
        abort(400)
    if not content or len(content) > MAX_UPLOAD:
        abort(413)
    token, tag = access_token(grant_id), file_tag(grant_id)
    headers = {'Authorization': 'Bearer ' + token}
    folders = google_request('GET', FILES, headers=headers, params={'q': "trashed=false and mimeType='" + FOLDER_TYPE + "' and appProperties has { key='zencrm_scope' and value='" + tag + "' }",
        'pageSize': 1, 'fields': 'files(id)'})
    existing = folders.get('files', [])
    if not isinstance(existing, list) or len(existing) > 1 or not all(isinstance(item, dict) for item in existing):
        abort(502)
    if existing:
        folder = existing[0].get('id', '')
    else:
        drive_principal(grant_id)
        folder = google_request('POST', FILES, headers=headers, json={'name': 'ZenCRM', 'mimeType': FOLDER_TYPE,
            'appProperties': {'zencrm_scope': tag}}, params={'fields': 'id'}).get('id', '')
    if not isinstance(folder, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', folder):
        abort(502)
    boundary = 'zencrm_' + secrets.token_hex(24)
    metadata = json.dumps({'name': filename, 'parents': [folder], 'appProperties': {'zencrm_scope': tag}}, ensure_ascii=False).encode()
    body = (f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'.encode() + metadata +
            f'\r\n--{boundary}\r\nContent-Type: application/octet-stream\r\n\r\n'.encode() + content + f'\r\n--{boundary}--\r\n'.encode())
    drive_principal(grant_id)
    result = google_request('POST', UPLOAD, headers={**headers, 'Content-Type': 'multipart/related; boundary=' + boundary},
                            params={'uploadType': 'multipart', 'fields': FILE_FIELDS}, data=body)
    db.session.expire_all()
    app, grant, user = drive_principal(grant_id); audit(app.id, user.id, 'drive.upload'); db.session.commit()
    return file_data(result)


def disconnect(grant_id):
    from werkzeug.exceptions import HTTPException
    drive_principal(grant_id)
    revoked = True
    try:
        _, value = connection(grant_id)
    except HTTPException as error:
        if error.code != 409:
            raise
        value = None
        revoked = False
    PluginStorage.query.filter_by(grant_id=grant_id).filter(PluginStorage.key.startswith('_drive.')).delete(synchronize_session=False)
    db.session.commit()
    if value:
        try:
            google_request('POST', REVOKE, data={'token': value['refresh_token']})
        except HTTPException:
            revoked = False
    app, grant, user = drive_principal(grant_id); audit(app.id, user.id, 'drive.disconnect'); db.session.commit()
    return {'connected': False, 'revoked_at_google': revoked}
