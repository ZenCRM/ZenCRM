"""CRM-side application management and explicit user authorization."""
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, abort, jsonify, request, current_app
from werkzeug.security import generate_password_hash
from werkzeug.exceptions import HTTPException
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models.user import User
from ..utils.deletion import current_user
from ..utils.secret_storage import seal
from ..utils.auth_limits import auth_limit
from ..utils.i18n import t
from .manifest import validate_manifest, scope_list, SCOPES, OPERATIONS, EVENTS, bounded_json
from .models import PluginApp, PluginGrant, PluginToken, PluginSubscription, PluginDelivery, PluginAudit
from .policy import require_enabled, app_or_404, audience, principal, audit, platform_enabled, configured_enabled, PLATFORM_SETTING
from ..models.setting import Setting
from .operations import invoke
from .tokens import authorize_code, issue
from .bundled import BUNDLED, ALL_USERS, bundled_metadata

plugins_bp = Blueprint('plugins', __name__)


def http_error(error):
    db.session.rollback()
    defaults = {400: 'Żądanie jest nieprawidłowe.', 401: 'Wymagane logowanie.',
                403: 'Brak dostępu', 404: 'Nie znaleziono zasobu.', 409: 'Konflikt danych aplikacji. Odśwież widok.',
                429: 'Zbyt wiele wywołań aplikacji. Spróbuj później.'}
    message = defaults.get(error.code, 'Wystąpił błąd serwera.') if error.description == type(error).description else error.description
    return jsonify(error=message), error.code


def conflict(error):
    db.session.rollback()
    return jsonify(error='Konflikt danych aplikacji. Odśwież widok.'), 409


plugins_bp.register_error_handler(HTTPException, http_error)
plugins_bp.register_error_handler(StaleDataError, conflict)
plugins_bp.register_error_handler(IntegrityError, conflict)


@plugins_bp.before_request
def plugin_access():
    if request.endpoint not in ('plugins.status', 'plugins.platform_settings') and request.method != 'OPTIONS':
        require_enabled()


@plugins_bp.errorhandler(ValueError)
def invalid_data(error):
    db.session.rollback()
    return jsonify(error=str(error)), 400


def data():
    if request.content_length is not None and request.content_length > 65536:
        abort(413)
    value = request.get_json(silent=True)
    if not isinstance(value, dict):
        abort(400)
    bounded_json(value)
    return value


def admin():
    user = current_user()
    if not user or user.role != 'admin':
        abort(403)
    return user


def public_app(app, user, management=False):
    grant = PluginGrant.query.filter_by(app_id=app.id, user_id=user.id, active=True).first()
    result = {'id': app.id, 'manifest': app.manifest, 'revision': app.revision,
              'installed': app.installed, 'enabled': app.enabled,
              'approved_scopes': app.approved_scopes, 'consented_scopes': grant.scopes if grant else [],
              'scope_descriptions': {key: t(SCOPES[key]) for key in app.approved_scopes}}
    result.update(bundled_metadata(app))
    if management:
        result.update(configuration=app.configuration, allowed_users=app.allowed_users,
                      all_users=ALL_USERS in app.allowed_users and result['bundled'],
                      credentials_configured=bool(app.client_secret_hash))
    return result


@plugins_bp.get('/status')
def status():
    return jsonify(enabled=platform_enabled(), api_version=1)


@plugins_bp.route('/settings', methods=['GET', 'PUT'])
def platform_settings():
    user = admin()
    locked = bool(current_app.config.get('PLUGINS_LOCKED', False))
    if request.method == 'PUT':
        payload = data()
        if set(payload) != {'enabled'} or type(payload['enabled']) is not bool:
            abort(400)
        if payload['enabled'] and locked:
            abort(409, description='Administrator serwera zablokował aplikacje. Włączenie w panelu jest niedostępne.')
        Setting.set_value(PLATFORM_SETTING, 'true' if payload['enabled'] else 'false', 'plugins')
        audit('_platform', user.id, 'platform_enable' if payload['enabled'] else 'platform_disable')
        db.session.commit()
    return jsonify(enabled=platform_enabled(), configured_enabled=configured_enabled(), server_locked=locked)


