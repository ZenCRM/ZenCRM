"""Pomocnik do zapisywania wpisów w dzienniku aktywności."""
from flask_jwt_extended import get_jwt_identity
from ..extensions import db
from ..models.activity import Activity


def log_activity(entity_type, entity_id, action, description=None, meta=None):
    """Zapisuje zdarzenie. Wywołujący musi zrobić db.session.commit() po tym."""
    uid = None
    try:
        ident = get_jwt_identity()
        if ident is not None:
            uid = int(ident)
    except Exception:
        pass

    try:
        a = Activity(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            description=description,
            user_id=uid,
            meta=meta,
        )
        db.session.add(a)
    except Exception as e:
        print(f'[activity] Błąd zapisu: {e}')
