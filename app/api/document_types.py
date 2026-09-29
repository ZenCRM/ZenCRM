"""Configuration of document categories and typed fields."""
import re
from flask import Blueprint, abort, jsonify, request
from flask_jwt_extended import jwt_required

from ..extensions import db
from ..models.document import Document
from ..models.document_type import DocumentType
from ..models.template import Template
from ..utils.deletion import is_admin

document_types_bp = Blueprint('document_types', __name__)
KINDS = {'text', 'textarea', 'number', 'date', 'boolean', 'select'}


def validate_payload(data, creating=False):
    name = str(data.get('name', '')).strip()
    if not name or len(name) > 120:
        raise ValueError('Podaj nazwę typu dokumentu (maks. 120 znaków)')
    key = str(data.get('key', '')).strip()
    if creating and not re.fullmatch(r'[a-z][a-z0-9_]{0,49}', key):
        raise ValueError('Identyfikator typu: małe litery, cyfry i _')
    raw = data.get('fields', [])
    if not isinstance(raw, list) or len(raw) > 50:
        raise ValueError('Typ może mieć maksymalnie 50 pól')
    fields, keys = [], set()
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError('Nieprawidłowa definicja pola')
        field_key = str(item.get('key', '')).strip()
        label = str(item.get('label', '')).strip()
        kind = item.get('kind')
        if not re.fullmatch(r'[a-z][a-z0-9_]{0,49}', field_key) or field_key in keys or not label or len(label) > 120 or kind not in KINDS:
            raise ValueError('Sprawdź nazwę, identyfikator i rodzaj pól')
        keys.add(field_key)
        options = item.get('options', []) if kind == 'select' else []
        if kind == 'select' and (not isinstance(options, list) or not options or len(options) > 30 or any(not isinstance(v, str) or not v.strip() or len(v) > 120 for v in options)):
            raise ValueError('Pole wyboru wymaga od 1 do 30 opcji')
        fields.append(dict(key=field_key, label=label, kind=kind,
                           required=bool(item.get('required', False)),
                           options=[v.strip() for v in options]))
    return name, key, fields


@document_types_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    return jsonify([row.to_dict() for row in DocumentType.query.order_by(DocumentType.name).all()])


@document_types_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    if not is_admin():
        abort(403)
    data = request.get_json(silent=True) or {}
    try:
        name, key, fields = validate_payload(data, creating=True)
        if db.session.get(DocumentType, key):
            return jsonify(error='Taki identyfikator już istnieje'), 409
        row = DocumentType(key=key, name=name, fields=fields,
                           is_active=bool(data.get('is_active', True)))
        db.session.add(row)
        db.session.commit()
        return jsonify(row.to_dict()), 201
    except ValueError as exc:
        return jsonify(error=str(exc)), 400


@document_types_bp.route('/<key>', methods=['PUT', 'DELETE'])
@jwt_required()
def item(key):
    if not is_admin():
        abort(403)
    row = db.get_or_404(DocumentType, key)
    if request.method == 'DELETE':
        if Document.query.filter_by(type=key).first() or Template.query.filter_by(document_type_key=key).first():
            return jsonify(error='Typ jest używany przez dokumenty lub szablony'), 409
        db.session.delete(row)
        db.session.commit()
        return jsonify(ok=True)
    data = request.get_json(silent=True) or {}
    try:
        name, _, fields = validate_payload(data)
        row.name, row.fields = name, fields
        row.is_active = bool(data.get('is_active', row.is_active))
        db.session.commit()
        return jsonify(row.to_dict())
    except ValueError as exc:
        return jsonify(error=str(exc)), 400