@plugins_bp.get('/catalog')
def catalog():
    user = admin()
    return jsonify(apps=[public_app(app, user, True) for app in PluginApp.query.order_by(PluginApp.id)],
                   scopes={key: t(value) for key, value in SCOPES.items()}, operations=OPERATIONS, events=sorted(EVENTS),
                   users=[{'id': u.id, 'name': ((u.first_name or '') + ' ' + (u.last_name or '')).strip(), 'email': u.email}
                          for u in User.query.filter_by(is_active=True).order_by(User.id)])


@plugins_bp.get('/apps')
def my_apps():
    user = current_user()
    return jsonify([public_app(app, user) for app in PluginApp.query.filter_by(enabled=True, installed=True)
                    if audience(app, user)])


@plugins_bp.get('/views')
def application_views():
    user = current_user()
    result = []
    for app, grant in db.session.query(PluginApp, PluginGrant).join(PluginGrant, PluginGrant.app_id == PluginApp.id).filter(
            PluginGrant.user_id == user.id, PluginGrant.active.is_(True), PluginApp.installed.is_(True), PluginApp.enabled.is_(True)):
        if not audience(app, user):
            continue
        scopes = set(app.approved_scopes) & set(grant.scopes) & set(app.manifest['scopes'])
        if not scopes:
            continue
        meta = bundled_metadata(app)
        # Bundled definitions keep their canonical manifest and existing approvals unchanged.
        views = ([{'id': p['id'], 'label': p['label'], 'placement': p['id']} for p in app.manifest['placements'] if p['slot'] == 'app.page']
                 if meta['bundled'] else app.manifest.get('views', []))
        for view in views:
            placement = next((p for p in app.manifest['placements'] if p['id'] == view['placement'] and p['slot'] == 'app.page'), None)
            if not placement or (app.manifest['type'] == 'declarative' and OPERATIONS[placement['operation']] not in scopes):
                continue
            result.append({'id': f"plugin/{app.id}/{view['id']}", 'app_id': app.id, 'view_id': view['id'],
                           'placement_id': placement['id'], 'label': view['label'], 'app_name': app.manifest['name'], **meta})
    return jsonify(sorted(result, key=lambda view: (view['app_id'], view['view_id'])))


@plugins_bp.get('/reports/capabilities')
def report_sources():
    from .reports import report_capabilities
    _, grant, _ = user_principal('zencrm-report-studio')
    from .policy import require_scope
    app = app_or_404('zencrm-report-studio')
    require_scope(app, grant, 'reports.read')
    return jsonify(report_capabilities())


@plugins_bp.get('/google-drive/status')
def google_drive_status():
    from .google_drive import status
    _, grant, _ = user_principal('zencrm-google-drive')
    return jsonify(status(grant.id))


@plugins_bp.route('/google-drive/settings', methods=['GET', 'PUT'])
def google_drive_settings():
    from .google_drive import APP_ID, admin_settings, save_admin_settings
    user = admin()
    if not bundled_metadata(app_or_404(APP_ID))['bundled']:
        abort(403)
    if request.method == 'PUT':
        result = save_admin_settings(data())
        audit(APP_ID, user.id, 'drive.configure'); db.session.commit()
    else:
        result = admin_settings()
    response = jsonify(result)
    response.headers['Cache-Control'] = 'no-store'
    return response


@plugins_bp.post('/google-drive/connect')
@auth_limit(10, seconds=60, by_user=True)
def google_drive_connect():
    from .google_drive import begin_connect, oauth_config, COOKIE, CALLBACK
    _, grant, _ = user_principal('zencrm-google-drive')
    if data():
        abort(400)
    url, state = begin_connect(grant.id)
    response = jsonify(authorization_url=url)
    response.set_cookie(COOKIE, state, max_age=600, httponly=True, samesite='Lax',
                        secure=oauth_config()['redirect_uri'].startswith('https:'), path=CALLBACK)
    return response


