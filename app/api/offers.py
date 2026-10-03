import os
from flask import Blueprint, request, jsonify, send_file, Response, current_app
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.offer import Offer
from ..models.template import Template
from ..services.render_service import render_offer
from ..services.pdf_service import html_to_pdf
from ..utils.sanitize import apply_payload, build_model
from ..utils.activity import log_activity
from ..utils.deletion import soft_delete
from ..utils.http_responses import rendered_html_response

offers_bp = Blueprint('offers', __name__)
PDF_DIR = 'generated/offers'


from ..services.offer_service import (
    ensure_token as _ensure_token,
    ensure_template as _ensure_template,
)


@offers_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    items = Offer.query.filter(Offer.deleted_at == None).order_by(Offer.id.desc()).all()
    return jsonify([o.to_dict() for o in items]), 200


@offers_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    o = db.session.get(Offer, item_id)
    if not o:
        return jsonify({'error': 'Oferta nie istnieje'}), 404
    return jsonify(o.to_dict()), 200


@offers_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        offer = build_model(Offer, data)
        _ensure_token(offer)
        if not offer.template_id:
            tpl = Template.query.filter_by(type='offer', is_active=True).first()
            if tpl:
                offer.template_id = tpl.id
        db.session.add(offer)
        db.session.flush()
        log_activity('offer', offer.id, 'created', f'Utworzono ofertę: {offer.number}')
        db.session.commit()
        return jsonify(offer.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@offers_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    o = db.session.get(Offer, item_id)
    if not o:
        return jsonify({'error': 'Oferta nie istnieje'}), 404
    try:
        apply_payload(o, request.get_json(silent=True) or {})
        db.session.commit()
        return jsonify(o.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@offers_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    o = db.session.get(Offer, item_id)
    if not o:
        return jsonify({'error': 'Oferta nie istnieje'}), 404
    soft_delete(o, 'offer')
    return jsonify({'message': 'Deleted'}), 200


@offers_bp.route('/<int:item_id>/generate', methods=['POST'])
@jwt_required()
def generate_offer(item_id):
    offer = db.session.get(Offer, item_id)
    if not offer:
        return jsonify({'error': 'Oferta nie istnieje'}), 404
    data = request.get_json(silent=True) or {}
    try:
        if 'data' in data:
            offer.data = data['data']
        if 'template_id' in data and data['template_id']:
            offer.template_id = data['template_id']
        if not _ensure_template(offer):
            return jsonify({
                'error': 'Brak szablonów ofert. Dodaj szablon w menu "Szablony".',
            }), 400
        _ensure_token(offer)
        html = render_offer(offer)
        db.session.commit()
        return jsonify({
            'ok': True,
            'public_token': offer.public_token,
            'public_url': f'/api/public/offer/{offer.public_token}',
            'html_length': len(html or ''),
        }), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.exception('Offer generation failed')
        return jsonify({'error': 'Nie udało się wygenerować oferty'}), 500


@offers_bp.route('/<int:item_id>/view', methods=['GET'])
@jwt_required()
def view_offer(item_id):
    offer = db.session.get(Offer, item_id)
    if not offer:
        return jsonify({'error': 'Oferta nie istnieje'}), 404
    if not offer.rendered_html:
        try:
            if not _ensure_template(offer):
                return jsonify({'error': 'Brak szablonów ofert.'}), 400
            render_offer(offer)
            _ensure_token(offer)
            db.session.commit()
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    return rendered_html_response(offer.rendered_html)


@offers_bp.route('/<int:item_id>/pdf', methods=['GET'])
@jwt_required()
def download_pdf(item_id):
    offer = db.session.get(Offer, item_id)
    if not offer:
        return jsonify({'error': 'Oferta nie istnieje'}), 404
    if not offer.rendered_html:
        try:
            if not _ensure_template(offer):
                return jsonify({'error': 'Brak szablonów ofert.'}), 400
            render_offer(offer)
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    safe_number = offer.number.replace('/', '_').replace('\\', '_')
    pdf_path = os.path.join(PDF_DIR, f'{safe_number}.pdf')
    result = html_to_pdf(offer.rendered_html, pdf_path)
    if not result:
        return jsonify({'error': 'Nie udało się wygenerować PDF.'}), 500
    offer.pdf_path = pdf_path
    db.session.commit()
    return send_file(os.path.abspath(pdf_path),
                     mimetype='application/pdf',
                     as_attachment=True,
                     download_name=f'{safe_number}.pdf')


@offers_bp.route('/<int:item_id>/link', methods=['POST'])
@jwt_required()
def share_link(item_id):
    offer = db.session.get(Offer, item_id)
    if not offer:
        return jsonify({'error': 'Oferta nie istnieje'}), 404
    if not _ensure_template(offer):
        return jsonify({'error': 'Brak szablonów ofert.'}), 400
    _ensure_token(offer)
    if not offer.rendered_html:
        try:
            render_offer(offer)
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400
    db.session.commit()
    return jsonify({
        'public_token': offer.public_token,
        'public_url':   f'/api/public/offer/{offer.public_token}',
    }), 200
