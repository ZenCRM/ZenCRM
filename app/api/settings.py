import os
from flask import Blueprint, request, jsonify, send_from_directory, abort
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.setting import Setting
from ..utils.settings_defaults import seed_defaults, _category
from ..utils.deletion import is_admin

settings_bp = Blueprint('settings', __name__)

BRAND_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'uploads', 'branding'))
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'svg', 'webp'}
MAX_SIZE = 2 * 1024 * 1024


@settings_bp.route('', methods=['GET'])
def list_settings():
    """Publiczne - zwraca wszystkie ustawienia jako dict."""
    seed_defaults()
    items = Setting.query.all()
    return jsonify({s.key: s.value for s in items}), 200


@settings_bp.route('/full', methods=['GET'])
@jwt_required()
def list_full():
    """Pelna lista z metadanymi - tylko admin."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    items = Setting.query.order_by(Setting.category, Setting.key).all()
    return jsonify([s.to_dict() for s in items]), 200


@settings_bp.route('', methods=['PUT'])
@jwt_required()
def update_settings():
    """Aktualizuje ustawienia. Body: {key: value, ...}"""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403

    data = request.get_json(silent=True) or {}
    try:
        if 'lead_stages' in data:
            import json
            from ..utils.lead_stages import validate_stages
            data['lead_stages'] = json.dumps(validate_stages(json.loads(data['lead_stages'])), ensure_ascii=False)
        if 'task_stages' in data:
            import json
            from ..utils.task_stages import validate_task_stages
            data['task_stages'] = json.dumps(validate_task_stages(json.loads(data['task_stages'])), ensure_ascii=False)
        for key, value in data.items():
            Setting.set_value(key, str(value) if value is not None else '', _category(key))
        db.session.commit()
        items = Setting.query.all()
        return jsonify({s.key: s.value for s in items}), 200
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
