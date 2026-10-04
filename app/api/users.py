import os
import re
import uuid
from PIL import Image, ImageOps, UnidentifiedImageError
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.user import User
from ..models.team import Team
from ..utils.deletion import current_user, is_admin, delete_if_unlinked
from ..models.permission import Role
from ..utils.permissions import BUILTIN_ROLES
from ..utils.passwords import valid_password

users_bp = Blueprint('users', __name__)

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
AVATAR_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', '..', 'uploads', 'avatars'))
MAX_SIZE = 2 * 1024 * 1024


def remove_avatar_file(user_id, avatar_url):
    filename = (avatar_url or '').removeprefix('/api/avatars/')
    if re.fullmatch(r'user_' + str(user_id) + r'(?:_[a-f0-9]{32})?\.(?:png|jpg|jpeg|gif|webp)', filename):
        try:
            os.remove(os.path.join(AVATAR_DIR, filename))
        except FileNotFoundError:
            pass

USER_FIELDS = ('email', 'first_name', 'last_name', 'role', 'is_active', 'avatar_url', 'default_call_method', 'default_email_method', 'email_notifications')


@users_bp.before_request
@jwt_required()
def authorize_user_changes():
    actor = current_user()
    if not actor or not actor.is_active:
        return jsonify({'error': 'Brak dostępu'}), 403
    if request.method in ('GET', 'OPTIONS') or is_admin():
        return None
    own_record = (request.view_args or {}).get('user_id') == actor.id
    own_profile = request.endpoint == 'users.update_user' and own_record
    own_avatar = request.endpoint in ('users.upload_avatar', 'users.delete_avatar') and own_record
    if not (own_profile or own_avatar):
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    data = request.get_json(silent=True) or {}
    if own_profile and any(key in data for key in ('role', 'is_active', 'team_ids')):
        return jsonify({'error': 'Uprawnienia może zmieniać tylko administrator'}), 403


@users_bp.route('', methods=['GET'])
@jwt_required()
def list_users():
    users = User.query.order_by(User.first_name).all()
    return jsonify([u.to_dict() for u in users]), 200


@users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'error': 'Użytkownik nie istnieje'}), 404
    return jsonify(u.to_dict()), 200


@users_bp.route('', methods=['POST'])
@jwt_required()
def create_user():
    data = request.get_json(silent=True) or {}
    if 'default_email_method' in data and data['default_email_method'] not in ('mailto', 'crm'):
        return jsonify({'error': 'Wybierz domyślną aplikację pocztową lub pocztę w CRM'}), 400
    if not data.get('email'):
        return jsonify({'error': 'Email jest wymagany'}), 400
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email już istnieje'}), 400
    if not valid_password(data.get('password')):
        return jsonify({'error': 'Hasło musi mieć od 10 do 256 znaków'}), 400
    role = data.get('role', 'employee')
    if not isinstance(role, str) or (role not in BUILTIN_ROLES and not db.session.get(Role, role)):
        return jsonify({'error': 'Nieznana rola'}), 400
    u = User(
        email=data['email'],
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        role=role,
        is_active=data.get('is_active', True),
    )
    u.set_password(data['password'])
    if 'team_ids' in data:
        t_ids = data.get('team_ids') or []
        teams = Team.query.filter(Team.id.in_(t_ids)).all() if t_ids else []
        u.teams = teams
    db.session.add(u)
    db.session.commit()
    return jsonify(u.to_dict()), 201


