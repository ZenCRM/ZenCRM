from flask import Blueprint, request, jsonify, Response
import re
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.template import Template
from ..models.document_type import DocumentType
from ..schemas.template import TemplateSchema
from ..services.render_service import render_preview
from ..utils.sanitize import apply_payload, build_model

templates_bp = Blueprint('templates', __name__)
schema = TemplateSchema()
schema_many = TemplateSchema(many=True)


def validate_variables(data):
    if 'variables' not in data:
        return data
    variables = data['variables']
    if not isinstance(variables, list) or len(variables) > 50:
        raise ValueError('Nieprawidłowa lista pól szablonu')
    names = set()
    clean = []
    for field in variables:
        if not isinstance(field, dict):
            raise ValueError('Nieprawidłowe pole szablonu')
        name = str(field.get('name', '')).strip()
        label = str(field.get('label', '')).strip()
        if not re.fullmatch(r'[a-zA-Z][a-zA-Z0-9_]{0,49}', name) or not label or len(label) > 120 or name in names:
            raise ValueError('Nazwa pola musi być unikalna i zawierać tylko litery, cyfry oraz _')
        names.add(name)
        clean.append({'name': name, 'label': label})
    data['variables'] = clean
    return data


def validate_document_type(data):
    if 'document_type_key' not in data:
        return
    key = data.get('document_type_key') or None
    if key and (data.get('type') == 'offer' or db.session.get(DocumentType, key) is None):
        raise ValueError('Wybierz istniejący typ dokumentu')
    data['document_type_key'] = key


@templates_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    return jsonify(schema_many.dump(
        Template.query.order_by(Template.id.desc()).all())), 200


@templates_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    return jsonify(schema.dump(Template.query.get_or_404(item_id))), 200


@templates_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        validate_variables(data)
        validate_document_type(data)
        tpl = build_model(Template, data)
        db.session.add(tpl)
        db.session.commit()
        return jsonify(schema.dump(tpl)), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@templates_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    tpl = Template.query.get_or_404(item_id)
    try:
        data = validate_variables(request.get_json(silent=True) or {})
        type_check = {**data, 'type': data.get('type', tpl.type)}
        validate_document_type(type_check)
        if 'document_type_key' in data:
            data['document_type_key'] = type_check['document_type_key']
        if (data.get('type', tpl.type) == 'offer' and data.get('document_type_key', tpl.document_type_key)):
            raise ValueError('Szablon oferty nie może być przypisany do typu dokumentu')
        apply_payload(tpl, data)
        db.session.commit()
        return jsonify(schema.dump(tpl)), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@templates_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    tpl = Template.query.get_or_404(item_id)
    db.session.delete(tpl)
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200


@templates_bp.route('/preview', methods=['POST'])
@jwt_required()
def preview_inline():
    data = request.get_json(silent=True) or {}
    content = data.get('content', '')
    tpl_type = data.get('type', 'offer')
    try:
        variables = validate_variables({'variables': data.get('variables', [])})['variables']
        kind = db.session.get(DocumentType, data.get('document_type_key')) if data.get('document_type_key') else None
        return Response(render_preview(content, tpl_type, variables, kind.fields if kind else []), mimetype='text/html')
    except Exception as e:
        return Response(
            f'<pre style="color:red;padding:20px;font-family:monospace">'
            f'Błąd renderowania szablonu:\n\n{e}</pre>',
            mimetype='text/html', status=400,
        )


@templates_bp.route('/<int:item_id>/preview', methods=['GET'])
@jwt_required()
def preview_saved(item_id):
    tpl = Template.query.get_or_404(item_id)
    try:
        kind = db.session.get(DocumentType, tpl.document_type_key) if tpl.document_type_key else None
        return Response(render_preview(tpl.content, tpl.type or 'offer', tpl.variables or [], kind.fields if kind else []),
                        mimetype='text/html')
    except Exception as e:
        return Response(
            f'<pre style="color:red;padding:20px;font-family:monospace">'
            f'Błąd renderowania szablonu:\n\n{e}</pre>',
            mimetype='text/html', status=400,
        )
