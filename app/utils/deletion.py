"""Soft delete + restore + hard delete + rola użytkownika."""
from datetime import datetime
from flask import abort
from flask_jwt_extended import get_jwt_identity
from sqlalchemy.exc import IntegrityError
from ..extensions import db


def soft_delete(obj, entity_type=None):
    obj.deleted_at = datetime.utcnow()
    ent = entity_type or getattr(obj, '__tablename__', None) or 'item'
    if ent.endswith('s') and ent != 'sms':
        ent = ent[:-1]
    name = (
        getattr(obj, 'name', None)
        or getattr(obj, 'title', None)
        or getattr(obj, 'number', None)
        or (f"{getattr(obj, 'first_name', '')} {getattr(obj, 'last_name', '')}".strip())
        or f'#{getattr(obj, "id", "")}'
    )
    from .activity import log_activity
    try:
        log_activity(ent, obj.id, 'deleted', f'Przeniesiono do archiwum: {name}')
    except Exception:
        pass
    db.session.commit()


def restore(obj, entity_type=None):
    obj.deleted_at = None
    ent = entity_type or getattr(obj, '__tablename__', None) or 'item'
    if ent.endswith('s') and ent != 'sms':
        ent = ent[:-1]
    name = (
        getattr(obj, 'name', None)
        or getattr(obj, 'title', None)
        or getattr(obj, 'number', None)
        or (f"{getattr(obj, 'first_name', '')} {getattr(obj, 'last_name', '')}".strip())
        or f'#{getattr(obj, "id", "")}'
    )
    from .activity import log_activity
    try:
        log_activity(ent, obj.id, 'restored', f'Przywrócono z archiwum: {name}')
    except Exception:
        pass
    db.session.commit()


LINKED_RECORD_ERROR = 'This record is still linked to other records. Remove or reassign them first.'


def has_protected_history(obj):
    """Links whose foreign keys would silently unlink history instead of blocking the delete."""
    from ..models.client import Client
    from ..models.project import Project
    from ..models.sms import SmsDevice
    from ..models.team import Team
    from ..models.ticket import Ticket, TicketMessage
    from ..models.user import User
    if isinstance(obj, User):
        return any(query.first() is not None for query in (
            SmsDevice.query.filter_by(user_id=obj.id),
            Ticket.query.filter_by(assignee_id=obj.id),
            TicketMessage.query.filter_by(user_id=obj.id),
            Team.query.filter_by(leader_id=obj.id),
        ))
    if isinstance(obj, Client):
        return Project.query.filter_by(client_id=obj.id).first() is not None
    return False


def release_dependents(obj):
    """Remove or unlink rows that only exist to support obj, so it can be deleted."""
    from ..models.client import Client
    from ..models.document import Document
    from ..models.offer import Offer
    from ..models.push import PushSubscription
    from ..models.reminder import Reminder
    from ..models.service import Service
    from ..models.sms import PhoneCall, SmsMessage, SmsQueue
    from ..models.task import Task
    from ..models.task_assignee import TaskAssignee
    from ..models.template import Template
    from ..models.user import User
    from ..models.auth_security import PasswordReset
    from ..models.workspace import PortalClientSpace
    if isinstance(obj, Client):
        PortalClientSpace.query.filter_by(client_id=obj.id).delete(synchronize_session=False)
        for model in (PhoneCall, SmsMessage, SmsQueue):
            model.query.filter_by(client_id=obj.id).update({model.client_id: None}, synchronize_session=False)
    elif isinstance(obj, Task):
        Reminder.query.filter_by(task_id=obj.id).delete(synchronize_session=False)
        TaskAssignee.query.filter_by(task_id=obj.id).delete(synchronize_session=False)
    elif isinstance(obj, Service):
        for model in (Document, Task):
            model.query.filter_by(service_id=obj.id).update({model.service_id: None}, synchronize_session=False)
    elif isinstance(obj, Template):
        for model in (Document, Offer):
            model.query.filter_by(template_id=obj.id).update({model.template_id: None}, synchronize_session=False)
    elif isinstance(obj, User):
        for model in (Reminder, PushSubscription, PasswordReset):
            model.query.filter_by(user_id=obj.id).delete(synchronize_session=False)


def delete_if_unlinked(obj):
    """Delete obj inside a savepoint; return False and keep it when other records still reference it."""
    if has_protected_history(obj):
        return False
    try:
        with db.session.begin_nested(), db.session.no_autoflush:
            release_dependents(obj)
            db.session.delete(obj)
            db.session.flush()
    except IntegrityError:
        return False
    return True


def hard_delete(obj):
    if not delete_if_unlinked(obj):
        db.session.rollback()
        abort(409, description=LINKED_RECORD_ERROR)
    db.session.commit()


def current_user():
    from ..models.user import User
    try:
        uid = get_jwt_identity()
        if uid is None:
            return None
        return db.session.get(User, int(uid))
    except Exception:
        return None


def is_admin():
    u = current_user()
    return u is not None and u.is_active and u.role == 'admin'
