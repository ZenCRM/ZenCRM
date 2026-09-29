"""Private files attached to CRM records."""
from pathlib import Path
import secrets

from flask import Blueprint, current_app, jsonify, request, send_from_directory, abort
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models.attachment import Attachment
from ..utils.deletion import current_user
from ..utils.permissions import has_permission

attachments_bp = Blueprint('attachments', __name__)
MODELS = {'project': 'projects', 'client': 'clients', 'lead': 'leads',
          'service': 'services', 'task': 'tasks'}
MAX_SIZE = 20 * 1024 * 1024


def storage():
    directory = Path(current_app.instance_path) / 'attachments'
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def record_or_404(entity, record_id):
    if entity not in MODELS:
        abort(404)
    from ..models.project import Project
    from ..models.client import Client
    from ..models.lead import Lead
    from ..models.service import Service
    from ..models.task import Task
    model = {'project': Project, 'client': Client, 'lead': Lead,
             'service': Service, 'task': Task}[entity]
    record = db.session.get(model, record_id)
    if not record or getattr(record, 'deleted_at', None):
        abort(404)
    return record


def require_action(entity, action):
    if not has_permission(current_user(), f'{MODELS[entity]}.{action}'):
        abort(403)


def display_name(value):
    value = str(value or '').strip()
    if not value or len(value) > 255 or value in ('.', '..') or any(ord(c) < 32 or c in '/\\' for c in value):
        raise ValueError('Nieprawidłowa nazwa pliku')
    return value


@attachments_bp.route('/<entity>/<int:record_id>', methods=['GET', 'POST'])
@jwt_required()
def collection(entity, record_id):
    record_or_404(entity, record_id)
    if request.method == 'GET':
        rows = Attachment.query.filter_by(entity_type=entity, entity_id=record_id).order_by(Attachment.id.desc()).all()
        return jsonify([row.to_dict() for row in rows])
    require_action(entity, 'edit')
    upload = request.files.get('file')
    if not upload or not upload.filename:
        return jsonify(error='Wybierz plik'), 400
    content = upload.stream.read(MAX_SIZE + 1)
    if not content or len(content) > MAX_SIZE:
        return jsonify(error='Plik musi mieć od 1 B do 20 MB'), 400
    try:
        filename = display_name(upload.filename.replace('\\', '/').split('/')[-1])
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
    name = secrets.token_hex(24)
    path = storage() / name
    path.write_bytes(content)
    try:
        row = Attachment(entity_type=entity, entity_id=record_id, filename=filename,
                         storage_name=name, size=len(content), created_by_id=current_user().id)
        db.session.add(row)
        db.session.commit()
    except Exception:
        db.session.rollback()
        path.unlink(missing_ok=True)
        raise
    return jsonify(row.to_dict()), 201


@attachments_bp.route('/<int:attachment_id>', methods=['GET', 'PUT', 'DELETE'])
@jwt_required()
def item(attachment_id):
    row = db.get_or_404(Attachment, attachment_id)
    record_or_404(row.entity_type, row.entity_id)
    if request.method == 'GET':
        return send_from_directory(storage(), row.storage_name, as_attachment=True,
                                   download_name=row.filename)
    require_action(row.entity_type, 'edit')
    if request.method == 'PUT':
        try:
            row.filename = display_name((request.get_json(silent=True) or {}).get('filename'))
        except ValueError as exc:
            return jsonify(error=str(exc)), 400
        db.session.commit()
        return jsonify(row.to_dict())
    path = storage() / row.storage_name
    db.session.delete(row)
    db.session.commit()
    path.unlink(missing_ok=True)
    return jsonify(ok=True)
