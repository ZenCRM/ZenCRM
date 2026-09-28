from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.contact import Contact
from ..utils.sanitize import apply_payload, build_model
from ..utils.deletion import soft_delete, restore, hard_delete, is_admin
from ..utils.activity import log_activity

contacts_bp = Blueprint('contacts', __name__)


@contacts_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    q = Contact.query.filter(Contact.deleted_at == None)
    cid = request.args.get('client_id', type=int)
    lid = request.args.get('lead_id', type=int)
    if cid is not None:
        q = q.filter_by(client_id=cid)
    if lid is not None:
        q = q.filter_by(lead_id=lid)
    return jsonify([c.to_dict() for c in q.order_by(Contact.is_primary.desc(), Contact.id.desc()).all()]), 200


@contacts_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    c = db.session.get(Contact, item_id)
    if not c:
        return jsonify({'error': 'Kontakt nie istnieje'}), 404
    return jsonify(c.to_dict()), 200


@contacts_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        c = build_model(Contact, data)
        db.session.add(c)
        db.session.flush()
        if c.is_primary and c.client_id:
            Contact.query.filter(
                Contact.client_id == c.client_id,
                Contact.id != c.id,
                Contact.deleted_at == None
            ).update({'is_primary': False})
        et = 'client' if c.client_id else ('lead' if c.lead_id else None)
        eid = c.client_id or c.lead_id
        if et:
            log_activity(et, eid, 'contact_added',
                         f'Dodano kontakt: {c.first_name} {c.last_name}')
        db.session.commit()
        return jsonify(c.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@contacts_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    c = db.session.get(Contact, item_id)
    if not c:
        return jsonify({'error': 'Kontakt nie istnieje'}), 404
    try:
        apply_payload(c, request.get_json(silent=True) or {})
        if c.is_primary and c.client_id:
            Contact.query.filter(
                Contact.client_id == c.client_id,
                Contact.id != c.id,
                Contact.deleted_at == None
            ).update({'is_primary': False})
        db.session.commit()
        return jsonify(c.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@contacts_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    c = db.session.get(Contact, item_id)
    if not c:
        return jsonify({'error': 'Kontakt nie istnieje'}), 404
    soft_delete(c)
    return jsonify({'ok': True, 'archived': True}), 200


@contacts_bp.route('/<int:item_id>/restore', methods=['POST'])
@jwt_required()
def restore_item(item_id):
    c = db.session.get(Contact, item_id)
    if not c:
        return jsonify({'error': 'Nie istnieje'}), 404
    restore(c)
    return jsonify({'ok': True}), 200


@contacts_bp.route('/<int:item_id>/permanent', methods=['DELETE'])
@jwt_required()
def permanent_delete(item_id):
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    c = db.session.get(Contact, item_id)
    if not c:
        return jsonify({'error': 'Nie istnieje'}), 404
    hard_delete(c)
    return jsonify({'ok': True}), 200