@plugins_bp.get('/google-drive/callback')
@auth_limit(30, seconds=60)
def google_drive_callback():
    if request.method != 'GET':
        abort(405)
    from flask import redirect
    from .google_drive import finish_connect, COOKIE, CALLBACK
    result = finish_connect()
    response = redirect('/?drive=' + result + '#plugin/zencrm-google-drive/main')
    response.delete_cookie(COOKIE, path=CALLBACK)
    return response


@plugins_bp.route('/google-drive/files', methods=['GET', 'POST'])
@auth_limit(60, seconds=60, by_user=True)
def google_drive_files():
    from .google_drive import list_files, upload_file, MAX_UPLOAD
    _, grant, _ = user_principal('zencrm-google-drive')
    if request.method == 'GET':
        if set(request.args) - {'search', 'page'} or any(len(request.args.getlist(key)) != 1 for key in request.args):
            abort(400)
        return jsonify(list_files(grant.id, request.args.get('search', ''), request.args.get('page', '')))
    if request.content_length is None or request.content_length > MAX_UPLOAD + 65536:
        abort(413)
    if set(request.files) != {'file'} or len(request.files.getlist('file')) != 1 or request.form:
        abort(400)
    file = request.files['file']
    return jsonify(upload_file(grant.id, file.filename, file.stream.read(MAX_UPLOAD + 1))), 201


@plugins_bp.delete('/google-drive/connection')
def google_drive_disconnect():
    from .google_drive import disconnect
    _, grant, _ = user_principal('zencrm-google-drive')
    return jsonify(disconnect(grant.id))


@plugins_bp.get('/store')
def store():
    user = current_user()
    # Only reviewed local definitions are visible outside the administrator-approved audience.
    apps = []
    for app in PluginApp.query.order_by(PluginApp.id):
        if bundled_metadata(app)['bundled'] or audience(app, user):
            item = public_app(app, user)
            item['available'] = audience(app, user)
            apps.append(item)
    return jsonify(apps)


@plugins_bp.post('/apps')
@auth_limit(20, by_user=True)
def register():
    user = admin()
    manifest = validate_manifest(data())
    if manifest['id'] in BUNDLED:
        abort(409)
    if db.session.get(PluginApp, manifest['id']):
        abort(409)
    if PluginApp.query.count() >= 100:
        abort(409)
    app = PluginApp(id=manifest['id'], manifest=manifest, created_by_id=user.id)
    db.session.add(app)
    audit(app.id, user.id, 'register')
    db.session.commit()
    return jsonify(public_app(app, user, True)), 201


@plugins_bp.put('/apps/<app_id>/manifest')
def update_manifest(app_id):
    user = admin()
    app = app_or_404(app_id)
    if app.id in BUNDLED:
        abort(409, description='Manifest aplikacji ZenCRM jest dostarczany z systemem i nie może być zmieniany w panelu.')
    if app.enabled:
        abort(409)
    manifest = validate_manifest(data())
    if manifest['id'] != app.id:
        abort(400)
    app.manifest = manifest
    app.revision += 1
    app.installed = False
    app.approved_scopes = []
    revoke_app(app)
    audit(app.id, user.id, 'update_manifest')
    db.session.commit()
    return jsonify(public_app(app, user, True))


def revoke_app(app):
    ids = db.select(PluginGrant.id).where(PluginGrant.app_id == app.id)
    PluginToken.query.filter(PluginToken.grant_id.in_(ids)).update({'revoked': True}, synchronize_session=False)
    PluginGrant.query.filter_by(app_id=app.id).update({'active': False}, synchronize_session=False)
    PluginSubscription.query.filter(PluginSubscription.grant_id.in_(ids)).delete(synchronize_session=False)
    PluginDelivery.query.filter(PluginDelivery.grant_id.in_(ids), PluginDelivery.status.in_(['pending', 'sending'])).update(
        {'status': 'cancelled'}, synchronize_session=False)