@users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
def update_user(user_id):
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'error': 'Użytkownik nie istnieje'}), 404
    data = request.get_json(silent=True) or {}
    changing_email = 'email' in data and data['email'] != u.email
    changing_password = 'password' in data and bool(data['password'])
    if changing_password and not valid_password(data['password']):
        return jsonify({'error': 'Hasło musi mieć od 10 do 256 znaków'}), 400
    if current_user().id == user_id and (changing_email or changing_password):
        if not isinstance(data.get('current_password'), str) or not u.check_password(data['current_password']):
            return jsonify({'error': 'Podaj obecne hasło'}), 403
    if u.role == 'admin' and (data.get('role', 'admin') != 'admin' or data.get('is_active') is False):
        if User.query.filter_by(role='admin', is_active=True).count() <= 1:
            return jsonify({'error': 'Musi pozostać aktywny administrator'}), 409
    if 'role' in data and (not isinstance(data['role'], str) or
                           (data['role'] not in BUILTIN_ROLES and not db.session.get(Role, data['role']))):
        return jsonify({'error': 'Nieznana rola'}), 400
    if 'default_call_method' in data and data['default_call_method'] not in ('link', 'android'):
        return jsonify({'error': 'Nieprawidłowa metoda połączeń'}), 400
    if 'default_email_method' in data and data['default_email_method'] not in ('mailto', 'crm'):
        return jsonify({'error': 'Wybierz domyślną aplikację pocztową lub pocztę w CRM'}), 400
    # Avatars are set only by the upload endpoint; the profile form may keep or clear them.
    if data.get('avatar_url') not in (None, '', u.avatar_url):
        return jsonify({'error': 'Avatar can only be changed by uploading an image'}), 400
    try:
        for k in USER_FIELDS:
            if k in data:
                val = data[k]
                if k == 'email_notifications' and isinstance(val, dict):
                    import json
                    val = json.dumps(val)
                # Puste stringi traktuj jako None (żeby można było usunąć avatar)
                setattr(u, k, val if val != '' else None)
        if data.get('password'):
            u.set_password(data['password'])
        if 'team_ids' in data:
            t_ids = data.get('team_ids') or []
            teams = Team.query.filter(Team.id.in_(t_ids)).all() if t_ids else []
            u.teams = teams
        db.session.commit()
        return jsonify(u.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
def delete_user(user_id):
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'error': 'Użytkownik nie istnieje'}), 404
    if u.role == 'admin' and u.is_active and User.query.filter_by(role='admin', is_active=True).count() <= 1:
        return jsonify({'error': 'Musi pozostać aktywny administrator'}), 409
    # Users with CRM history or a phone stay as authors and owners; deactivation keeps that history.
    if not delete_if_unlinked(u):
        db.session.rollback()
        return jsonify({'error': 'This user has history in the CRM. Deactivate the account instead.'}), 409
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200


@users_bp.route('/<int:user_id>/avatar', methods=['POST'])
@jwt_required()
def upload_avatar(user_id):
    request.max_content_length = MAX_SIZE + 65536
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'error': 'Użytkownik nie istnieje'}), 404

    if 'file' not in request.files:
        return jsonify({'error': 'Brak pliku (pole "file")'}), 400
    f = request.files['file']
    if not f or not f.filename:
        return jsonify({'error': 'Nie wybrano pliku'}), 400

    ext = f.filename.rsplit('.', 1)[-1].lower() if '.' in f.filename else ''
    if ext not in ALLOWED_EXT:
        return jsonify({'error': 'Niedozwolone rozszerzenie'}), 400

    f.seek(0, os.SEEK_END)
    size = f.tell()
    f.seek(0)
    if size > MAX_SIZE:
        return jsonify({'error': 'Plik za duży (max 2 MB)'}), 400

    try:
        with Image.open(f) as source:
            if source.format not in ('PNG', 'JPEG', 'GIF', 'WEBP') or source.width * source.height > 16000000:
                raise ValueError('Wybierz poprawny obraz PNG, JPG, GIF lub WEBP.')
            source.load()
            image = ImageOps.exif_transpose(source).convert('RGBA')
            image.info.clear()
            image.thumbnail((512, 512))
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        return jsonify({'error': 'Wybierz poprawny obraz PNG, JPG, GIF lub WEBP.'}), 400

    os.makedirs(AVATAR_DIR, exist_ok=True)
    filename = f'user_{user_id}_{uuid.uuid4().hex}.png'
    image.save(os.path.join(AVATAR_DIR, filename), format='PNG')
    old_url = u.avatar_url
    u.avatar_url = f'/api/avatars/{filename}'
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        remove_avatar_file(user_id, f'/api/avatars/{filename}')
        raise
    try:
        remove_avatar_file(user_id, old_url)
    except OSError:
        current_app.logger.warning('Could not remove previous avatar for user %s', user_id)
    return jsonify({'ok': True, 'avatar_url': u.avatar_url, 'user': u.to_dict()}), 200


@users_bp.route('/<int:user_id>/avatar', methods=['DELETE'])
@jwt_required()
def delete_avatar(user_id):
    u = db.session.get(User, user_id)
    if not u:
        return jsonify({'error': 'Użytkownik nie istnieje'}), 404
    old_url = u.avatar_url
    u.avatar_url = None
    db.session.commit()
    try:
        remove_avatar_file(user_id, old_url)
    except OSError:
        current_app.logger.warning('Could not remove avatar for user %s', user_id)
    return jsonify({'ok': True}), 200
