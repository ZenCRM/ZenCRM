from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.user import User
from ..models.task import Task
from ..models.client import Client
from ..models.task_assignee import TaskAssignee
from ..utils.activity import log_activity

def can_change(row):
    user = db.session.get(User, int(get_jwt_identity()))
    return user and (user.role == 'admin' or user.id == row.user_id)


task_assignees_bp = Blueprint('task_assignees', __name__)


@task_assignees_bp.route('/task/<int:task_id>', methods=['GET'])
@jwt_required()
def list_for_task(task_id):
    rows = TaskAssignee.query.filter_by(task_id=task_id).all()
    return jsonify([r.to_dict() for r in rows]), 200


@task_assignees_bp.route('/task/<int:task_id>/set', methods=['POST'])
@jwt_required()
def set_assignees(task_id):
    """Ustawia liste przypisanych osob. Body: {user_ids: [1,2,3]}"""
    task = db.session.get(Task, task_id)
    if not task:
        return jsonify({'error': 'Zadanie nie istnieje'}), 404
    data = request.get_json(silent=True) or {}
    user_ids = data.get('user_ids') or []
    if not isinstance(user_ids, list) or not all(type(uid) is int for uid in user_ids):
        return jsonify({'error': 'user_ids must be a list of user IDs'}), 400
    user_ids = list(dict.fromkeys(user_ids))
    existing = {r.user_id: r for r in TaskAssignee.query.filter_by(task_id=task_id).all()}
    # Users already on the task may since have been deactivated; only newcomers must be active.
    known = dict(db.session.query(User.id, User.is_active).filter(User.id.in_(user_ids)).all())
    if any(uid not in known or (uid not in existing and not known[uid]) for uid in user_ids):
        return jsonify({'error': 'Unknown or inactive user'}), 400

    # Usun tych, ktorych juz nie ma
    if any(uid not in user_ids and not can_change(row) for uid, row in existing.items()):
        return jsonify({'error': 'Nie możesz usuwać innych wykonawców'}), 403
    for uid, row in existing.items():
        if uid not in user_ids:
            db.session.delete(row)

    # Dodaj nowych
    newly_added_uids = [uid for uid in user_ids if uid not in existing]
    for uid in newly_added_uids:
        db.session.add(TaskAssignee(task_id=task_id, user_id=uid, status='pending'))

    db.session.flush()
    task.recompute_status()
    if set(existing) != set(user_ids):
        log_activity('task', task.id, 'team', 'Zmieniono zespół')
    db.session.commit()

    for uid in newly_added_uids:
        try:
            u = db.session.get(User, uid)
            if u:
                from ..services.email_service import send_notification, staff_link_base_url
                crm_task_url = f"{staff_link_base_url()}/#tasks"
                client = db.session.get(Client, task.client_id) if task.client_id else None
                client_name = client.name if client else '-'
                due_date_str = task.due_date.strftime('%Y-%m-%d %H:%M') if task.due_date else 'Brak terminu'
                send_notification('employee_new_task', u.email, {
                    'employee_name': u.first_name,
                    'task_title': task.title,
                    'task_due_date': due_date_str,
                    'task_priority': task.priority or 'Normalny',
                    'client_name': client_name,
                    'task_description': task.description or 'Brak opisu',
                    'crm_task_url': crm_task_url,
                }, user=u)
        except Exception:
            pass
    return jsonify({
        'ok': True,
        'assignees': [r.to_dict() for r in TaskAssignee.query.filter_by(task_id=task_id).all()],
        'task_status': task.status,
    }), 200


@task_assignees_bp.route('/<int:ta_id>', methods=['PUT'])
@jwt_required()
def update_assignee(ta_id):
    """Zmiana statusu lub komentarza pojedynczego wykonawcy."""
    ta = db.session.get(TaskAssignee, ta_id)
    if not ta:
        return jsonify({'error': 'Nie istnieje'}), 404
    if not can_change(ta):
        return jsonify({'error': 'Możesz zmieniać tylko własny status i komentarz'}), 403
    data = request.get_json(silent=True) or {}
    if 'status' in data and data['status'] not in ('pending', 'in_progress', 'done'):
        return jsonify({'error': 'Nieprawidłowy status'}), 400
    if 'status' in data:
        ta.status = data['status']
    if 'comment' in data:
        ta.comment = data['comment']
    db.session.flush()

    task = db.session.get(Task, ta.task_id)
    if task:
        task.recompute_status()
        log_activity('task', task.id, 'status',
                     f'{ta.user_id}: {ta.status}')
    db.session.commit()
    return jsonify({'ok': True, 'assignee': ta.to_dict(),
                    'task_status': task.status if task else None}), 200


@task_assignees_bp.route('/<int:ta_id>', methods=['DELETE'])
@jwt_required()
def remove_assignee(ta_id):
    ta = db.session.get(TaskAssignee, ta_id)
    if not ta:
        return jsonify({'error': 'Nie istnieje'}), 404
    if not can_change(ta):
        return jsonify({'error': 'Nie możesz usuwać innych wykonawców'}), 403
    task = db.session.get(Task, ta.task_id)
    db.session.delete(ta)
    db.session.flush()
    if task:
        task.recompute_status()
    db.session.commit()
    return jsonify({'ok': True}), 200
