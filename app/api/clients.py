from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.client import Client
from ..models.lead import Lead
from ..utils.sanitize import apply_payload, build_model
from ..utils.deletion import soft_delete, restore, hard_delete, is_admin
from ..utils.activity import log_activity

clients_bp = Blueprint('clients', __name__)
ADDRESS_FIELDS = ('street', 'building_number', 'apartment_number', 'postal_code', 'city', 'country')


def _prepare_client_data(data):
    if not isinstance(data, dict):
        raise ValueError('Niepoprawne dane klienta.')
    data = dict(data)
    if 'status' in data:
        from ..utils.client_statuses import get_statuses
        if data['status'] not in {s['id'] for s in get_statuses()}:
            raise ValueError('Wybierz poprawny status klienta.')
    for key in ('nip', 'regon', 'krs', *ADDRESS_FIELDS):
        if key not in data:
            continue
        value = data[key]
        if value is None or value == '':
            data[key] = None
            continue
        if not isinstance(value, str):
            raise ValueError(f'Pole {key} musi być tekstem.')
        value = value.strip()
        if key == 'nip' and value:
            from ..services.gus_service import normalize_nip
            value = normalize_nip(value)
        elif key in ('regon', 'krs') and value:
            import re
            value = re.sub(r'[\s-]', '', value)
            lengths = (9, 14) if key == 'regon' else (10,)
            if not re.fullmatch(r'[0-9]+', value) or len(value) not in lengths:
                raise ValueError('REGON musi mieć 9 lub 14 cyfr.' if key == 'regon' else 'KRS musi mieć 10 cyfr.')
        if len(value) > Client.__table__.columns[key].type.length:
            raise ValueError(f'Pole {key} jest za długie.')
        data[key] = value or None
    return data


def _sync_address(client, data, previously_structured=False, previous_address=None):
    if not any(key in data for key in ADDRESS_FIELDS):
        return
    structured = any(getattr(client, key) for key in ADDRESS_FIELDS)
    if not structured and data.get('address') and data['address'] != previous_address:
        return
    if structured or previously_structured:
        street = ' '.join(v for v in (client.street, client.building_number) if v)
        if client.apartment_number:
            street += '/' + client.apartment_number
        locality = ' '.join(v for v in (client.postal_code, client.city) if v)
        client.address = ', '.join(v for v in (street, locality, client.country) if v) or None


@clients_bp.route('/company-lookup', methods=['GET'])
@clients_bp.route('/gus', methods=['GET'])
@jwt_required()
def gus_lookup():
    from ..utils.deletion import current_user
    from ..utils.permissions import has_permission
    from ..services.gus_service import lookup_company, GusError
    user = current_user()
    if not any(has_permission(user, f'clients.{action}') for action in ('create', 'edit')):
        return jsonify({'error': 'Brak uprawnienia do tej operacji'}), 403
    from ..services.company_lookup import provider, lookup_mf
    selected = provider()
    if selected == 'off':
        return jsonify({'error': 'Wyszukiwarka firm jest wyłączona w ustawieniach CRM.'}), 403
    try:
        result = (lookup_mf if selected == 'mf' else lookup_company)(request.args.get('nip', ''))
        if result is None:
            return jsonify({'error': 'Nie znaleziono firmy w wybranym rejestrze dla podanego NIP.'}), 404
        return jsonify(result), 200
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    except GusError as exc:
        return jsonify({'error': str(exc)}), 503



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
        from ..services.email_service import send_notification, staff_link_base_url
        u = db.session.get(User, assignee_id)
        if u and u.email:
            crm_client_url = f"{staff_link_base_url()}/#clients/{client.id}"
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
        data = _prepare_client_data(data)
        if 'status' not in data:
            from ..utils.client_statuses import get_statuses
            statuses = get_statuses()
            data['status'] = 'active' if any(s['id'] == 'active' for s in statuses) else statuses[0]['id']
        c = build_model(Client, data)
        _sync_address(c, data)
        db.session.add(c)
        db.session.flush()
        log_activity('client', c.id, 'created', f'Utworzono klienta: {c.name}')
        from ..plugins.events import emit_client_event
        emit_client_event('client.created.v1', c.id)
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
        data = _prepare_client_data(request.get_json(silent=True) or {})
        previous_address = c.address
        previously_structured = any(getattr(c, key) for key in ADDRESS_FIELDS)
        apply_payload(c, data)
        _sync_address(c, data, previously_structured, previous_address)
        log_activity('client', c.id, 'updated', 'Zaktualizowano')
        from ..plugins.events import emit_client_event
        emit_client_event('client.updated.v1', c.id)
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
