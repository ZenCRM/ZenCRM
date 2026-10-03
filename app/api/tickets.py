from datetime import datetime
import hmac
from flask import Blueprint, request, jsonify, abort, current_app
from flask_jwt_extended import jwt_required
from ..extensions import db
from ..models.ticket import Ticket, TicketMessage
from ..models.client import Client
from ..models.user import User
from ..models.team import Team
from ..utils.deletion import current_user, is_admin
from ..utils.helpdesk import get_helpdesk_config, save_helpdesk_config
from ..utils.auth_limits import auth_limit

tickets_bp = Blueprint('tickets', __name__)


from ..services.ticket_service import (
    public_base_url as _public_base_url,
    find_client_by_email as _find_client_by_email,
    apply_auto_assignment as _apply_auto_assignment,
    notify_ticket_created as _notify_ticket_created,
)


@tickets_bp.route('', methods=['GET'])
@jwt_required()
def list_tickets():
    user = current_user()
    if not user or not user.is_active:
        abort(403)

    query = Ticket.query

    client_id = request.args.get('client_id', type=int)
    if client_id:
        query = query.filter(Ticket.client_id == client_id)

    status = request.args.get('status')
    if status:
        query = query.filter(Ticket.status == status)

    category = request.args.get('category')
    if category:
        query = query.filter(Ticket.category == category)

    priority = request.args.get('priority')
    if priority:
        query = query.filter(Ticket.priority == priority)

    assignee_id = request.args.get('assignee_id', type=int)
    if assignee_id:
        query = query.filter(Ticket.assignee_id == assignee_id)

    team_id = request.args.get('team_id', type=int)
    if team_id:
        query = query.filter(Ticket.team_id == team_id)

    q = request.args.get('q', '').strip()
    if q:
        like_q = f'%{q}%'
        query = query.filter(
            db.or_(
                Ticket.ticket_number.ilike(like_q),
                Ticket.title.ilike(like_q),
                Ticket.contact_email.ilike(like_q),
                Ticket.contact_name.ilike(like_q),
                Ticket.description.ilike(like_q)
            )
        )

    tickets = query.order_by(Ticket.id.desc()).all()
    return jsonify([t.to_dict(include_messages=False) for t in tickets]), 200


@tickets_bp.route('/<int:ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket nie istnieje'}), 404
    return jsonify(ticket.to_dict(include_messages=True)), 200


@tickets_bp.route('', methods=['POST'])
@jwt_required()
def create_ticket():
    user = current_user()
    data = request.get_json(silent=True) or {}
    title = str(data.get('title', '')).strip()
    description = str(data.get('description', '')).strip()
    contact_email = str(data.get('contact_email', '')).strip().lower()

    if not title:
        return jsonify({'error': 'Tytuł zgłoszenia jest wymagany'}), 400
    if not description:
        return jsonify({'error': 'Opis zgłoszenia jest wymagany'}), 400
    if not contact_email:
        contact_email = user.email

    client_id = data.get('client_id')
    client = db.session.get(Client, client_id) if client_id else _find_client_by_email(contact_email)

    ticket = Ticket(
        ticket_number=Ticket.generate_number(),
        title=title,
        description=description,
        client_id=client.id if client else None,
        contact_name=data.get('contact_name') or (client.name if client else f"{user.first_name} {user.last_name}"),
        contact_email=contact_email,
        contact_phone=data.get('contact_phone') or (client.phone if client else None),
        category=data.get('category') or 'general',
        priority=data.get('priority') or 'medium',
        status=data.get('status') or 'new',
        assignee_id=data.get('assignee_id') or user.id,
        team_id=data.get('team_id'),
        token=Ticket.generate_token(),
        source='crm'
    )

    if not ticket.assignee_id and not ticket.team_id:
        _apply_auto_assignment(ticket, client)

    # Pierwsza wiadomość
    msg = TicketMessage(
        sender_type='agent',
        sender_name=f"{user.first_name} {user.last_name}",
        sender_email=user.email,
        user_id=user.id,
        content=description,
        is_internal=False
    )
    ticket.messages.append(msg)

    db.session.add(ticket)
    db.session.commit()
    _notify_ticket_created(ticket)
    return jsonify(ticket.to_dict(include_messages=True)), 201


@tickets_bp.route('/<int:ticket_id>', methods=['PUT'])
@jwt_required()
def update_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket nie istnieje'}), 404

    data = request.get_json(silent=True) or {}
    if 'title' in data:
        ticket.title = str(data['title']).strip()
    if 'category' in data:
        ticket.category = data['category']
    if 'priority' in data:
        ticket.priority = data['priority']
    if 'client_id' in data:
        ticket.client_id = data['client_id'] or None
    if 'assignee_id' in data:
        ticket.assignee_id = data['assignee_id'] or None
    if 'team_id' in data:
        ticket.team_id = data['team_id'] or None

    if 'status' in data:
        new_status = data['status']
        if new_status != ticket.status:
            ticket.status = new_status
            if new_status == 'resolved':
                ticket.resolved_at = datetime.utcnow()
            elif new_status == 'closed':
                ticket.closed_at = datetime.utcnow()

    db.session.commit()
    return jsonify(ticket.to_dict(include_messages=True)), 200


