"""Administration of roles and team action overrides."""
import re

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models.permission import Role, PermissionRule
from ..models.team import Team
from ..models.user import User
from ..utils.deletion import current_user, is_admin
from ..utils.permissions import PERMISSIONS, ensure_builtin_roles, effective_permissions
from ..utils.i18n import t

permissions_bp = Blueprint('permissions', __name__)


@permissions_bp.route('/me', methods=['GET'])
@jwt_required()
def my_permissions():
    return jsonify(effective_permissions(current_user()))


@permissions_bp.before_request
@jwt_required()
def admin_only():
    if request.endpoint == 'permissions.my_permissions':
        return None
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    return None


@permissions_bp.route('', methods=['GET'])
def list_permissions():
    ensure_builtin_roles()
    db.session.commit()
    roles = Role.query.order_by(Role.built_in.desc(), Role.name).all()
    rules = PermissionRule.query.all()
    return jsonify({
        'permissions': [{'key': key, 'label': ' · '.join(t(part) for part in label.split(' · '))} for key, label in PERMISSIONS.items()],
        'roles': [role.to_dict() for role in roles],
        'role_rules': {role.key: {r.permission: r.allowed for r in rules if r.role_key == role.key}
                       for role in roles},
        'team_rules': {str(team.id): {r.permission: r.allowed for r in rules if r.team_id == team.id}
                       for team in Team.query.all()},
    })


@permissions_bp.route('/roles', methods=['POST'])
def create_role():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name') or '').strip()
    key = re.sub(r'[^a-z0-9_]+', '_', name.lower()).strip('_')[:20]
    if not name or len(name) > 100 or not key:
        return jsonify({'error': 'Podaj poprawną nazwę roli'}), 400
    ensure_builtin_roles()
    if db.session.get(Role, key):
        return jsonify({'error': 'Rola o tej nazwie już istnieje'}), 409
    role = Role(key=key, name=name, built_in=False)
    db.session.add(role)
    db.session.commit()
    return jsonify(role.to_dict()), 201


@permissions_bp.route('/roles/<string:key>', methods=['PUT'])
def rename_role(key):
    role = db.session.get(Role, key)
    if not role:
        return jsonify({'error': 'Rola nie istnieje'}), 404
    if role.built_in:
        return jsonify({'error': 'Nazwy roli systemowej nie można zmienić'}), 400
    name = str((request.get_json(silent=True) or {}).get('name') or '').strip()
    if not name or len(name) > 100:
        return jsonify({'error': 'Podaj poprawną nazwę roli'}), 400
    role.name = name
    db.session.commit()
    return jsonify(role.to_dict())


@permissions_bp.route('/roles/<string:key>', methods=['DELETE'])
def delete_role(key):
    role = db.session.get(Role, key)
    if not role:
        return jsonify({'error': 'Rola nie istnieje'}), 404
    if role.built_in or User.query.filter_by(role=key).first():
        return jsonify({'error': 'Rola systemowa lub przypisana użytkownikom nie może zostać usunięta'}), 409
    PermissionRule.query.filter_by(role_key=key).delete()
    db.session.delete(role)
    db.session.commit()
    return jsonify({'ok': True})


def _save_rules(subject, value):
    data = request.get_json(silent=True) or {}
    rules = data.get('rules')
    if not isinstance(rules, dict) or any(key not in PERMISSIONS or (state is not True and state is not False and state is not None)
                                           for key, state in rules.items()):
        return jsonify({'error': 'Nieprawidłowa lista uprawnień'}), 400
    for key, state in rules.items():
        filters = {subject: value, 'permission': key}
        rule = PermissionRule.query.filter_by(**filters).first()
        if state is None:
            if rule:
                db.session.delete(rule)
        elif rule:
            rule.allowed = state
        else:
            db.session.add(PermissionRule(**filters, allowed=state))
    db.session.commit()
    return jsonify({'ok': True})


@permissions_bp.route('/roles/<string:key>/rules', methods=['PUT'])
def save_role_rules(key):
    if not db.session.get(Role, key):
        return jsonify({'error': 'Rola nie istnieje'}), 404
    if key == 'admin':
        return jsonify({'error': 'Administrator zawsze ma pełny dostęp'}), 400
    return _save_rules('role_key', key)


@permissions_bp.route('/teams/<int:team_id>/rules', methods=['PUT'])
def save_team_rules(team_id):
    if not db.session.get(Team, team_id):
        return jsonify({'error': 'Zespół nie istnieje'}), 404
    return _save_rules('team_id', team_id)
