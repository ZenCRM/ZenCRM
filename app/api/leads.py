import hmac
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.lead import Lead
from ..models.client import Client
from ..models.contact import Contact
from ..models.task import Task
from ..models.document import Document
from ..utils.sanitize import apply_payload, build_model
from ..utils.deletion import soft_delete, restore, hard_delete, is_admin
from ..utils.activity import log_activity

leads_bp = Blueprint('leads', __name__)


@leads_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    from flask import request
    q = Lead.query.filter(Lead.deleted_at == None)
    cid = request.args.get('client_id', type=int)
    if cid is not None:
        q = q.filter(Lead.client_id == cid)
    items = q.order_by(Lead.id.desc()).all()
    return jsonify([x.to_dict() for x in items]), 200


@leads_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    lead = db.session.get(Lead, item_id)
    if not lead:
        return jsonify({'error': 'Lead nie istnieje'}), 404
    return jsonify(lead.to_dict()), 200


@leads_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        lead = build_model(Lead, data)
        db.session.add(lead)
        db.session.flush()
        log_activity('lead', lead.id, 'created', f'Utworzono lead: {lead.title}')
        db.session.commit()
        return jsonify(lead.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@leads_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    lead = db.session.get(Lead, item_id)
    if not lead:
        return jsonify({'error': 'Lead nie istnieje'}), 404
    try:
        apply_payload(lead, request.get_json(silent=True) or {})
        log_activity('lead', lead.id, 'updated', 'Zaktualizowano lead')
        db.session.commit()
        return jsonify(lead.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@leads_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    lead = db.session.get(Lead, item_id)
    if not lead:
        return jsonify({'error': 'Lead nie istnieje'}), 404
    soft_delete(lead)
    return jsonify({'ok': True, 'archived': True}), 200


@leads_bp.route('/<int:item_id>/restore', methods=['POST'])
@jwt_required()
def restore_item(item_id):
    lead = db.session.get(Lead, item_id)
    if not lead:
        return jsonify({'error': 'Nie istnieje'}), 404
    restore(lead)
    return jsonify({'ok': True}), 200


@leads_bp.route('/<int:item_id>/permanent', methods=['DELETE'])
@jwt_required()
def permanent_delete(item_id):
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    lead = db.session.get(Lead, item_id)
    if not lead:
        return jsonify({'error': 'Nie istnieje'}), 404
    hard_delete(lead)
    return jsonify({'ok': True}), 200


@leads_bp.route('/<int:item_id>/convert', methods=['POST'])
@jwt_required()
def convert_lead(item_id):
    lead = db.session.get(Lead, item_id)
    if not lead:
        return jsonify({'error': 'Lead nie istnieje'}), 404
    if lead.converted_to_client_id:
        return jsonify({'error': 'Lead zostal juz przekonwertowany'}), 400
    data = request.get_json(silent=True) or {}
    try:
        client = Client(
            name=data.get('name') or lead.title,
            email=data.get('email'),
            phone=data.get('phone'),
            company=data.get('company'),
            address=data.get('address'),
            status='active',
            notes=data.get('notes') or f'Utworzony z leada #{lead.id}: {lead.title}',
            assignee_id=lead.assignee_id,
        )
        db.session.add(client)
        db.session.flush()
        Contact.query.filter_by(lead_id=lead.id).update({'client_id': client.id, 'lead_id': None})
        Task.query.filter_by(lead_id=lead.id).update({'client_id': client.id, 'lead_id': None})
        Document.query.filter_by(lead_id=lead.id).update({'client_id': client.id, 'lead_id': None})
        from ..models.meeting import Meeting
        Meeting.query.filter_by(lead_id=lead.id).update({'client_id': client.id, 'lead_id': None})
        lead.converted_to_client_id = client.id
        lead.stage = 'won'
        log_activity('lead', lead.id, 'converted', f'Przekonwertowano na klienta: {client.name}')
        log_activity('client', client.id, 'created', f'Utworzony z leada: {lead.title}')
        db.session.commit()
        return jsonify({'ok': True, 'client_id': client.id, 'client': client.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@leads_bp.route('/board-settings', methods=['GET', 'PUT'])
@jwt_required()
def board_settings():
    import json
    from ..models.setting import Setting
    from ..utils.lead_stages import get_stages, validate_stages
    if request.method == 'GET':
        return jsonify({'stages': get_stages()})
    if not is_admin():
        return jsonify({'error': 'Statusy dla zespołu ustawia administrator.'}), 403
    try:
        stages = validate_stages((request.get_json(silent=True) or {}).get('stages'))
        Setting.set_value('lead_stages', json.dumps(stages, ensure_ascii=False), 'leads')
        db.session.commit()
        return jsonify({'stages': stages})
    except ValueError as error:
        return jsonify({'error': str(error)}), 400


@leads_bp.route('/webhook', methods=['POST'])
def webhook_submit_lead():
    """Zewnętrzny webhook do dodawania leadów z formularzy kontaktowych / landing page."""
    from ..models.setting import Setting
    enabled = Setting.get_value('lead_webhook_enabled', 'true')
    if enabled.lower() not in ('true', '1', 'yes'):
        return jsonify({'error': 'Webhook zgłoszeń leadów jest wyłączony'}), 403

    expected_token = Setting.get_value('lead_webhook_token', '')
    req_token = request.headers.get('X-Webhook-Token', '')

    if not expected_token or not hmac.compare_digest(req_token, expected_token):
        return jsonify({'error': 'Nieprawidłowy token autoryzacyjny webhooka'}), 401

    data = request.get_json(silent=True) or request.form.to_dict() or {}
    title = (data.get('title') or '').strip()
    client_name = (data.get('client_name') or data.get('company') or data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    phone = (data.get('phone') or '').strip()
    source = (data.get('source') or 'Formularz WWW').strip()
    notes = (data.get('notes') or data.get('message') or data.get('description') or '').strip()

    value = None
    if data.get('value') is not None and str(data.get('value')).strip():
        try:
            value = float(str(data.get('value')).replace(',', '.'))
        except (ValueError, TypeError):
            value = None

    if not title:
        if client_name:
            title = f'Lead: {client_name}'
        elif email:
            title = f'Lead: {email}'
        elif phone:
            title = f'Lead: {phone}'
        else:
            title = 'Nowy lead z webhooka'

    client_id = data.get('client_id')
    if not client_id and (client_name or email or phone):
        cl = None
        if email:
            cl = Client.query.filter_by(email=email).first()
        if not cl and phone:
            cl = Client.query.filter_by(phone=phone).first()
        if not cl and client_name:
            cl = Client.query.filter_by(name=client_name).first()
        if not cl:
            cl = Client(
                name=client_name or email or phone or 'Nowy Klient',
                email=email or None,
                phone=phone or None,
                company=data.get('company') or None,
                status='prospect'
            )
            db.session.add(cl)
            db.session.flush()
        client_id = cl.id

    lead = Lead(
        title=title,
        client_id=client_id,
        value=value,
        stage='new',
        source=source,
        notes=notes or None
    )
    db.session.add(lead)
    db.session.flush()
    log_activity('lead', lead.id, 'created', f'Nowy lead z webhooka ({source}): {title}')
    db.session.commit()

    return jsonify({'success': True, 'lead_id': lead.id, 'lead': lead.to_dict()}), 201
