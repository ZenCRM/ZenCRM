from ..utils.i18n import t
import os
import secrets
from flask import Blueprint, request, jsonify, send_file, Response, current_app
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.document import Document
from ..models.template import Template
from ..models.document_type import DocumentType
from ..services.render_service import render_document
from ..services.pdf_service import html_to_pdf
from ..utils.sanitize import apply_payload, build_model
from ..utils.activity import log_activity
from ..utils.deletion import soft_delete
from .public import rendered_html_response

documents_bp = Blueprint('documents', __name__)
PDF_DIR = 'generated/documents'


def _validate_relations(doc):
    """Optional associations must belong to the document's selected client."""
    from ..models.lead import Lead
    from ..models.service import Service
    for field, model, label in (('lead_id', Lead, 'Lead'), ('service_id', Service, 'Usługa')):
        value = getattr(doc, field)
        if value is None:
            continue
        related = db.session.get(model, value)
        if not related:
            raise ValueError(t('{label} nie istnieje', {'label': t(label)}))
        if doc.client_id and related.client_id != doc.client_id:
            raise ValueError(t('{label} nie należy do wybranego klienta', {'label': t(label)}))


def _ensure_token(doc):
    if not doc.public_token:
        doc.public_token = secrets.token_urlsafe(32)
    return doc.public_token


def _ensure_template(doc):
    if doc.template_id:
        tpl = db.session.get(Template, doc.template_id)
        if not tpl or tpl.type != 'document' or (tpl.document_type_key and tpl.document_type_key != doc.type):
            raise ValueError('Szablon nie pasuje do typu dokumentu')
        return True
    tpl = Template.query.filter_by(type='document', document_type_key=doc.type, is_active=True).first()
    if not tpl:
        tpl = Template.query.filter_by(type='document', document_type_key=None, is_active=True).first()
    if not tpl:
        return False
    doc.template_id = tpl.id
    return True


def _validate_type_fields(doc):
    kind = db.session.get(DocumentType, doc.type or 'other')
    if not kind:
        raise ValueError('Typ dokumentu nie istnieje')
    values = (doc.data or {}).get('type_fields', {})
    if not isinstance(values, dict):
        raise ValueError('Nieprawidłowe pola typu dokumentu')
    from datetime import date
    from decimal import Decimal, InvalidOperation
    for field in kind.fields or []:
        value = values.get(field['key'], '')
        if field.get('required') and (value == '' or value is None):
            raise ValueError('Wymagane pole: ' + field['label'])
        if value in ('', None):
            continue
        try:
            if field['kind'] == 'number' and not Decimal(str(value).replace(',', '.')).is_finite():
                raise ValueError()
            if field['kind'] == 'date':
                date.fromisoformat(str(value))
            if field['kind'] == 'boolean' and not isinstance(value, bool):
                raise ValueError()
            if field['kind'] == 'select' and value not in field['options']:
                raise ValueError()
            if len(str(value)) > 10000:
                raise ValueError()
        except (ValueError, InvalidOperation, TypeError):
            raise ValueError('Nieprawidłowa wartość pola: ' + field['label'])


@documents_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    q = Document.query.filter(Document.deleted_at == None)
    client_id = request.args.get('client_id', type=int)
    lead_id = request.args.get('lead_id', type=int)
    if client_id is not None:
        q = q.filter_by(client_id=client_id)
    if lead_id is not None:
        q = q.filter_by(lead_id=lead_id)
    items = q.order_by(Document.id.desc()).all()
    return jsonify([d.to_dict() for d in items]), 200


@documents_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    d = db.session.get(Document, item_id)
    if not d:
        return jsonify({'error': 'Dokument nie istnieje'}), 404
    return jsonify(d.to_dict()), 200


