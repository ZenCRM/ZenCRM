from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)
from ..extensions import db
from ..models.user import User
from ..models.auth_security import PasswordReset
from ..utils.auth_limits import auth_limit
from datetime import datetime, timedelta
import hashlib
import secrets
from markupsafe import escape
from ..utils.i18n import t

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/setup-status', methods=['GET'])
def setup_status():
    has_users = User.query.first() is not None
    return jsonify({
        'needs_setup': not has_users,
        'has_users': has_users
    }), 200


@auth_bp.route('/setup', methods=['POST'])
@auth_limit(10)
def setup_admin():
    if User.query.first() is not None:
        return jsonify({'error': t('Konfiguracja początkowa została już zakończona')}), 403

    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    first_name = (data.get('first_name') or '').strip()
    last_name = (data.get('last_name') or '').strip()

    if not email or '@' not in email or '.' not in email.split('@')[-1]:
        return jsonify({'error': t('Podaj poprawny adres e-mail')}), 400
    if not isinstance(password, str) or len(password) < 8 or len(password) > 256:
        return jsonify({'error': t('Hasło musi mieć co najmniej 8 znaków')}), 400

    admin = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        role='admin',
        is_active=True
    )
    admin.set_password(password)
    db.session.add(admin)
    db.session.commit()

    identity = str(admin.id)
    return jsonify({
        'ok': True,
        'message': t('Konto administratora zostało pomyślnie utworzone'),
        'access_token': create_access_token(identity=identity),
        'refresh_token': create_refresh_token(identity=identity),
        'user': admin.to_dict(),
    }), 201


@auth_bp.route('/register', methods=['POST'])
@jwt_required()
def register():
    from ..utils.deletion import is_admin
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
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
@auth_limit(30)
def login():
    data = request.get_json() or {}
    user = User.query.filter_by(email=data.get('email')).first()
    if not user or not user.is_active or not user.check_password(data.get('password', '')):
        return jsonify({'error': 'Nieprawidłowe dane logowania'}), 401

    identity = str(user.id)
    return jsonify({
        'access_token':  create_access_token(identity=identity),
        'refresh_token': create_refresh_token(identity=identity),
        'user':          user.to_dict(),
    }), 200


@auth_bp.route('/forgot-password', methods=['POST'])
@auth_limit(5)
def forgot_password():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip().lower()
    if not email:
        return jsonify({'error': 'Podaj adres e-mail'}), 400
    user = User.query.filter(User.email.ilike(email)).first()
    if user and user.is_active:
        token = secrets.token_urlsafe(24)
        PasswordReset.query.filter(PasswordReset.expires_at <= datetime.utcnow()).delete()
        db.session.add(PasswordReset(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                                    user_id=user.id, password_version=user.password_hash,
                                    expires_at=datetime.utcnow() + timedelta(minutes=15)))
        db.session.commit()

        try:
            from ..services.email_service import send_email
            send_email(user.email, t('Resetowanie hasła'),
                       '<p>' + escape(t('Wpisz ten kod w formularzu resetowania hasła. Kod jest ważny przez 15 minut.')) +
                       '</p><p><code>' + escape(token) + '</code></p>')
        except Exception:
            pass

    return jsonify({
        'ok': True,
        'message': t('Jeśli konto istnieje, wysłaliśmy kod resetowania na jego adres e-mail.')
    }), 200


@auth_bp.route('/reset-password', methods=['POST'])
@auth_limit(10)
def reset_password():
    data = request.get_json(silent=True) or {}
    token = data.get('token', '')
    password = data.get('password', '')
    if not isinstance(token, str) or not isinstance(password, str) or not 10 <= len(password) <= 256:
        return jsonify(error=t('Podaj kod i hasło o długości od 10 do 256 znaków.')), 400
    reset = db.session.get(PasswordReset, hashlib.sha256(token.encode()).hexdigest())
    user = db.session.get(User, reset.user_id) if reset else None
    if not reset or reset.expires_at <= datetime.utcnow() or not user or not user.is_active or user.password_hash != reset.password_version:
        return jsonify(error=t('Kod resetowania jest nieprawidłowy lub wygasł.')), 400
    from werkzeug.security import generate_password_hash
    changed = User.query.filter_by(id=user.id, password_hash=reset.password_version).update(
        {'password_hash': generate_password_hash(password)}, synchronize_session=False)
    if not changed:
        db.session.rollback()
        return jsonify(error=t('Kod resetowania jest nieprawidłowy lub wygasł.')), 400
    PasswordReset.query.filter_by(user_id=user.id).delete(synchronize_session=False)
    db.session.commit()
    return jsonify(ok=True, message=t('Hasło zostało zmienione. Zaloguj się ponownie.'))


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
