from flask import Blueprint, request, jsonify, Response
import re
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.template import Template
from ..models.document_type import DocumentType
from ..schemas.template import TemplateSchema
from ..services.render_service import render_preview
from ..utils.sanitize import apply_payload, build_model
from ..utils.deletion import hard_delete
from ..utils.i18n import t
from html import escape
from ..services.template_sandbox import run_template
from ..utils.auth_limits import auth_limit
from ..utils.permissions import has_permission
from ..utils.deletion import current_user


def validate_content(data, tpl=None):
    name = data.get('name', tpl.name if tpl else '')
    content = data.get('content', tpl.content if tpl else '')
    kind = data.get('type', tpl.type if tpl else '')
    if not isinstance(name, str) or not name.strip() or len(name) > 200:
        raise ValueError('Podaj nazwę szablonu (do 200 znaków)')
    if kind not in ('offer', 'document'):
        raise ValueError('Wybierz ofertę lub dokument')
    if not isinstance(content, str) or not content.strip() or len(content) > 1000000:
        raise ValueError('Podaj treść szablonu (do 1 MB)')
    run_template(content, validate=True)
    if 'name' in data:
        data['name'] = name.strip()

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
        validate_content(data)
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
        validate_content(data, tpl)
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
    hard_delete(tpl)
    return jsonify({'message': 'Deleted'}), 200


@templates_bp.route('/preview', methods=['POST'])
@jwt_required()
@auth_limit(30, seconds=60, by_user=True, scope='template-render')
def preview_inline():
    if not any(has_permission(current_user(), 'templates.' + action) for action in ('create', 'edit')):
        return jsonify(error='Brak uprawnienia do podglądu szablonów'), 403
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify(error='Nieprawidłowe dane'), 400
    content = data.get('content', '')
    tpl_type = data.get('type', 'offer')
    try:
        variables = validate_variables({'variables': data.get('variables', [])})['variables']
        kind = db.session.get(DocumentType, data.get('document_type_key')) if data.get('document_type_key') else None
        return Response(render_preview(content, tpl_type, variables, kind.fields if kind else []), mimetype='text/html')
    except Exception as e:
        return Response(
            f'<pre style="color:red;padding:20px;font-family:monospace">'
            f'{escape(t("Błąd renderowania szablonu:"))}\n\n{escape(str(e))}</pre>',
            mimetype='text/html', status=400,
        )


@templates_bp.route('/<int:item_id>/preview', methods=['GET'])
@jwt_required()
@auth_limit(30, seconds=60, by_user=True, scope='template-render')
def preview_saved(item_id):
    if not any(has_permission(current_user(), 'templates.' + action) for action in ('create', 'edit')):
        return jsonify(error='Brak uprawnienia do podglądu szablonów'), 403
    tpl = Template.query.get_or_404(item_id)
    try:
        kind = db.session.get(DocumentType, tpl.document_type_key) if tpl.document_type_key else None
        return Response(render_preview(tpl.content, tpl.type or 'offer', tpl.variables or [], kind.fields if kind else []),
                        mimetype='text/html')
    except Exception as e:
        return Response(
            f'<pre style="color:red;padding:20px;font-family:monospace">'
            f'{escape(t("Błąd renderowania szablonu:"))}\n\n{escape(str(e))}</pre>',
            mimetype='text/html', status=400,
        )