@documents_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        doc = build_model(Document, data)
        _validate_type_fields(doc)
        _validate_relations(doc)
        _ensure_token(doc)
        if doc.template_id:
            _ensure_template(doc)
        db.session.add(doc)
        db.session.flush()
        log_activity('document', doc.id, 'created', 'Utworzono dokument: ' + doc.title)
        db.session.commit()
        return jsonify(doc.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@documents_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    d = db.session.get(Document, item_id)
    if not d:
        return jsonify({'error': 'Dokument nie istnieje'}), 404
    try:
        apply_payload(d, request.get_json(silent=True) or {})
        _validate_type_fields(d)
        _validate_relations(d)
        if d.template_id:
            _ensure_template(d)
        db.session.commit()
        return jsonify(d.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@documents_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    d = db.session.get(Document, item_id)
    if not d:
        return jsonify({'error': 'Dokument nie istnieje'}), 404
    soft_delete(d, 'document')
    db.session.commit()
    return jsonify({'message': 'Deleted'}), 200


@documents_bp.route('/<int:item_id>/generate', methods=['POST'])
@jwt_required()
def generate_document(item_id):
    doc = db.session.get(Document, item_id)
    if not doc:
        return jsonify({'error': 'Dokument nie istnieje'}), 404
    data = request.get_json(silent=True) or {}
    try:
        if 'data' in data:
            doc.data = data['data']
        if 'template_id' in data and data['template_id']:
            doc.template_id = data['template_id']
        if not _ensure_template(doc):
            return jsonify({'error': 'Brak szablonow dokumentow. Dodaj szablon w menu Szablony.'}), 400
        _ensure_token(doc)
        _validate_type_fields(doc)
        html = render_document(doc)
        db.session.commit()
        return jsonify({
            'ok': True,
            'public_token': doc.public_token,
            'public_url': '/api/public/document/' + doc.public_token,
            'html_length': len(html or ''),
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Document generation failed')
        return jsonify({'error': 'Nie udało się wygenerować dokumentu'}), 500


@documents_bp.route('/<int:item_id>/view', methods=['GET'])
@jwt_required()
def view_document(item_id):
    d = db.session.get(Document, item_id)
    if not d:
        return jsonify({'error': 'Dokument nie istnieje'}), 404
    if not d.rendered_html:
        try:
            if not _ensure_template(d):
                return jsonify({'error': 'Brak szablonow dokumentow.'}), 400
            render_document(d)
            _ensure_token(d)
            db.session.commit()
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    return rendered_html_response(d.rendered_html)


@documents_bp.route('/<int:item_id>/pdf', methods=['GET'])
@jwt_required()
def download_pdf(item_id):
    d = db.session.get(Document, item_id)
    if not d:
        return jsonify({'error': 'Dokument nie istnieje'}), 404
    if not d.rendered_html:
        try:
            if not _ensure_template(d):
                return jsonify({'error': 'Brak szablonow dokumentow.'}), 400
            render_document(d)
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    safe_title = ''.join(c if c.isalnum() or c in '-_' else '_' for c in d.title)[:60]
    pdf_path = os.path.join(PDF_DIR, safe_title + '_' + str(d.id) + '.pdf')
    result = html_to_pdf(d.rendered_html, pdf_path)
    if not result:
        return jsonify({'error': 'Nie udalo sie wygenerowac PDF.'}), 500
    d.pdf_path = pdf_path
    db.session.commit()
    return send_file(os.path.abspath(pdf_path),
                     mimetype='application/pdf',
                     as_attachment=True,
                     download_name=safe_title + '.pdf')


@documents_bp.route('/<int:item_id>/link', methods=['POST'])
@jwt_required()
def share_link(item_id):
    d = db.session.get(Document, item_id)
    if not d:
        return jsonify({'error': 'Dokument nie istnieje'}), 404
    if not _ensure_template(d):
        return jsonify({'error': 'Brak szablonow dokumentow.'}), 400
    _ensure_token(d)
    if not d.rendered_html:
        try:
            render_document(d)
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    db.session.commit()
    return jsonify({
        'public_token': d.public_token,
        'public_url':   '/api/public/document/' + d.public_token,
    }), 200
