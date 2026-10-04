import os
from flask import Blueprint, request, jsonify, send_from_directory, abort, current_app
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.setting import Setting
from ..utils.settings_defaults import seed_defaults, _category
from ..utils.deletion import is_admin, current_user

settings_bp = Blueprint('settings', __name__)

BRAND_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'uploads', 'branding'))
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
MAX_SIZE = 2 * 1024 * 1024

# Explicit lists prevent newly added credentials from becoming public.
PUBLIC_KEYS = frozenset({
    'brand_name', 'brand_color_primary', 'brand_color_secondary',
    'brand_logo_light', 'brand_logo_dark', 'brand_logo_size', 'brand_favicon',
    'login_bg_type', 'login_bg_color', 'login_bg_color2', 'login_bg_image',
    'login_welcome_text', 'login_footer', 'login_show_logo',
})
UI_KEYS = PUBLIC_KEYS | frozenset({
    'gus_enabled', 'client_company_provider', 'client_statuses', 'client_metrics',
    'ui_template', 'ui_hero_background', 'ui_classic_sidebar',
    'ui_detail_client', 'ui_detail_lead', 'ui_detail_task', 'ui_detail_service',
    'ui_show_footer', 'ui_footer_text', 'ui_dark_default',
    'lead_stages', 'task_stages', 'required_standard_fields', 'standard_field_labels',
    'menu_permissions', 'lead_sources', 'lead_webhook_enabled', 'lead_webhook_token',
})


