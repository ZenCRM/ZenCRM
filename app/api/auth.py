from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)
from ..extensions import db
from ..models.user import User

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json() or {}
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email i hasło są wymagane'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email już istnieje'}), 400
    user = User(
        email=data['email'],
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        role='employee',
    )
    user.set_password(data['password'])
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json() or {}
    user = User.query.filter_by(email=data.get('email')).first()
    if not user or not user.check_password(data.get('password', '')):
        return jsonify({'error': 'Nieprawidłowe dane logowania'}), 401

    identity = str(user.id)
    return jsonify({
        'access_token':  create_access_token(identity=identity),
        'refresh_token': create_refresh_token(identity=identity),
        'user':          user.to_dict(),
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'error': 'Podaj adres e-mail'}), 400
    user = User.query.filter(User.email.ilike(email)).first()
    if user:
        import secrets, string
        chars = string.ascii_letters + string.digits
        temp_password = ''.join(secrets.choice(chars) for _ in range(10))
        user.set_password(temp_password)
        db.session.commit()

        try:
            from ..services.email_service import send_notification
            from ..models.setting import Setting
            admin_email = Setting.get_value('company_email', 'admin@zencrm.pl')
            login_url = request.host_url.rstrip('/')
            send_notification('password_reset', user.email, {
                'user_name': f"{user.first_name} {user.last_name}".strip() or user.email,
                'temp_password': temp_password,
                'login_url': login_url,
                'admin_email': admin_email,
            }, recipient_name=user.first_name)
        except Exception:
            pass

    return jsonify({
        'ok': True,
        'message': 'Jeśli konto z tym adresem istnieje, instrukcja wraz z hasłem tymczasowym została wysłana na Twój adres e-mail.'
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def me():
    """Zwraca aktualne dane zalogowanego użytkownika (świeże z bazy)."""
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Użytkownik nie istnieje'}), 404
    return jsonify(user.to_dict()), 200


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    identity = get_jwt_identity()
    return jsonify({'access_token': create_access_token(identity=identity)}), 200
