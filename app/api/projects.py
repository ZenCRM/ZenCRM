from datetime import datetime, date
from decimal import Decimal
import json
from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.project import Project, ProjectMember
from ..models.task import Task
from ..models.user import User
from ..utils.activity import log_activity
from ..utils.deletion import current_user, is_admin

projects_bp = Blueprint('projects', __name__)


@projects_bp.before_request
@jwt_required()
def authorize():
    user = current_user()
    if not user or not user.is_active:
        abort(403)


@projects_bp.route('', methods=['GET'])
def list_projects():
    query = Project.query.filter(Project.deleted_at.is_(None))
    client_id = request.args.get('client_id', type=int)
    if client_id is not None:
        query = query.filter(Project.client_id == client_id)
    manager_id = request.args.get('manager_id', type=int)
    if manager_id is not None:
        query = query.filter(Project.manager_id == manager_id)
    status = request.args.get('status')
    if status:
        query = query.filter(Project.status == status)

    projects = query.order_by(Project.id.desc()).all()
    return jsonify([p.to_dict(include_tasks=False) for p in projects]), 200


@projects_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    project = Project.query.filter_by(id=project_id, deleted_at=None).first_or_404()
    return jsonify(project.to_dict(include_tasks=True)), 200


@projects_bp.route('', methods=['POST'])
def create_project():
    data = request.get_json(silent=True) or {}
    name = str(data.get('name', '')).strip()
    if not name:
        return jsonify({'error': 'Nazwa projektu jest wymagana'}), 400

    try:
        start_date = None
        if data.get('start_date'):
            start_date = date.fromisoformat(str(data['start_date'])[:10])
        end_date = None
        if data.get('end_date'):
            end_date = date.fromisoformat(str(data['end_date'])[:10])

        budget = 0
        if data.get('budget'):
            budget = Decimal(str(data['budget']).replace(',', '.').strip())

        project = Project(
            name=name,
            description=data.get('description', ''),
            status=data.get('status', 'in_progress') or 'in_progress',
            client_id=int(data['client_id']) if data.get('client_id') else None,
            manager_id=int(data['manager_id']) if data.get('manager_id') else None,
            budget=budget,
            start_date=start_date,
            end_date=end_date,
        )

        if data.get('task_stages'):
            if isinstance(data['task_stages'], (list, dict)):
                project.task_stages = json.dumps(data['task_stages'], ensure_ascii=False)
            else:
                project.task_stages = str(data['task_stages'])

        db.session.add(project)
        db.session.flush()

        # Members
        member_ids = data.get('member_ids') or []
        for uid in member_ids:
            try:
                user_id = int(uid)
                if not ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first():
                    db.session.add(ProjectMember(project_id=project.id, user_id=user_id))
            except (ValueError, TypeError):
                pass

        log_activity('project', project.id, 'created', 'Utworzono projekt')
        db.session.commit()
        return jsonify(project.to_dict(include_tasks=True)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@projects_bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    project = Project.query.filter_by(id=project_id, deleted_at=None).first_or_404()
    data = request.get_json(silent=True) or {}

    try:
        if 'name' in data:
            name = str(data['name']).strip()
            if not name:
                return jsonify({'error': 'Nazwa projektu jest wymagana'}), 400
            project.name = name

        if 'description' in data:
            project.description = data['description']

        if 'status' in data:
            project.status = data['status']

        if 'client_id' in data:
            project.client_id = int(data['client_id']) if data['client_id'] else None

        if 'manager_id' in data:
            project.manager_id = int(data['manager_id']) if data['manager_id'] else None

        if 'budget' in data:
            project.budget = Decimal(str(data['budget']).replace(',', '.').strip()) if data['budget'] is not None else 0

        if 'start_date' in data:
            project.start_date = date.fromisoformat(str(data['start_date'])[:10]) if data['start_date'] else None

        if 'end_date' in data:
            project.end_date = date.fromisoformat(str(data['end_date'])[:10]) if data['end_date'] else None

        if 'task_stages' in data:
            if isinstance(data['task_stages'], (list, dict)):
                project.task_stages = json.dumps(data['task_stages'], ensure_ascii=False)
            else:
                project.task_stages = str(data['task_stages']) if data['task_stages'] else None

        if 'member_ids' in data and isinstance(data['member_ids'], list):
            target_ids = {int(x) for x in data['member_ids'] if x}
            current_members = ProjectMember.query.filter_by(project_id=project.id).all()
            current_ids = {m.user_id for m in current_members}

            # Remove removed
            for m in current_members:
                if m.user_id not in target_ids:
                    db.session.delete(m)

            # Add new
            for uid in target_ids:
                if uid not in current_ids:
                    db.session.add(ProjectMember(project_id=project.id, user_id=uid))

        log_activity('project', project.id, 'updated', 'Zaktualizowano projekt')
        db.session.commit()
        return jsonify(project.to_dict(include_tasks=True)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    project = Project.query.filter_by(id=project_id, deleted_at=None).first_or_404()
    project.deleted_at = datetime.utcnow()
    log_activity('project', project.id, 'deleted', 'Usunięto projekt')
    db.session.commit()
    return jsonify({'ok': True}), 200


@projects_bp.route('/<int:project_id>/stages', methods=['PUT'])
def update_project_stages(project_id):
    project = Project.query.filter_by(id=project_id, deleted_at=None).first_or_404()
    data = request.get_json(silent=True) or {}
    stages = data.get('stages')
    if stages is not None:
        if isinstance(stages, (list, dict)):
            project.task_stages = json.dumps(stages, ensure_ascii=False)
        else:
            project.task_stages = str(stages)
        db.session.commit()
    return jsonify(project.to_dict(include_tasks=True)), 200


@projects_bp.route('/<int:project_id>/members', methods=['POST'])
def add_member(project_id):
    project = Project.query.filter_by(id=project_id, deleted_at=None).first_or_404()
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id')
    role = data.get('role', 'member')
    if not user_id:
        return jsonify({'error': 'Brak identyfikatora użytkownika'}), 400

    user_id = int(user_id)
    member = ProjectMember.query.filter_by(project_id=project.id, user_id=user_id).first()
    if not member:
        member = ProjectMember(project_id=project.id, user_id=user_id, role=role)
        db.session.add(member)
    else:
        member.role = role
    db.session.commit()
    return jsonify({
        'member': member.to_dict(),
        'members': [m.to_dict() for m in ProjectMember.query.filter_by(project_id=project.id).all()]
    }), 200


@projects_bp.route('/<int:project_id>/members/<int:user_id>', methods=['DELETE'])
def remove_member(project_id, user_id):
    ProjectMember.query.filter_by(project_id=project_id, user_id=user_id).delete()
    db.session.commit()
    remaining = [m.to_dict() for m in ProjectMember.query.filter_by(project_id=project_id).all()]
    return jsonify({'ok': True, 'members': remaining}), 200
