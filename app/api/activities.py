from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..models.activity import Activity
from ..schemas.activity import ActivitySchema

activities_bp = Blueprint('activities', __name__)
schema_many = ActivitySchema(many=True)


@activities_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    et = request.args.get('entity_type')
    eid = request.args.get('entity_id', type=int)
    q = Activity.query
    if et:
        q = q.filter_by(entity_type=et)
    if eid is not None:
        q = q.filter_by(entity_id=eid)
    items = q.order_by(Activity.created_at.desc()).limit(100).all()
    return jsonify([x.to_dict() for x in items]), 200
