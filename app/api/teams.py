from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.team import Team
from ..models.user import User
from ..models.permission import PermissionRule
from ..utils.deletion import current_user, is_admin

teams_bp = Blueprint('teams', __name__)


@teams_bp.before_request
@jwt_required()
def authorize():
    user = current_user()
    if not user or not user.is_active:
        abort(403)
    if request.method not in ('GET', 'OPTIONS') and not is_admin():
        abort(403)


@teams_bp.route('', methods=['GET'])
def list_teams():
    teams = Team.query.order_by(Team.name.asc()).all()
    return jsonify([t.to_dict() for t in teams]), 200


@teams_bp.route('/<int:team_id>', methods=['GET'])
def get_team(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        return jsonify({'error': 'Zespół nie istnieje'}), 404
    return jsonify(team.to_dict()), 200


@teams_bp.route('', methods=['POST'])
def create_team():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'error': 'Nazwa zespołu jest wymagana'}), 400

    team = Team(
        name=name,
        description=data.get('description'),
        color=data.get('color') or '#018bfc',
        leader_id=data.get('leader_id') or None,
    )

    member_ids = data.get('member_ids') or []
    if member_ids:
        users = User.query.filter(User.id.in_(member_ids)).all()
        team.members = users

    db.session.add(team)
    db.session.commit()
    return jsonify(team.to_dict()), 201


@teams_bp.route('/<int:team_id>', methods=['PUT'])
def update_team(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        return jsonify({'error': 'Zespół nie istnieje'}), 404

    data = request.get_json(silent=True) or {}
    if 'name' in data:
        name = str(data.get('name', '')).strip()
        if not name:
            return jsonify({'error': 'Nazwa zespołu jest wymagana'}), 400
        team.name = name

    if 'description' in data:
        team.description = data.get('description')
    if 'color' in data:
        team.color = data.get('color') or '#018bfc'
    if 'leader_id' in data:
        team.leader_id = data.get('leader_id') or None

    if 'member_ids' in data:
        member_ids = data.get('member_ids') or []
        users = User.query.filter(User.id.in_(member_ids)).all() if member_ids else []
        team.members = users

    db.session.commit()
    return jsonify(team.to_dict()), 200


@teams_bp.route('/<int:team_id>', methods=['DELETE'])
def delete_team(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        return jsonify({'error': 'Zespół nie istnieje'}), 404

    PermissionRule.query.filter_by(team_id=team_id).delete()
    db.session.delete(team)
    db.session.commit()
    return jsonify({'ok': True, 'id': team_id}), 200


@teams_bp.route('/<int:team_id>/members', methods=['POST'])
def add_member(team_id):
    team = db.session.get(Team, team_id)
    if not team:
        return jsonify({'error': 'Zespół nie istnieje'}), 404

    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id jest wymagany'}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Użytkownik nie istnieje'}), 404

    if user not in team.members:
        team.members.append(user)
        db.session.commit()

    return jsonify(team.to_dict()), 200


@teams_bp.route('/<int:team_id>/members/<int:user_id>', methods=['DELETE'])
def remove_member(team_id, user_id):
    team = db.session.get(Team, team_id)
    if not team:
        return jsonify({'error': 'Zespół nie istnieje'}), 404

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'Użytkownik nie istnieje'}), 404

    if user in team.members:
        team.members.remove(user)
        db.session.commit()

    return jsonify(team.to_dict()), 200
