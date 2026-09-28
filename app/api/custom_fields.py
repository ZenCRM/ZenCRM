from datetime import date
from decimal import Decimal, InvalidOperation
from flask import Blueprint, request, jsonify, abort
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.workspace import CustomField, CustomValue
from ..utils.deletion import current_user, is_admin

custom_fields_bp = Blueprint('custom_fields', __name__)


def entities():
    from ..models.client import Client
    from ..models.lead import Lead
    from ..models.contact import Contact
    from ..models.task import Task
    from ..models.meeting import Meeting
    from ..models.service import Service
    from ..models.service_catalog import ServiceCatalog
    from ..models.document import Document
    from ..models.offer import Offer
    from ..models.template import Template
    from ..models.user import User
    from ..models.project import Project
    return dict(clients=Client, leads=Lead, contacts=Contact, tasks=Task,
                meetings=Meeting, services=Service, service_catalog=ServiceCatalog,
                documents=Document, offers=Offer, templates=Template, users=User, projects=Project)


@custom_fields_bp.before_request
@jwt_required()
def authorize():
    user = current_user()
    if not user or not user.is_active:
        abort(403)


@custom_fields_bp.route('', methods=['GET', 'POST'])
def definitions():
    if request.method == 'GET':
        return jsonify([f.to_dict() for f in CustomField.query.order_by(CustomField.id).all()])
    if not is_admin():
        abort(403)
    data = request.get_json() or {}
    label = str(data.get('label', '')).strip()
    if data.get('entity') not in entities() or data.get('kind') not in ('text', 'textarea', 'number', 'date', 'boolean') or not label or len(label) > 120:
        return jsonify(error='Nieprawidłowa definicja pola'), 400
    field = CustomField(entity=data['entity'], label=label, kind=data['kind'], required=bool(data.get('required', False)))
    db.session.add(field)
    db.session.commit()
    return jsonify(field.to_dict()), 201


@custom_fields_bp.route('/<int:field_id>', methods=['PUT'])
def update_definition(field_id):
    if not is_admin():
        abort(403)
    field = db.get_or_404(CustomField, field_id)
    data = request.get_json() or {}
    if 'label' in data:
        label = str(data['label']).strip()
        if not label or len(label) > 120:
            return jsonify(error='Nieprawidłowa nazwa pola'), 400
        field.label = label
    if 'required' in data:
        field.required = bool(data['required'])
    if 'kind' in data and data['kind'] in ('text', 'textarea', 'number', 'date', 'boolean'):
        field.kind = data['kind']
    if 'entity' in data and data['entity'] in entities():
        field.entity = data['entity']
    db.session.commit()
    return jsonify(field.to_dict()), 200


@custom_fields_bp.route('/<int:field_id>', methods=['DELETE'])
def remove_definition(field_id):
    if not is_admin():
        abort(403)
    field = db.get_or_404(CustomField, field_id)
    CustomValue.query.filter_by(field_id=field_id).delete()
    db.session.delete(field)
    db.session.commit()
    return jsonify(ok=True)


@custom_fields_bp.route('/<entity>/values', methods=['GET'])
def entity_values(entity):
    model = entities().get(entity)
    if model is None:
        abort(404)
    fields = CustomField.query.filter_by(entity=entity).all()
    if not fields:
        return jsonify({})
    field_ids = [f.id for f in fields]
    query = CustomValue.query.filter(CustomValue.field_id.in_(field_ids))
    ids_arg = request.args.get('ids')
    if ids_arg:
        try:
            record_ids = [int(x) for x in ids_arg.split(',') if x.strip()]
            if record_ids:
                query = query.filter(CustomValue.record_id.in_(record_ids))
        except ValueError:
            pass
    rows = query.all()
    res = {}
    for r in rows:
        rec_key = str(r.record_id)
        if rec_key not in res:
            res[rec_key] = {}
        res[rec_key][str(r.field_id)] = r.value
    return jsonify(res)



@custom_fields_bp.route('/<entity>/<int:record_id>', methods=['GET', 'PUT'])
def values(entity, record_id):
    model = entities().get(entity)
    if model is None:
        abort(404)
    record = db.get_or_404(model, record_id)
    if getattr(record, 'deleted_at', None):
        abort(404)
    if entity == 'users' and not is_admin() and current_user().id != record_id:
        abort(403)
    fields = CustomField.query.filter_by(entity=entity).all()
    if request.method == 'PUT':
        data = request.get_json() or {}
        clean = {}
        try:
            for field in fields:
                if str(field.id) not in data:
                    continue
                value = data[str(field.id)]
                if not isinstance(value, (str, int, float, bool)) and value is not None:
                    raise ValueError()
                value = '' if value is None else str(value)
                if len(value) > 10000:
                    raise ValueError()
                if value and field.kind == 'number':
                    value = value.replace(',', '.').strip()
                    if not Decimal(value).is_finite():
                        raise ValueError()
                if value and field.kind == 'date':
                    date.fromisoformat(value)
                if field.kind == 'boolean':
                    value = value.strip().lower()
                    if value not in ('', 'true', 'false'):
                        raise ValueError()
                clean[field.id] = value
        except (ValueError, InvalidOperation):
            return jsonify(error='Nieprawidłowa wartość pola własnego'), 400
        for field_id, value in clean.items():
            row = CustomValue.query.filter_by(field_id=field_id, record_id=record_id).first()
            if row is None:
                row = CustomValue(field_id=field_id, record_id=record_id)
                db.session.add(row)
            row.value = value
        db.session.commit()
    if not fields:
        return jsonify({})
    rows = CustomValue.query.filter(CustomValue.field_id.in_([f.id for f in fields]), CustomValue.record_id == record_id).all()
    return jsonify({str(row.field_id): row.value for row in rows})