@settings_bp.after_request
def prevent_settings_cache(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


SECRET_KEYS = frozenset({'smtp_password', 'gus_api_key'})


def settings_values(items):
    values = {s.key: ('' if s.key in SECRET_KEYS else s.value) for s in items}
    from ..services.company_lookup import provider
    values['client_company_provider'] = provider()
    values['gus_api_key_set'] = bool(Setting.get_value('gus_api_key', '') or current_app.config.get('GUS_API_KEY', ''))
    return values


def selected_settings(keys):
    seed_defaults()
    items = Setting.query.filter(Setting.key.in_(keys)).all()
    res = {s.key: s.value for s in items}
    if 'client_company_provider' in keys:
        from ..services.company_lookup import provider
        res['client_company_provider'] = provider()
    if not is_admin() and 'lead_webhook_token' in res:
        del res['lead_webhook_token']
    return jsonify(res), 200


@settings_bp.route('/lead-webhook/generate-token', methods=['POST'])
@jwt_required()
def generate_lead_webhook_token():
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    import secrets
    new_token = f'zen_lead_{secrets.token_hex(16)}'
    Setting.set_value('lead_webhook_token', new_token, 'leads')
    db.session.commit()
    return jsonify({'token': new_token}), 200


@settings_bp.route('/public', methods=['GET'])
def public_settings():
    from ..models.user import User
    seed_defaults()
    items = Setting.query.filter(Setting.key.in_(PUBLIC_KEYS)).all()
    data = {s.key: s.value for s in items}
    data['needs_setup'] = (User.query.first() is None)
    return jsonify(data), 200


@settings_bp.route('/ui', methods=['GET'])
@jwt_required()
def ui_settings():
    user = current_user()
    if user is None or not user.is_active:
        abort(403)
    return selected_settings(UI_KEYS)


@settings_bp.route('', methods=['GET'])
@jwt_required()
def list_settings():
    """All settings are restricted to active administrators."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    seed_defaults()
    items = Setting.query.all()
    return jsonify(settings_values(items)), 200


@settings_bp.route('/full', methods=['GET'])
@jwt_required()
def list_full():
    """Pelna lista z metadanymi - tylko admin."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    items = Setting.query.order_by(Setting.category, Setting.key).all()
    values = settings_values(items)
    return jsonify([{**s.to_dict(), 'value': '', 'configured': values['gus_api_key_set']} if s.key == 'gus_api_key' else ({**s.to_dict(), 'value': ''} if s.key in SECRET_KEYS else s.to_dict()) for s in items]), 200


@settings_bp.route('', methods=['PUT'])
@jwt_required()
def update_settings():
    """Aktualizuje ustawienia. Body: {key: value, ...}"""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403

    data = request.get_json(silent=True) or {}
    try:
        if 'ui_template' in data and data['ui_template'] not in ('classic', 'modern'):
            raise ValueError('Wybierz dostępny szablon interfejsu.')
        if 'ui_classic_sidebar' in data and data['ui_classic_sidebar'] not in ('light', 'dark'):
            raise ValueError('Wybierz jasny lub ciemny pasek boczny.')
        if 'ui_hero_background' in data and data['ui_hero_background'] not in ('random', 'mountains', 'forest', 'coast'):
            raise ValueError('Wybierz dostępne tło sekcji hero.')
        for kind in ('client', 'lead', 'task', 'service'):
            key = 'ui_detail_' + kind
            if key in data and data[key] not in ('full', 'compact'):
                raise ValueError('Wybierz pełny lub skrócony widok rekordu.')
        if 'lead_stages' in data:
            import json
            from ..utils.lead_stages import validate_stages
            data['lead_stages'] = json.dumps(validate_stages(json.loads(data['lead_stages'])), ensure_ascii=False)
        if 'task_stages' in data:
            import json
            from ..utils.task_stages import validate_task_stages
            data['task_stages'] = json.dumps(validate_task_stages(json.loads(data['task_stages'])), ensure_ascii=False)
        if 'client_statuses' in data:
            import json
            from ..utils.client_statuses import validate_statuses
            data['client_statuses'] = json.dumps(validate_statuses(json.loads(data['client_statuses'])), ensure_ascii=False)
        if 'client_metrics' in data:
            import json
            from ..utils.client_metrics import validate_metrics
            from ..utils.client_statuses import get_statuses
            statuses = json.loads(data['client_statuses']) if 'client_statuses' in data else get_statuses()
            data['client_metrics'] = json.dumps(validate_metrics(json.loads(data['client_metrics']), statuses))
        if 'client_company_provider' in data:
            if data['client_company_provider'] not in ('off', 'gus', 'mf'):
                raise ValueError('Wybierz poprawną wyszukiwarkę firm.')
            data['gus_enabled'] = 'true' if data['client_company_provider'] == 'gus' else 'false'
        elif 'gus_enabled' in data:
            data['client_company_provider'] = 'gus' if data['gus_enabled'] in (True, 'true') else 'off'
        if 'gus_enabled' in data:
            value = data['gus_enabled']
            if value not in (True, False, 'true', 'false'):
                raise ValueError('Niepoprawny stan wyszukiwarki GUS.')
            data['gus_enabled'] = 'true' if value is True or value == 'true' else 'false'
        if 'gus_api_key' in data and not isinstance(data['gus_api_key'], str):
            raise ValueError('Klucz API GUS musi być tekstem.')
        if 'gus_api_key' in data:
            data['gus_api_key'] = data['gus_api_key'].strip()
        for key, value in data.items():
            if key == 'gus_api_key_set':
                continue
            if key in SECRET_KEYS and not value:
                continue
            Setting.set_value(key, str(value) if value is not None else '', _category(key))
        db.session.commit()
        items = Setting.query.all()
        return jsonify(settings_values(items)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@settings_bp.route('/reset', methods=['POST'])
@jwt_required()
def reset_settings():
    """Przywraca domyslne."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    from ..utils.settings_defaults import DEFAULTS
    try:
        from ..utils.client_statuses import validate_statuses, DEFAULT_STATUSES
        validate_statuses(DEFAULT_STATUSES)
        for key, value in DEFAULTS.items():
            Setting.set_value(key, str(value), _category(key))
        db.session.commit()
        return jsonify({'ok': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@settings_bp.route('/upload-logo', methods=['POST'])
@jwt_required()
def upload_logo():
    """Upload logo firmowego. Pole 'file' + 'variant' = light|dark|favicon."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403

    if 'file' not in request.files:
        return jsonify({'error': 'Brak pliku'}), 400

    f = request.files['file']
    if not f or not f.filename:
        return jsonify({'error': 'Nie wybrano pliku'}), 400

    variant = request.form.get('variant', 'light')
    if variant not in ('light', 'dark', 'favicon', 'helpdesk'):
        return jsonify({'error': 'Nieznany wariant'}), 400

    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED_EXT:
        return jsonify({'error': 'Niedozwolone rozszerzenie'}), 400

    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    if size > MAX_SIZE:
        return jsonify({'error': 'Plik za duzy (max 2 MB)'}), 400

    os.makedirs(BRAND_DIR, exist_ok=True)
    filename = f'{variant}.{ext}'

    for old_ext in ALLOWED_EXT:
        old = os.path.join(BRAND_DIR, f'{variant}.{old_ext}')
        if os.path.exists(old) and old_ext != ext:
            try:
                os.remove(old)
            except OSError:
                pass

    f.save(os.path.join(BRAND_DIR, filename))

    key = {'light': 'brand_logo_light', 'dark': 'brand_logo_dark', 'favicon': 'brand_favicon', 'helpdesk': 'helpdesk_logo'}[variant]
    url = f'/api/settings/branding/{filename}'
    Setting.set_value(key, url, 'branding')
    db.session.commit()

    return jsonify({'ok': True, 'url': url, 'key': key}), 200


@settings_bp.route('/branding/<path:filename>', methods=['GET'])
def serve_branding(filename):
    """Publiczne serwowanie plikow brandingowych."""
    if '..' in filename or filename.startswith('/'):
        abort(404)
    full = os.path.join(BRAND_DIR, filename)
    if not os.path.exists(full):
        abort(404)
    return send_from_directory(BRAND_DIR, filename)
