from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.service_catalog import ServiceCatalog
from ..utils.sanitize import apply_payload, build_model
from ..utils.deletion import soft_delete, restore, hard_delete, is_admin
from ..utils.activity import log_activity

service_catalog_bp = Blueprint('service_catalog', __name__)


@service_catalog_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    q = ServiceCatalog.query
    cid = request.args.get('client_id', type=int)
    if cid is not None and hasattr(ServiceCatalog, 'client_id'):
        q = q.filter(ServiceCatalog.client_id == cid)
    return jsonify([x.to_dict() for x in q.order_by(ServiceCatalog.id.desc()).all()]), 200


@service_catalog_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    o = db.session.get(ServiceCatalog, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    return jsonify(o.to_dict()), 200


@service_catalog_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        o = build_model(ServiceCatalog, data)
        db.session.add(o)
        db.session.flush()
        log_activity('service_catalog', o.id, 'created', 'Utworzono')
        db.session.commit()
        return jsonify(o.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@service_catalog_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    o = db.session.get(ServiceCatalog, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    try:
        apply_payload(o, request.get_json(silent=True) or {})
        db.session.commit()
        return jsonify(o.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@service_catalog_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    o = db.session.get(ServiceCatalog, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    soft_delete(o)
    return jsonify({'ok': True, 'archived': True}), 200


@service_catalog_bp.route('/<int:item_id>/restore', methods=['POST'])
@jwt_required()
def restore_item(item_id):
    o = db.session.get(ServiceCatalog, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    restore(o)
    return jsonify({'ok': True}), 200


@service_catalog_bp.route('/<int:item_id>/permanent', methods=['DELETE'])
@jwt_required()
def permanent_delete(item_id):
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    o = db.session.get(ServiceCatalog, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    hard_delete(o)
    return jsonify({'ok': True}), 200


# ── Alias: /api/service_catalog (podkreslnik) – zgodnosc z frontendem ──
service_catalog_alias_bp = Blueprint('service_catalog_alias', __name__)


@service_catalog_alias_bp.route('', methods=['GET'])
@jwt_required()
def alias_list():
    q = ServiceCatalog.query
    return jsonify([x.to_dict() for x in q.order_by(ServiceCatalog.id.desc()).all()]), 200


@service_catalog_alias_bp.route('', methods=['POST'])
@jwt_required()
def alias_create():
    data = request.get_json(silent=True) or {}
    try:
        o = build_model(ServiceCatalog, data)
        db.session.add(o)
        db.session.commit()
        return jsonify(o.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@service_catalog_alias_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def alias_get(item_id):
    o = db.session.get(ServiceCatalog, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    return jsonify(o.to_dict()), 200


@service_catalog_alias_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def alias_update(item_id):
    o = db.session.get(ServiceCatalog, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    try:
        apply_payload(o, request.get_json(silent=True) or {})
        db.session.commit()
        return jsonify(o.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@service_catalog_alias_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def alias_delete(item_id):
    o = db.session.get(ServiceCatalog, item_id)
    if not o:
        return jsonify({'error': 'Nie istnieje'}), 404
    soft_delete(o)
    return jsonify({'ok': True, 'archived': True}), 200
