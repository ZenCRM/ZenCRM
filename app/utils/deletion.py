"""Soft delete + restore + hard delete + rola użytkownika."""
from datetime import datetime
from flask_jwt_extended import get_jwt_identity
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


def hard_delete(obj):
    db.session.delete(obj)
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
