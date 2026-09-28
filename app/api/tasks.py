from .reminders import save_task_reminder
from ..utils.activity import log_activity
import json
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.task import Task
from ..models.setting import Setting
from ..utils.task_stages import get_task_stages, validate_task_stages
from ..utils.deletion import is_admin
from ..schemas.task import TaskSchema
from ..utils.sanitize import apply_payload, build_model
from ..utils.deletion import soft_delete

tasks_bp = Blueprint('tasks', __name__)
schema = TaskSchema()
schema_many = TaskSchema(many=True)
@tasks_bp.route('/board-settings', methods=['GET', 'PUT'])
@jwt_required()
def board_settings():
    if request.method == 'GET':
        return jsonify({'stages': get_task_stages()})
    if not is_admin():
        return jsonify({'error': 'Statusy zadań ustawia administrator.'}), 403
    try:
        clean = validate_task_stages((request.get_json(silent=True) or {}).get('stages'))
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    Setting.set_value('task_stages', json.dumps(clean, ensure_ascii=False), 'tasks')
    db.session.commit()
    return jsonify({'stages': clean})


@tasks_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    query = Task.query.filter(Task.deleted_at.is_(None))
    for field in ('client_id', 'lead_id', 'service_id', 'project_id'):
        value = request.args.get(field, type=int)
        if value is not None:
            query = query.filter(getattr(Task, field) == value)
    items = query.order_by(Task.id.desc()).all()
    return jsonify([x.to_dict() for x in items]), 200


@tasks_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    return jsonify(Task.query.get_or_404(item_id).to_dict()), 200


@tasks_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        item = build_model(Task, data)
        if item.status is None:
            item.status = 'todo'
        if item.project_id is None and item.status not in {stage['id'] for stage in get_task_stages()}:
            raise ValueError('Wybierz dostępny status zadania.')
        db.session.add(item)
        db.session.flush()
        save_task_reminder(item, data)
        log_activity('task', item.id, 'created', 'Utworzono')
        db.session.commit()
        return jsonify(item.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@tasks_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    item = Task.query.get_or_404(item_id)
    try:
        data = request.get_json(silent=True) or {}
        from ..models.user import User
        user = db.session.get(User, int(get_jwt_identity()))
        if item.assignees and 'status' in data and data['status'] != item.status and (not user or user.role != 'admin'):
            return jsonify({'error': 'Zmień własny status w zespole zadania'}), 403
        apply_payload(item, data)
        if item.project_id is None and item.status not in {stage['id'] for stage in get_task_stages()}:
            raise ValueError('Wybierz dostępny status zadania.')
        save_task_reminder(item, data)
        log_activity('task', item.id, 'updated', 'Zaktualizowano')
        db.session.commit()
        return jsonify(item.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@tasks_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    item = Task.query.get_or_404(item_id)
    soft_delete(item, 'task')
    return jsonify({'message': 'Deleted'}), 200

@tasks_bp.route('/<int:item_id>/detail', methods=['GET'])
@jwt_required()
def get_detail(item_id):
    """Zwraca zadanie z przypisanymi osobami, komentarzami i aktywnosciami."""
    from ..models.task_assignee import TaskAssignee
    from ..models.comment import Comment
    from ..models.activity import Activity

    t = db.session.get(Task, item_id)
    if not t:
        return jsonify({'error': 'Zadanie nie istnieje'}), 404

    data = t.to_dict()

    # Przypisani (z TaskAssignee)
    assignees = TaskAssignee.query.filter_by(task_id=item_id).all()
    data['assignees_detailed'] = [a.to_dict() for a in assignees]

    # Komentarze
    comments = Comment.query.filter_by(entity_type='task', entity_id=item_id) \
        .order_by(Comment.created_at.asc()).all()
    data['comments'] = [c.to_dict() for c in comments]

    # Aktywnosci
    acts = Activity.query.filter_by(entity_type='task', entity_id=item_id) \
        .order_by(Activity.created_at.desc()).limit(100).all()
    data['activities'] = [a.to_dict() for a in acts]

    # Statystyki
    total = len(assignees)
    done = sum(1 for a in assignees if a.status == 'done')
    in_progress = sum(1 for a in assignees if a.status == 'in_progress')
    pending = sum(1 for a in assignees if a.status == 'pending')

    data['stats'] = {
        'total': total,
        'done': done,
        'in_progress': in_progress,
        'pending': pending,
        'progress': round((done / total * 100) if total else 0),
    }

    return jsonify(data), 200
