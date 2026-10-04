from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.email_template import EmailTemplate, DEFAULT_TEMPLATES
from ..models.setting import Setting
from ..services.email_service import get_smtp_config, test_smtp_connection
from ..utils.deletion import is_admin
from ..utils.secret_storage import unseal

emails_bp = Blueprint('emails', __name__)


@emails_bp.route('/templates', methods=['GET'])
@jwt_required()
def list_templates():
    """Zwraca listę wszystkich szablonów e-mail."""
    # Upewnij się, że domyślne są w bazie
    EmailTemplate.seed_defaults()
    templates = EmailTemplate.query.order_by(EmailTemplate.id.asc()).all()
    return jsonify([t.to_dict() for t in templates]), 200


@emails_bp.route('/templates/<string:key>', methods=['GET'])
@jwt_required()
def get_template(key):
    """Zwraca pojedynczy szablon e-mail."""
    t = EmailTemplate.get_by_key(key)
    if not t:
        return jsonify({'error': 'Szablon nie istnieje'}), 404
    return jsonify(t.to_dict()), 200


@emails_bp.route('/templates/<string:key>', methods=['PUT'])
@jwt_required()
def update_template(key):
    """Aktualizuje temat i treść szablonu e-mail (tylko administrator)."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    t = EmailTemplate.get_by_key(key)
    if not t:
        return jsonify({'error': 'Szablon nie istnieje'}), 404
    data = request.get_json(silent=True) or {}
    if 'subject' in data:
        t.subject = (data['subject'] or '').strip()
    if 'body_html' in data:
        t.body_html = (data['body_html'] or '').strip()
    db.session.commit()
    return jsonify(t.to_dict()), 200


@emails_bp.route('/templates/<string:key>/reset', methods=['POST'])
@jwt_required()
def reset_template(key):
    """Przywraca szablon e-mail do wartości domyślnej."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    t = EmailTemplate.get_by_key(key)
    default = next((d for d in DEFAULT_TEMPLATES if d['key'] == key), None)
    if not default:
        return jsonify({'error': 'Brak domyślnego szablonu dla tego klucza'}), 404
    if not t:
        t = EmailTemplate(key=key, name=default['name'], category=default['category'])
        db.session.add(t)
    t.subject = default['subject']
    t.body_html = default['body_html']
    t.variables = default.get('variables', '')
    db.session.commit()
    return jsonify(t.to_dict()), 200


@emails_bp.route('/smtp-config', methods=['GET'])
@emails_bp.route('/smtp', methods=['GET'])
@jwt_required()
def get_smtp_settings():
    """Pobiera konfigurację SMTP."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    cfg = get_smtp_config()
    has_pwd = bool(cfg.get('password'))
    return jsonify({
        'enabled': cfg.get('enabled', False),
        'smtp_enabled': cfg.get('enabled', False),
        'host': cfg.get('host', ''),
        'smtp_host': cfg.get('host', ''),
        'port': cfg.get('port', 587),
        'smtp_port': cfg.get('port', 587),
        'user': cfg.get('user', ''),
        'smtp_user': cfg.get('user', ''),
        'has_password': has_pwd,
        'smtp_password_set': has_pwd,
        'from_email': cfg.get('from_email', ''),
        'smtp_from_email': cfg.get('from_email', ''),
        'from_name': cfg.get('from_name', ''),
        'smtp_from_name': cfg.get('from_name', ''),
        'encryption': cfg.get('encryption', 'tls'),
        'smtp_encryption': cfg.get('encryption', 'tls'),
    }), 200


@emails_bp.route('/smtp-config', methods=['PUT'])
@emails_bp.route('/smtp', methods=['PUT'])
@jwt_required()
def save_smtp_settings():
    """Zapisuje konfigurację SMTP."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    data = request.get_json(silent=True) or {}

    enabled_val = data.get('enabled') if 'enabled' in data else data.get('smtp_enabled')
    if enabled_val is not None:
        Setting.set_value('smtp_enabled', 'true' if enabled_val else 'false', 'smtp')

    host_val = data.get('host') if 'host' in data else data.get('smtp_host')
    if host_val is not None:
        Setting.set_value('smtp_host', str(host_val or '').strip(), 'smtp')

    port_val = data.get('port') if 'port' in data else data.get('smtp_port')
    if port_val is not None:
        Setting.set_value('smtp_port', str(port_val or '587').strip(), 'smtp')

    user_val = data.get('user') if 'user' in data else data.get('smtp_user')
    if user_val is not None:
        Setting.set_value('smtp_user', str(user_val or '').strip(), 'smtp')

    pwd_val = data.get('password') if 'password' in data else data.get('smtp_password')
    if pwd_val:
        Setting.set_value('smtp_password', str(pwd_val), 'smtp')

    from_email_val = data.get('from_email') if 'from_email' in data else data.get('smtp_from_email')
    if from_email_val is not None:
        Setting.set_value('smtp_from_email', str(from_email_val or '').strip(), 'smtp')

    from_name_val = data.get('from_name') if 'from_name' in data else data.get('smtp_from_name')
    if from_name_val is not None:
        Setting.set_value('smtp_from_name', str(from_name_val or '').strip(), 'smtp')

    enc_val = data.get('encryption') if 'encryption' in data else data.get('smtp_encryption')
    if enc_val is not None:
        Setting.set_value('smtp_encryption', str(enc_val or 'tls').strip(), 'smtp')

    db.session.commit()
    return get_smtp_settings()


@emails_bp.route('/test-smtp', methods=['POST'])
@emails_bp.route('/smtp/test', methods=['POST'])
@jwt_required()
def test_smtp():
    """Testuje połączenie SMTP wysyłając próbny e-mail."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    data = request.get_json(silent=True) or {}
    test_to = (data.get('test_to') or data.get('to_email') or '').strip()
    if not test_to or '@' not in test_to:
        return jsonify({'error': 'Podaj poprawny adres e-mail do testu'}), 400

    cfg = {
        'host': data.get('host') or data.get('smtp_host') or Setting.get_value('smtp_host', ''),
        'port': data.get('port') or data.get('smtp_port') or Setting.get_value('smtp_port', '587'),
        'user': data.get('user') or data.get('smtp_user') or Setting.get_value('smtp_user', ''),
        'password': data.get('password') or data.get('smtp_password') or unseal(Setting.get_value('smtp_password', '') or ''),
        'from_email': data.get('from_email') or data.get('smtp_from_email') or Setting.get_value('smtp_from_email', ''),
        'from_name': data.get('from_name') or data.get('smtp_from_name') or Setting.get_value('smtp_from_name', 'ZenCRM'),
        'encryption': data.get('encryption') or data.get('smtp_encryption') or Setting.get_value('smtp_encryption', 'tls'),
    }
    if not (data.get('password') or data.get('smtp_password')):
        # Saved credentials may only be tested against the saved server.
        cfg = get_smtp_config()

    ok, message = test_smtp_connection(cfg, test_to)
    if not ok:
        return jsonify({'error': message}), 400
    return jsonify({'ok': True, 'message': message}), 200
