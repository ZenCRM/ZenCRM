from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.comment import Comment
from ..schemas.comment import CommentSchema
from ..utils.activity import log_activity

comments_bp = Blueprint('comments', __name__)
schema = CommentSchema()
schema_many = CommentSchema(many=True)


@comments_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    et = request.args.get('entity_type')
    eid = request.args.get('entity_id', type=int)
    q = Comment.query
    if et:
        q = q.filter_by(entity_type=et)
    if eid is not None:
        q = q.filter_by(entity_id=eid)
    items = q.order_by(Comment.created_at.asc()).all()
    return jsonify([x.to_dict() for x in items]), 200


@comments_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Nieprawidłowy wpis'}), 400
    if not isinstance(data.get('content', ''), str):
        return jsonify({'error': 'Treść musi być tekstem'}), 400
    content = (data.get('content') or '').strip()
    et = data.get('entity_type')
    eid = data.get('entity_id')
    if not content or not et or not eid:
        return jsonify({'error': 'Brak treści, entity_type lub entity_id'}), 400

    from ..models.client import Client
    from ..models.lead import Lead
    from ..models.contact import Contact
    from ..models.task import Task
    from ..models.service import Service
    models = {'client': Client, 'lead': Lead, 'contact': Contact, 'task': Task, 'service': Service}
    kind = data.get('kind', 'note')
    state = data.get('communication_status')
    address = data.get('address') or None
    if not isinstance(et, str) or et not in models:
        return jsonify({'error': 'Nieprawidłowy typ rekordu'}), 400
    try:
        eid = int(eid)
    except (TypeError, ValueError):
        return jsonify({'error': 'Wybierz rekord'}), 400
    entity = db.session.get(models[et], eid)
    if not entity or getattr(entity, 'deleted_at', None):
        return jsonify({'error': 'Rekord nie istnieje lub jest w archiwum'}), 404
    allowed = {'note': (None, ''), 'call': ('answered', 'missed'), 'email': ('outgoing', 'incoming')}
    if not isinstance(kind, str) or kind not in allowed or state not in allowed[kind]:
        return jsonify({'error': 'Nieprawidłowy typ lub status wpisu'}), 400
    if kind != 'note' and et not in ('client', 'lead', 'contact'):
        return jsonify({'error': 'Telefon i e-mail przypisz do klienta, leada lub kontaktu'}), 400
    if address is not None and (not isinstance(address, str) or len(address) > 254):
        return jsonify({'error': 'Numer lub adres jest zbyt długi'}), 400
    labels = {'note': 'Notatka', 'call': 'Telefon', 'email': 'E-mail'}
    states = {'answered': 'odebrane', 'missed': 'nieodebrane', 'outgoing': 'wychodzący', 'incoming': 'przychodzący'}

    try:
        c = Comment(
            content=content,
            kind=kind, communication_status=state or None, address=address,
            entity_type=et,
            entity_id=int(eid),
            user_id=int(get_jwt_identity()),
        )
        db.session.add(c)
        db.session.flush()
        log_activity(et, int(eid), 'comment' if kind == 'note' else kind,
                     f"{labels[kind]}{(' · ' + states[state]) if state else ''}: {content[:80]}")
        db.session.commit()
        return jsonify(c.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@comments_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    c = db.session.get(Comment, item_id)
    if not c:
        return jsonify({'error': 'Komentarz nie istnieje'}), 404
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Nieprawidłowy wpis'}), 400
    content = data.get('content')
    if not isinstance(content, str) or not content.strip() or len(content) > 5000:
        return jsonify({'error': 'Treść musi mieć od 1 do 5000 znaków'}), 400
    c.content = content.strip()
    db.session.commit()
    return jsonify(c.to_dict()), 200


@comments_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    c = db.session.get(Comment, item_id)
    if not c:
        return jsonify({'error': 'Komentarz nie istnieje'}), 404
    db.session.delete(c)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200
