from ..utils.activity import log_activity
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.meeting import Meeting
from ..schemas.meeting import MeetingSchema
from ..utils.sanitize import apply_payload, build_model
from ..utils.deletion import soft_delete

meetings_bp = Blueprint('meetings', __name__)
schema = MeetingSchema()
schema_many = MeetingSchema(many=True)


@meetings_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    query = Meeting.query.filter(Meeting.deleted_at == None)
    for field in ('client_id', 'lead_id'):
        value = request.args.get(field, type=int)
        if value is not None:
            query = query.filter(getattr(Meeting, field) == value)
    items = query.order_by(Meeting.id.desc()).all()
    return jsonify(schema_many.dump(items)), 200


@meetings_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    return jsonify(schema.dump(Meeting.query.get_or_404(item_id))), 200


@meetings_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        item = build_model(Meeting, data)
        db.session.add(item)
        db.session.flush()
        log_activity('meeting', item.id, 'created', 'Utworzono')
        db.session.commit()
        return jsonify(schema.dump(item)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@meetings_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    item = Meeting.query.get_or_404(item_id)
    try:
        apply_payload(item, request.get_json(silent=True) or {})
        log_activity('meeting', item.id, 'updated', 'Zaktualizowano')
        db.session.commit()
        return jsonify(schema.dump(item)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@meetings_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    item = Meeting.query.get_or_404(item_id)
    soft_delete(item, 'meeting')
    return jsonify({'message': 'Deleted'}), 200
