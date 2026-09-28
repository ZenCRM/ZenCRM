"""Assignment inbox: only records currently assigned to the authenticated user."""
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_
from ..models.activity import Activity
from ..models.client import Client
from ..models.lead import Lead
from ..models.task import Task
from ..models.task_assignee import TaskAssignee
from ..models.service import Service
from ..models.meeting import Meeting

notifications_bp = Blueprint('notifications', __name__)


@notifications_bp.get('')
@jwt_required()
def inbox():
    uid = int(get_jwt_identity())
    records = []
    for kind, model in [('client', Client), ('lead', Lead)]:
        records.extend((kind, row) for row in model.query.filter_by(assignee_id=uid, deleted_at=None).all())
    task_ids = TaskAssignee.query.with_entities(TaskAssignee.task_id).filter_by(user_id=uid)
    records.extend(('task', row) for row in Task.query.filter(Task.deleted_at.is_(None), or_(Task.assignee_id == uid, Task.id.in_(task_ids))).all())
    records.extend(('service', row) for row in Service.query.filter_by(deleted_at=None).all() if str(uid) in {str(v) for v in (row.assignee_ids or [])})
    records.extend(('meeting', row) for row in Meeting.query.filter_by(organizer_id=uid, deleted_at=None).all())
    lookup = {(kind, row.id): row for kind, row in records}
    conditions = [and_(Activity.entity_type == kind, Activity.entity_id.in_([r.id for k, r in records if k == kind])) for kind in {k for k, _ in records}]
    activities = Activity.query.filter(or_(*conditions)).order_by(Activity.created_at.desc(), Activity.id.desc()).limit(200).all() if conditions else []
    items = []
    for kind, row in records:
        items.append(dict(id=f'assigned:{kind}:{row.id}', entity_type=kind, entity_id=row.id, title=getattr(row, 'title', None) or getattr(row, 'name', ''), action='assigned', created_at=row.created_at.isoformat() if row.created_at else '', actor=None))
    for event in activities:
        row = lookup[(event.entity_type, event.entity_id)]
        items.append(dict(id=f'activity:{event.id}', entity_type=event.entity_type, entity_id=event.entity_id, title=getattr(row, 'title', None) or getattr(row, 'name', ''), action=event.action, created_at=event.created_at.isoformat(), actor=event.to_dict()['user']))
    return jsonify(sorted(items, key=lambda item: (item['created_at'], item['id']), reverse=True))
