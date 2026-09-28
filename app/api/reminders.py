from datetime import datetime, timezone, timedelta
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.reminder import Reminder
from ..models.task import Task

reminders_bp = Blueprint('reminders', __name__)


def parse_time(value):
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if dt.tzinfo is None:
            raise ValueError()
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        if dt <= datetime.utcnow():
            raise ValueError()
        return dt
    except (TypeError, AttributeError, ValueError, OverflowError):
        raise ValueError('Wybierz przyszłą datę i godzinę przypomnienia.')


def clean_link(value):
    if not value:
        return None
    value = str(value).strip()
    if not value:
        return None
    if len(value) > 500:
        raise ValueError('Link do przypomnienia jest za dlugi (max 500 znakow).')
    from urllib.parse import urlsplit
    parsed = urlsplit(value)
    if parsed.scheme and parsed.scheme not in ('http', 'https'):
        raise ValueError('Niedozwolony schemat linku.')
    return value


def save_task_reminder(task, data):
    # The caller commits the task and reminder together.
    if 'reminder_at' not in data:
        return
    uid = int(get_jwt_identity())
    row = Reminder.query.filter_by(user_id=uid, task_id=task.id).first()
    if not data['reminder_at']:
        if row:
            db.session.delete(row)
        return
    at = parse_time(data['reminder_at'])
    if not row:
        row = Reminder(user_id=uid, task_id=task.id)
        db.session.add(row)
    row.title = task.title
    row.remind_at = at
    row.dismissed = False


@reminders_bp.get('')
@jwt_required()
def list_items():
    uid = int(get_jwt_identity())
    include_archived = request.args.get('include_archived', 'false').lower() in ('1', 'true', 'yes')
    archived_only = request.args.get('archived', 'false').lower() in ('1', 'true', 'yes')

    query = Reminder.query.filter_by(user_id=uid)
    if archived_only:
        query = query.filter_by(dismissed=True)
    elif not include_archived:
        query = query.filter_by(dismissed=False)

    rows = query.order_by(Reminder.remind_at.desc() if (include_archived or archived_only) else Reminder.remind_at.asc()).all()
    result = []
    for row in rows:
        if row.task_id:
            task = db.session.get(Task, row.task_id)
            if not task or task.deleted_at:
                continue
            if not (include_archived or archived_only) and task.status == 'done':
                continue
        result.append(row.to_dict())
    return jsonify(result)


@reminders_bp.post('')
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        title = data.get('title')
        if not isinstance(title, str) or not title.strip() or len(title.strip()) > 200:
            raise ValueError('Wpisz treść przypomnienia (maksymalnie 200 znaków).')
        link = clean_link(data.get('link'))
        row = Reminder(user_id=int(get_jwt_identity()), title=title.strip(), remind_at=parse_time(data.get('remind_at')), link=link)
        db.session.add(row)
        db.session.commit()
        return jsonify(row.to_dict()), 201
    except ValueError as error:
        db.session.rollback()
        return jsonify(error=str(error)), 400


@reminders_bp.put('/<int:item_id>')
@jwt_required()
def update_item(item_id):
    row = Reminder.query.filter_by(id=item_id, user_id=int(get_jwt_identity())).first_or_404()
    data = request.get_json(silent=True) or {}
    try:
        action = data.get('action')
        if action == 'dismiss':
            row.dismissed = True
        elif action == 'restore':
            row.dismissed = False
            if row.remind_at <= datetime.utcnow():
                row.remind_at = datetime.utcnow() + timedelta(minutes=10)
        elif action == 'snooze':
            minutes = data.get('minutes')
            if type(minutes) is not int or minutes not in (5, 10, 15, 30, 60, 1440):
                raise ValueError('Wybierz poprawny czas odłożenia.')
            row.remind_at = datetime.utcnow() + timedelta(minutes=minutes)
            row.dismissed = False
        else:
            raise ValueError('Nieznana operacja.')
        db.session.commit()
        return jsonify(row.to_dict())
    except ValueError as error:
        db.session.rollback()
        return jsonify(error=str(error)), 400


@reminders_bp.delete('/<int:item_id>')
@jwt_required()
def delete_item(item_id):
    row = Reminder.query.filter_by(id=item_id, user_id=int(get_jwt_identity())).first_or_404()
    db.session.delete(row)
    db.session.commit()
    return jsonify(success=True)