@plugins_bp.post('/apps/<app_id>/install')
def install(app_id):
    user = admin()
    app = app_or_404(app_id)
    payload = data()
    if set(payload) - {'scopes', 'allowed_users', 'all_users', 'configuration', 'revision'}:
        abort(400)
    if app.enabled or type(payload.get('revision')) is not int or payload.get('revision') != app.revision:
        abort(409)
    scopes = scope_list(payload.get('scopes'), app.manifest['scopes'])
    users = payload.get('allowed_users')
    all_users = payload.get('all_users', False)
    if type(all_users) is not bool or (all_users and not bundled_metadata(app)['bundled']):
        abort(400)
    if not isinstance(users, list) or (not users and not all_users) or len(users) > 500 or any(type(uid) is not int for uid in users) or len(set(users)) != len(users):
        abort(400)
    if (all_users and users) or User.query.filter(User.id.in_(users), User.is_active.is_(True)).count() != len(users):
        abort(400)
    configuration = payload.get('configuration', {})
    if not isinstance(configuration, dict):
        abort(400)
    bounded_json(configuration, 8192)
    # Configuration is not a credential vault; provider secrets belong to the external app.
    app.approved_scopes = scopes
    app.allowed_users = [ALL_USERS] if all_users else users
    app.configuration = configuration
    app.installed = True
    app.revision += 1
    revoke_app(app)
    audit(app.id, user.id, 'install')
    db.session.commit()
    return jsonify(public_app(app, user, True))


@plugins_bp.post('/apps/<app_id>/<action>')
def change_state(app_id, action):
    user = admin()
    app = app_or_404(app_id)
    if action not in ('enable', 'disable', 'uninstall'):
        abort(404)
    payload = data()
    if set(payload) != {'revision'} or type(payload['revision']) is not int or payload['revision'] != app.revision:
        abort(409)
    if action == 'enable' and not app.installed:
        abort(409)
    app.enabled = action == 'enable'
    if action != 'enable':
        revoke_app(app)
    if action == 'uninstall':
        app.installed = False
    app.revision += 1
    audit(app.id, user.id, action)
    db.session.commit()
    return jsonify(public_app(app, user, True))


@plugins_bp.post('/apps/<app_id>/credentials')
@auth_limit(10, by_user=True)
def credentials(app_id):
    user = admin()
    app = app_or_404(app_id)
    if app.manifest['type'] != 'remote':
        abort(400)
    secret, signing = secrets.token_urlsafe(48), secrets.token_urlsafe(48)
    app.client_secret_hash = generate_password_hash(secret)
    app.signing_secret_encrypted = seal(signing)
    app.revision += 1
    revoke_app(app)
    audit(app.id, user.id, 'rotate_credentials')
    db.session.commit()
    return jsonify(client_id=app.id, client_secret=secret, webhook_signing_secret=signing)


@plugins_bp.post('/apps/<app_id>/consent')
def consent(app_id):
    user = current_user()
    app = app_or_404(app_id)
    if not audience(app, user):
        abort(403)
    payload = data()
    if set(payload) - {'scopes', 'revision'} or type(payload.get('revision')) is not int or payload.get('revision') != app.revision:
        abort(409)
    scopes = scope_list(payload.get('scopes'), app.approved_scopes)
    grant = PluginGrant.query.filter_by(app_id=app.id, user_id=user.id).first()
    if grant:
        grant.scopes = scopes
        grant.active = True
        grant.revision += 1
        PluginToken.query.filter_by(grant_id=grant.id).update({'revoked': True}, synchronize_session=False)
        PluginSubscription.query.filter_by(grant_id=grant.id).delete()
        PluginDelivery.query.filter_by(grant_id=grant.id).filter(PluginDelivery.status.in_(['pending', 'sending'])).update({'status': 'cancelled'}, synchronize_session=False)
    else:
        grant = PluginGrant(app_id=app.id, user_id=user.id, scopes=scopes)
        db.session.add(grant)
    audit(app.id, user.id, 'consent')
    db.session.commit()
    return jsonify(public_app(app, user))