@tickets_bp.route('/<int:ticket_id>', methods=['DELETE'])
@jwt_required()
def delete_ticket(ticket_id):
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket nie istnieje'}), 404

    db.session.delete(ticket)
    db.session.commit()
    return jsonify({'ok': True, 'id': ticket_id}), 200


@tickets_bp.route('/<int:ticket_id>/messages', methods=['POST'])
@jwt_required()
def add_agent_message(ticket_id):
    user = current_user()
    ticket = db.session.get(Ticket, ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket nie istnieje'}), 404

    data = request.get_json(silent=True) or {}
    content = str(data.get('content', '')).strip()
    if not content:
        return jsonify({'error': 'Treść wiadomości jest wymagana'}), 400

    is_internal = bool(data.get('is_internal', False))

    msg = TicketMessage(
        ticket_id=ticket.id,
        sender_type='agent',
        sender_name=f"{user.first_name} {user.last_name}",
        sender_email=user.email,
        user_id=user.id,
        content=content,
        is_internal=is_internal
    )
    db.session.add(msg)

    # Jeśli odpowiedź została wysłana do klienta (nie notatka wewnętrzna), zmień status na oczekuje na klienta
    if not is_internal and ticket.status in ('new', 'open'):
        ticket.status = 'pending_client'

    ticket.updated_at = datetime.utcnow()
    db.session.commit()

    if not is_internal and ticket.contact_email:
        try:
            from ..services.email_service import send_notification
            from ..utils.helpdesk import get_helpdesk_config
            tracking_url = f"{request.host_url.rstrip('/')}{get_helpdesk_config().get('helpdesk_path', '/pomoc')}?ticket={ticket.token}"
            send_notification('client_ticket_reply', ticket.contact_email, {
                'client_name': ticket.contact_name or 'Kliencie',
                'agent_name': f"{user.first_name} {user.last_name}".strip(),
                'ticket_number': ticket.ticket_number,
                'ticket_title': ticket.title,
                'reply_content': content,
                'ticket_url': tracking_url,
            }, recipient_name=ticket.contact_name)
        except Exception:
            pass

    return jsonify(msg.to_dict()), 201


# ─────────────────────────────────────────────────────────────
# HELPDESK SETTINGS
# ─────────────────────────────────────────────────────────────
@tickets_bp.route('/settings', methods=['GET'])
@jwt_required()
def get_settings():
    config = get_helpdesk_config()
    if current_user().role not in ('admin', 'manager'):
        config.pop('helpdesk_webhook_token', None)
    return jsonify(config), 200


@tickets_bp.route('/settings', methods=['PUT'])
@jwt_required()
def update_settings():
    user = current_user()
    if not user or user.role not in ('admin', 'manager'):
        abort(403)
    data = request.get_json(silent=True) or {}
    updated = save_helpdesk_config(data)
    return jsonify(updated), 200


# ─────────────────────────────────────────────────────────────
# PUBLIC / HELPDESK PORTAL ENDPOINTS (Dla klienta bez logowania w CRM)
# ─────────────────────────────────────────────────────────────
@tickets_bp.route('/public/config', methods=['GET'])
def public_helpdesk_config():
    config = get_helpdesk_config()
    from ..utils.i18n import t
    from ..utils.helpdesk import DEFAULT_HELPDESK_CONFIG, DEFAULT_HELPDESK_CATEGORIES
    # Localize only unchanged system defaults, never administrator-authored copy.
    for key in ('title', 'header_subtitle', 'badge', 'heading', 'description', 'success_heading', 'success_description', 'footer_text'):
        name = 'helpdesk_' + key
        if config.get(name) == DEFAULT_HELPDESK_CONFIG.get(name):
            config[name] = t(config[name])
    defaults = {row['id']: row['name'] for row in DEFAULT_HELPDESK_CATEGORIES}
    config['helpdesk_categories'] = [dict(row, name=t(row['name']) if row.get('name') == defaults.get(row.get('id')) else row.get('name', '')) for row in config.get('helpdesk_categories', [])]
    logo = config.get('helpdesk_logo')
    if not logo:
        from ..models.setting import Setting
        brand = Setting.query.filter_by(key='brand_logo_light').first()
        if brand and brand.value:
            logo = brand.value
        else:
            logo = '/logo.png'

    return jsonify({
        'enabled': config.get('helpdesk_enabled', True),
        'path': config.get('helpdesk_path', '/pomoc'),
        'title': config.get('helpdesk_title', 'Centrum Pomocy'),
        'header_subtitle': config.get('helpdesk_header_subtitle', 'Wsparcie i obsługa zgłoszeń'),
        'badge': config.get('helpdesk_badge', 'Zgłoszenie serwisowe'),
        'heading': config.get('helpdesk_heading', 'W czym możemy Ci pomóc?'),
        'description': config.get('helpdesk_description', ''),
        'success_heading': config.get('helpdesk_success_heading', 'Zgłoszenie zostało wysłane!'),
        'success_description': config.get('helpdesk_success_description', 'Wysłaliśmy potwierdzenie na Twój adres e-mail wraz z bezpośrednim linkiem do śledzenia statusu zgłoszenia.'),
        'footer_text': config.get('helpdesk_footer_text', 'Obsługa klienta · Bezpieczny portal pomocy'),
        'logo': logo or '',
        'accent_color': config.get('helpdesk_accent_color', '#018bfc'),
        'categories': config.get('helpdesk_categories', [])
    }), 200


@tickets_bp.route('/public/submit', methods=['POST'])
@auth_limit(5, 3600)
def public_submit_ticket():
    config = get_helpdesk_config()
    if not config.get('helpdesk_enabled', True):
        return jsonify({'error': 'Portal pomocy jest obecnie wyłączony'}), 403

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or any(not isinstance(data.get(k, ''), str) for k in ('email', 'title', 'description', 'name', 'phone', 'category')):
        return jsonify({'error': 'Nieprawidłowe dane zgłoszenia'}), 400
    email = data.get('email', '').strip().lower()
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    name = data.get('name', '').strip() or None
    phone = data.get('phone', '').strip() or None
    category = data.get('category', 'general').strip()
    if len(email) > 120 or len(title) > 200 or len(description) > 5000 or len(name or '') > 100 or len(phone or '') > 50 or len(category) > 50:
        return jsonify({'error': 'Pole zgłoszenia jest za długie'}), 400
    allowed_categories = {str(item.get('id')) for item in config.get('helpdesk_categories', []) if isinstance(item, dict)}
    if category not in allowed_categories:
        return jsonify({'error': 'Nieprawidłowa kategoria'}), 400

    if not email or '@' not in email:
        return jsonify({'error': 'Prawidłowy adres e-mail jest wymagany'}), 400
    if not title:
        return jsonify({'error': 'Temat zgłoszenia jest wymagany'}), 400
    if not description:
        return jsonify({'error': 'Treść zgłoszenia jest wymagana'}), 400

    client = _find_client_by_email(email)

    token = Ticket.generate_token()
    ticket_num = Ticket.generate_number()

    ticket = Ticket(
        ticket_number=ticket_num,
        title=title,
        description=description,
        client_id=client.id if client else None,
        contact_name=name or email.split('@')[0],
        contact_email=email,
        contact_phone=phone,
        category=category,
        priority='medium',
        status='new',
        token=token,
        source='helpdesk'
    )

    _apply_auto_assignment(ticket, client)

    # Pierwsza wiadomość w wątku
    msg = TicketMessage(
        sender_type='client',
        sender_name=ticket.contact_name,
        sender_email=ticket.contact_email,
        content=description,
        is_internal=False
    )
    ticket.messages.append(msg)

    db.session.add(ticket)
    db.session.commit()
    _notify_ticket_created(ticket)

    tracking_url = f"{config.get('helpdesk_path', '/pomoc')}?ticket={token}"

    return jsonify({
        'ok': True,
        'ticket_number': ticket.ticket_number,
        'token': ticket.token,
        'tracking_url': tracking_url,
        'message': 'Zgłoszenie zostało pomyślnie przyjęte. Wysłaliśmy link do śledzenia zgłoszenia.'
    }), 201


@tickets_bp.route('/public/track/<string:token>', methods=['GET'])
def public_track_ticket(token):
    ticket = Ticket.query.filter_by(token=token).first()
    if not ticket:
        return jsonify({'error': 'Nie znaleziono zgłoszenia o podanym identyfikatorze'}), 404

    public_messages = [{
        'sender_type': m.sender_type,
        'sender_name': m.sender_name or ('Zespół Wsparcia' if m.sender_type == 'agent' else 'Klient'),
        'content': m.content,
        'created_at': m.created_at.isoformat() if m.created_at else None,
    } for m in ticket.messages if not m.is_internal]

    return jsonify({
        'ticket_number': ticket.ticket_number,
        'title': ticket.title,
        'description': ticket.description,
        'category': ticket.category,
        'status': ticket.status,
        'created_at': ticket.created_at.isoformat() if ticket.created_at else None,
        'updated_at': ticket.updated_at.isoformat() if ticket.updated_at else None,
        'contact_name': ticket.contact_name,
        'contact_email': ticket.contact_email,
        'messages': public_messages
    }), 200


@tickets_bp.route('/public/track/<string:token>/reply', methods=['POST'])
@auth_limit(20, 3600)
def public_reply_ticket(token):
    ticket = Ticket.query.filter_by(token=token).first()
    if not ticket:
        return jsonify({'error': 'Nie znaleziono zgłoszenia o podanym identyfikatorze'}), 404

    if ticket.status == 'closed':
        return jsonify({'error': 'To zgłoszenie zostało już zamknięte'}), 400

    data = request.get_json(silent=True) or {}
    content = data.get('content', '') if isinstance(data, dict) else ''
    if not isinstance(content, str) or not content.strip() or len(content) > 5000:
        return jsonify({'error': 'Treść odpowiedzi jest wymagana'}), 400
    content = content.strip()

    msg = TicketMessage(
        ticket_id=ticket.id,
        sender_type='client',
        sender_name=ticket.contact_name,
        sender_email=ticket.contact_email,
        content=content,
        is_internal=False
    )
    db.session.add(msg)

    # Jeśli ticket był nowy, w stanie oczekiwania na klienta lub rozwiązany, otwórz go
    if ticket.status in ('new', 'pending_client', 'resolved'):
        ticket.status = 'open'

    ticket.updated_at = datetime.utcnow()
    db.session.commit()

    if ticket.assignee:
        try:
            from ..services.email_service import send_notification
            crm_ticket_url = f"{_public_base_url()}/#tickets" if _public_base_url() else ''
            send_notification('employee_ticket_reply', ticket.assignee.email, {
                'employee_name': ticket.assignee.first_name,
                'client_name': ticket.contact_name or 'Klient',
                'ticket_number': ticket.ticket_number,
                'ticket_title': ticket.title,
                'reply_content': content,
                'crm_ticket_url': crm_ticket_url,
            }, user=ticket.assignee)
        except Exception:
            pass

    return jsonify(msg.to_dict()), 201


# ─────────────────────────────────────────────────────────────
# WEBHOOK DO ZBIERANIA TICKETÓW
# ─────────────────────────────────────────────────────────────
@tickets_bp.route('/webhook', methods=['POST'])
def webhook_submit_ticket():
    config = get_helpdesk_config()
    if not config.get('helpdesk_webhook_enabled', True):
        return jsonify({'error': 'Webhook zgłoszeń jest wyłączony'}), 403

    expected_token = config.get('helpdesk_webhook_token', '')
    req_token = request.headers.get('X-Webhook-Token', '')

    if not expected_token or not hmac.compare_digest(req_token, expected_token):
        return jsonify({'error': 'Nieprawidłowy token autoryzacyjny webhooka'}), 401

    data = request.get_json(silent=True) or request.form.to_dict() or {}

    email = str(data.get('email') or data.get('contact_email') or '').strip().lower()
    title = str(data.get('title') or data.get('subject') or '').strip()
    description = str(data.get('description') or data.get('message') or data.get('content') or '').strip()

    if not email or '@' not in email:
        return jsonify({'error': 'Pole email jest wymagane'}), 400
    if not title:
        return jsonify({'error': 'Pole title/subject jest wymagane'}), 400
    if not description:
        return jsonify({'error': 'Pole description/message jest wymagane'}), 400

    client = _find_client_by_email(email)
    token = Ticket.generate_token()
    ticket_num = Ticket.generate_number()

    ticket = Ticket(
        ticket_number=ticket_num,
        title=title,
        description=description,
        client_id=client.id if client else None,
        contact_name=str(data.get('name') or data.get('contact_name') or '').strip() or (client.name if client else email.split('@')[0]),
        contact_email=email,
        contact_phone=str(data.get('phone') or data.get('contact_phone') or '').strip() or (client.phone if client else None),
        category=str(data.get('category') or 'general').strip(),
        priority=str(data.get('priority') or 'medium').strip(),
        status='new',
        token=token,
        source='webhook'
    )

    _apply_auto_assignment(ticket, client)

    msg = TicketMessage(
        sender_type='client',
        sender_name=ticket.contact_name,
        sender_email=ticket.contact_email,
        content=description,
        is_internal=False
    )
    ticket.messages.append(msg)

    db.session.add(ticket)
    db.session.commit()
    _notify_ticket_created(ticket)

    tracking_url = f"{config.get('helpdesk_path', '/pomoc')}?ticket={token}"

    return jsonify({
        'ok': True,
        'id': ticket.id,
        'ticket_number': ticket.ticket_number,
        'token': ticket.token,
        'tracking_url': tracking_url
    }), 201
