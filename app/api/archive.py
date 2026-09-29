"""Archiwum: lista usuniętych, przywracanie, permanentne usuwanie (admin)."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.client import Client
from ..models.lead import Lead
from ..models.contact import Contact
from ..models.task import Task
from ..models.project import Project
from ..models.meeting import Meeting
from ..models.service import Service
from ..models.service_catalog import ServiceCatalog
from ..models.offer import Offer
from ..models.document import Document
from ..models.activity import Activity
from ..models.user import User
from ..utils.deletion import restore, hard_delete, is_admin
from ..utils.activity import log_activity

archive_bp = Blueprint('archive', __name__)


@archive_bp.before_request
def check_archive_access():
    from ..models.setting import Setting
    import json
    val = Setting.get_value('menu_permissions', '{}')
    try:
        perms = json.loads(val) if val else {}
    except Exception:
        perms = {}
    cfg = perms.get('archive', {})
    if cfg.get('enabled') is False:
        return jsonify({'error': 'Moduł archiwum jest wyłączony'}), 403
    req_role = cfg.get('role', 'all')
    from ..utils.deletion import current_user
    u = current_user()
    if req_role == 'admin' and (not u or u.role != 'admin'):
        return jsonify({'error': 'Brak uprawnień do modułu archiwum'}), 403
    if req_role == 'manager' and (not u or u.role not in ('admin', 'manager')):
        return jsonify({'error': 'Brak uprawnień do modułu archiwum'}), 403


MODELS = {
    'clients':         Client,
    'leads':           Lead,
    'contacts':        Contact,
    'tasks':           Task,
    'projects':        Project,
    'meetings':        Meeting,
    'services':        Service,
    'service_catalog': ServiceCatalog,
    'offers':          Offer,
    'documents':       Document,
}


def _archived(M):
    return M.query.filter(M.deleted_at != None).order_by(M.deleted_at.desc()).all()


@archive_bp.route('', methods=['GET'])
@jwt_required()
def list_archive():
    """Zwraca wszystkie usunięte elementy (flat list, z _type, info o usunięciu i użytkowniku)."""
    # Pobierz historię usunięć z tabeli activities
    del_activities = (
        Activity.query
        .filter(Activity.action.in_(['deleted', 'archived']))
        .order_by(Activity.id.desc())
        .all()
    )
    user_ids = {a.user_id for a in del_activities if a.user_id}
    users_by_id = {}
    if user_ids:
        users = User.query.filter(User.id.in_(user_ids)).all()
        for u in users:
            name = f"{u.first_name or ''} {u.last_name or ''}".strip() or u.email
            users_by_id[u.id] = {
                'id': u.id,
                'name': name,
                'email': u.email,
                'avatar_url': getattr(u, 'avatar_url', None),
            }

    act_map = {}
    for a in del_activities:
        k = (str(a.entity_type).lower(), a.entity_id)
        if k not in act_map:
            act_map[k] = {
                'user': users_by_id.get(a.user_id) if a.user_id else None,
                'date': a.created_at.isoformat() if a.created_at else None,
            }

    items = []
    for key, M in MODELS.items():
        try:
            for obj in _archived(M):
                d = obj.to_dict()
                d['_type'] = key
                d['_type_singular'] = key.rstrip('s') if key != 'sms' else key

                title = d.get('name') or d.get('title') or d.get('full_name') or d.get('number') or f"#{obj.id}"
                subtitle = d.get('email') or d.get('company') or d.get('client_name') or d.get('position') or ''
                d['_title'] = str(title)
                d['_subtitle'] = str(subtitle) if subtitle else ''

                sing = d['_type_singular']
                candidates = [
                    (key.lower(), obj.id),
                    (sing.lower(), obj.id),
                    (key.replace('_', '-').lower(), obj.id),
                ]
                act_info = None
                for cand in candidates:
                    if cand in act_map:
                        act_info = act_map[cand]
                        break

                d['deleted_by'] = act_info['user'] if act_info else None
                if not d.get('deleted_at') and act_info and act_info.get('date'):
                    d['deleted_at'] = act_info['date']

                items.append(d)
        except Exception as e:
            print(f'[archive] {key}: {e}')

    items.sort(key=lambda x: x.get('deleted_at') or '', reverse=True)
    return jsonify({
        'items': items,
        'total': len(items),
        'is_admin': is_admin(),
    }), 200


@archive_bp.route('/<entity>/<int:item_id>', methods=['GET'])
@jwt_required()
def get_archived_item(entity, item_id):
    """Zwraca szczegółowe dane usuniętego elementu do podglądu."""
    M = MODELS.get(entity)
    if not M:
        return jsonify({'error': 'Nieznany typ'}), 400
    obj = db.session.get(M, item_id)
    if not obj:
        return jsonify({'error': 'Nie istnieje'}), 404
    d = obj.to_dict()
    d['_type'] = entity
    d['_type_singular'] = entity.rstrip('s') if entity != 'sms' else entity
    d['_title'] = d.get('name') or d.get('title') or d.get('full_name') or d.get('number') or f"#{obj.id}"
    return jsonify(d), 200


@archive_bp.route('/<entity>/<int:item_id>/restore', methods=['POST'])
@jwt_required()
def restore_item(entity, item_id):
    M = MODELS.get(entity)
    if not M:
        return jsonify({'error': 'Nieznany typ'}), 400
    obj = db.session.get(M, item_id)
    if not obj:
        return jsonify({'error': 'Nie istnieje'}), 404
    restore(obj, entity)
    return jsonify({'ok': True, 'id': obj.id, 'type': entity}), 200


@archive_bp.route('/<entity>/<int:item_id>/permanent', methods=['DELETE'])
@jwt_required()
def permanent_delete(entity, item_id):
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    M = MODELS.get(entity)
    if not M:
        return jsonify({'error': 'Nieznany typ'}), 400
    obj = db.session.get(M, item_id)
    if not obj:
        return jsonify({'error': 'Nie istnieje'}), 404
    hard_delete(obj)
    return jsonify({'ok': True}), 200


@archive_bp.route('/empty', methods=['POST'])
@jwt_required()
def empty_archive():
    """Opróżnienie archiwum (admin)."""
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    total = 0
    for key, M in MODELS.items():
        for obj in _archived(M):
            db.session.delete(obj)
            total += 1
    db.session.commit()
    return jsonify({'ok': True, 'deleted': total}), 200