@plugins_bp.delete('/apps/<app_id>/consent')
def revoke_consent(app_id):
    app = app_or_404(app_id)
    user = current_user()
    grant = PluginGrant.query.filter_by(app_id=app.id, user_id=user.id).first()
    if grant:
        grant.active = False
        grant.revision += 1
        if app.id == 'zencrm-google-drive':
            from .models import PluginStorage
            PluginStorage.query.filter_by(grant_id=grant.id).filter(PluginStorage.key.startswith('_drive.')).delete(synchronize_session=False)
        PluginToken.query.filter_by(grant_id=grant.id).update({'revoked': True}, synchronize_session=False)
        PluginSubscription.query.filter_by(grant_id=grant.id).delete()
        PluginDelivery.query.filter_by(grant_id=grant.id).filter(PluginDelivery.status.in_(['pending', 'sending'])).update({'status': 'cancelled'}, synchronize_session=False)
    audit(app.id, user.id, 'revoke_consent')
    db.session.commit()
    return jsonify(ok=True)


def user_principal(app_id):
    user = current_user()
    grant = PluginGrant.query.filter_by(app_id=app_id, user_id=user.id).first()
    if not grant:
        abort(403)
    return principal(grant.id)


@plugins_bp.post('/apps/<app_id>/invoke')
@auth_limit(120, seconds=60, by_user=True, scope='plugin_ui')
def invoke_ui(app_id):
    app, grant, user = user_principal(app_id)
    payload = data()
    if set(payload) - {'operation', 'params'}:
        abort(400)
    return jsonify(invoke(app, grant, user, payload.get('operation'), payload.get('params', {})))


@plugins_bp.post('/apps/<app_id>/authorize')
@auth_limit(20, by_user=True)
def authorize(app_id):
    app, grant, user = user_principal(app_id)
    return jsonify(authorize_code(app, grant, user, data()))


@plugins_bp.post('/apps/<app_id>/personal-token')
@auth_limit(10, by_user=True)
def personal_token(app_id):
    app, grant, user = user_principal(app_id)
    payload = data()
    days = payload.get('days', 1)
    if set(payload) - {'days'} or type(days) is not int or not 1 <= days <= 30:
        abort(400)
    response = issue(app, grant, user, refresh=False, expires=datetime.utcnow() + timedelta(days=days))
    audit(app.id, user.id, 'personal_token')
    db.session.commit()
    return jsonify(response), 201


@plugins_bp.delete('/apps/<app_id>/tokens')
def revoke_tokens(app_id):
    app, grant, user = user_principal(app_id)
    PluginToken.query.filter_by(grant_id=grant.id).update({'revoked': True}, synchronize_session=False)
    audit(app.id, user.id, 'revoke_tokens')
    db.session.commit()
    return jsonify(ok=True)


@plugins_bp.get('/apps/<app_id>/audit')
def application_audit(app_id):
    admin()
    app = app_or_404(app_id)
    return jsonify([{'id': row.id, 'user_id': row.user_id, 'action': row.action, 'created_at': row.created_at.isoformat()}
                    for row in PluginAudit.query.filter_by(app_id=app.id).order_by(PluginAudit.id.desc()).limit(100)])


@plugins_bp.get('/apps/<app_id>/deliveries')
def deliveries(app_id):
    admin()
    app = app_or_404(app_id)
    ids = db.select(PluginGrant.id).where(PluginGrant.app_id == app.id)
    return jsonify([{'id': row.id, 'event_id': row.event_id, 'status': row.status, 'attempts': row.attempts,
                     'last_status': row.last_status, 'next_attempt_at': row.next_attempt_at.isoformat()}
                    for row in PluginDelivery.query.filter(PluginDelivery.grant_id.in_(ids))
                    .order_by(PluginDelivery.next_attempt_at.desc()).limit(100)])
