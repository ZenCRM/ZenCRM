from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.service import Service
from ..utils.sanitize import apply_payload, build_model
from ..utils.deletion import soft_delete, restore, hard_delete, is_admin
from ..utils.activity import log_activity

services_bp = Blueprint('services', __name__)


@services_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    q = Service.query.filter(Service.deleted_at == None)
    cid = request.args.get('client_id', type=int)
    if cid is not None and hasattr(Service, 'client_id'):
        q = q.filter(Service.client_id == cid)
    return jsonify([x.to_dict() for x in q.order_by(Service.id.desc()).all()]), 200


@services_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    o = db.session.get(Service, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    return jsonify(o.to_dict()), 200


@services_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        o = build_model(Service, data)
        db.session.add(o)
        db.session.flush()
        log_activity('service', o.id, 'created', 'Utworzono')
        db.session.commit()
        return jsonify(o.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@services_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    o = db.session.get(Service, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    try:
        apply_payload(o, request.get_json(silent=True) or {})
        log_activity('service', o.id, 'updated', 'Zaktualizowano')
        db.session.commit()
        return jsonify(o.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@services_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    o = db.session.get(Service, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    soft_delete(o)
    return jsonify({'ok': True, 'archived': True}), 200


@services_bp.route('/<int:item_id>/restore', methods=['POST'])
@jwt_required()
def restore_item(item_id):
    o = db.session.get(Service, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    restore(o)
    return jsonify({'ok': True}), 200


@services_bp.route('/<int:item_id>/permanent', methods=['DELETE'])
@jwt_required()
def permanent_delete(item_id):
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    o = db.session.get(Service, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    hard_delete(o)
    return jsonify({'ok': True}), 200

@services_bp.route('/<int:item_id>/detail', methods=['GET'])
@jwt_required()
def get_detail(item_id):
    """Zwraca usluge z powiazanymi: zadaniami, dokumentami, komentarzami,
    aktywnosciami i zespolem."""
    from ..models.task import Task
    from ..models.document import Document
    from ..models.comment import Comment
    from ..models.activity import Activity
    from ..models.task_assignee import TaskAssignee
    from ..models.user import User

    s = db.session.get(Service, item_id)
    if not s:
        return jsonify({'error': 'Usluga nie istnieje'}), 404

    data = s.to_dict()

    # Powiazane zadania (nieusuniete)
    tasks = Task.query.filter_by(service_id=item_id).filter(Task.deleted_at == None).all()
    data['tasks'] = [t.to_dict() for t in tasks]

    # Powiazane dokumenty
    docs = Document.query.filter_by(service_id=item_id).filter(Document.deleted_at == None).all()
    data['documents'] = [d.to_dict() for d in docs]

    # Komentarze
    comments = Comment.query.filter_by(entity_type='service', entity_id=item_id) \
        .order_by(Comment.created_at.asc()).all()
    data['comments'] = [c.to_dict() for c in comments]

    # Aktywnosci
    acts = Activity.query.filter_by(entity_type='service', entity_id=item_id) \
        .order_by(Activity.created_at.desc()).limit(100).all()
    data['activities'] = [a.to_dict() for a in acts]

    # Zespol – unikalni userzy z task assignees
    user_ids = set()
    for t in tasks:
        for ta in TaskAssignee.query.filter_by(task_id=t.id).all():
            user_ids.add(ta.user_id)
    team = []
    for uid in user_ids:
        u = db.session.get(User, uid)
        if u:
            team.append(u.to_dict())
    data['team'] = team

    return jsonify(data), 200
