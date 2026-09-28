from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.client import Client
from ..models.lead import Lead
from ..utils.sanitize import apply_payload, build_model
from ..utils.deletion import soft_delete, restore, hard_delete, is_admin
from ..utils.activity import log_activity

clients_bp = Blueprint('clients', __name__)


@clients_bp.route('', methods=['GET'])
@jwt_required()
def list_items():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    q = Client.query.filter(Client.deleted_at == None)
    if search:
        q = q.filter(Client.name.ilike(f'%{search}%'))
    paginated = q.order_by(Client.created_at.desc()).paginate(
        page=page, per_page=100, error_out=False)
    return jsonify({
        'clients': [c.to_dict() for c in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page,
    }), 200


@clients_bp.route('/<int:item_id>', methods=['GET'])
@jwt_required()
def get_item(item_id):
    c = db.session.get(Client, item_id)
    if not c:
        return jsonify({'error': 'Klient nie istnieje'}), 404
    data = c.to_dict()
    lead = Lead.query.filter_by(converted_to_client_id=item_id).first()
    if lead:
        data['converted_from_lead'] = {
            'id': lead.id, 'title': lead.title,
            'value': float(lead.value) if lead.value else 0,
            'stage': lead.stage, 'source': lead.source,
            'created_at': lead.created_at.isoformat() if lead.created_at else None,
        }
    else:
        data['converted_from_lead'] = None
    return jsonify(data), 200


def _notify_client_assigned(client, assignee_id):
    try:
        from ..models.user import User
        from ..services.email_service import send_notification
        u = db.session.get(User, assignee_id)
        if u and u.email:
            crm_client_url = f"{request.host_url.rstrip('/')}/#clients/{client.id}"
            send_notification('employee_client_assigned', u.email, {
                'employee_name': u.first_name or u.email,
                'client_name': client.name or 'Klient',
                'client_email': client.email or 'Brak',
                'client_phone': client.phone or 'Brak',
                'crm_client_url': crm_client_url,
            }, user=u)
    except Exception:
        pass


@clients_bp.route('', methods=['POST'])
@jwt_required()
def create_item():
    data = request.get_json(silent=True) or {}
    try:
        c = build_model(Client, data)
        db.session.add(c)
        db.session.flush()
        log_activity('client', c.id, 'created', f'Utworzono klienta: {c.name}')
        db.session.commit()
        if c.assignee_id:
            _notify_client_assigned(c, c.assignee_id)
        return jsonify(c.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@clients_bp.route('/<int:item_id>', methods=['PUT'])
@jwt_required()
def update_item(item_id):
    c = db.session.get(Client, item_id)
    if not c:
        return jsonify({'error': 'Klient nie istnieje'}), 404
    try:
        old_assignee_id = c.assignee_id
        apply_payload(c, request.get_json(silent=True) or {})
        log_activity('client', c.id, 'updated', 'Zaktualizowano')
        db.session.commit()
        if c.assignee_id and c.assignee_id != old_assignee_id:
            _notify_client_assigned(c, c.assignee_id)
        return jsonify(c.to_dict()), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400


@clients_bp.route('/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(item_id):
    c = db.session.get(Client, item_id)
    if not c:
        return jsonify({'error': 'Klient nie istnieje'}), 404
    soft_delete(c)
    try:
        log_activity('client', c.id, 'archived', f'Przeniesiono klienta do archiwum: {c.name}')
        db.session.commit()
    except Exception:
        pass
    return jsonify({'ok': True, 'archived': True}), 200


@clients_bp.route('/<int:item_id>/restore', methods=['POST'])
@jwt_required()
def restore_item(item_id):
    c = db.session.get(Client, item_id)
    if not c:
        return jsonify({'error': 'Nie istnieje'}), 404
    restore(c)
    return jsonify({'ok': True}), 200


@clients_bp.route('/<int:item_id>/permanent', methods=['DELETE'])
@jwt_required()
def permanent_delete(item_id):
    if not is_admin():
        return jsonify({'error': 'Wymagane uprawnienia administratora'}), 403
    c = db.session.get(Client, item_id)
    if not c:
        return jsonify({'error': 'Nie istnieje'}), 404
    hard_delete(c)
    return jsonify({'ok': True}), 200
