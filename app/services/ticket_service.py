"""Tickets domain helpers. The API caller owns authorization and transactions."""
from urllib.parse import urlsplit
from flask import current_app
from ..extensions import db
from ..models.client import Client
from ..models.contact import Contact
from ..utils.helpdesk import get_helpdesk_config


def public_base_url():
    from ..models.setting import Setting
    value = current_app.config.get('PUBLIC_BASE_URL') or Setting.get_value('company_www', '') or ''
    value = value.strip()
    if value and '://' not in value:
        value = 'https://' + value
    parsed = urlsplit(value)
    if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
        return ''
    return f'{parsed.scheme}://{parsed.netloc}'


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def find_client_by_email(email):
    if not email:
        return None
    email_clean = str(email).strip().lower()
    client = Client.query.filter(
        db.func.lower(Client.email) == email_clean,
        Client.deleted_at.is_(None)
    ).first()
    if client:
        return client
    contact = Contact.query.filter(
        db.func.lower(Contact.email) == email_clean
    ).first()
    if contact and contact.client_id:
        return db.session.get(Client, contact.client_id)
    return None


def apply_auto_assignment(ticket, client=None):
    config = get_helpdesk_config()
    # 1. Jeśli klient ma przypisanego opiekuna w CRM -> przypisz do opiekuna
    if client and client.assignee_id:
        ticket.assignee_id = client.assignee_id
        return

    # 2. W przeciwnym razie sprawdź regułę automatycznego przydzielania z ustawień
    if config.get('helpdesk_auto_assign'):
        target = config.get('helpdesk_auto_assign_target', 'team')
        if target == 'team' and config.get('helpdesk_default_team_id'):
            ticket.team_id = config['helpdesk_default_team_id']
        elif target == 'user' and config.get('helpdesk_default_user_id'):
            ticket.assignee_id = config['helpdesk_default_user_id']


def notify_ticket_created(ticket):
    try:
        from ..services.email_service import send_notification
        from ..utils.helpdesk import get_helpdesk_config
        config = get_helpdesk_config()
        base_url = public_base_url()
        if not base_url:
            current_app.logger.warning('Set PUBLIC_BASE_URL to enable ticket notification links')
            return
        tracking_url = f"{base_url}{config.get('helpdesk_path', '/pomoc')}?ticket={ticket.token}"

        # 1. Do klienta (potwierdzenie rejestracji)
        if ticket.contact_email:
            send_notification('client_ticket_created', ticket.contact_email, {
                'client_name': ticket.contact_name or 'Kliencie',
                'ticket_number': ticket.ticket_number,
                'ticket_title': ticket.title,
                'ticket_category': ticket.category or 'Ogólne',
                'ticket_url': tracking_url,
            }, recipient_name=ticket.contact_name)

        # 2. Do przypisanego pracownika
        if ticket.assignee:
            crm_ticket_url = f"{base_url}/#tickets"
            send_notification('employee_new_ticket', ticket.assignee.email, {
                'employee_name': ticket.assignee.first_name,
                'ticket_number': ticket.ticket_number,
                'ticket_title': ticket.title,
                'client_name': ticket.contact_name or '-',
                'client_email': ticket.contact_email or '-',
                'ticket_priority': ticket.priority or 'Normalny',
                'ticket_category': ticket.category or 'Ogólne',
                'ticket_description': ticket.description or '',
                'crm_ticket_url': crm_ticket_url,
            }, user=ticket.assignee)
    except Exception:
        pass


# ─────────────────────────────────────────────────────────────
# CRM AGENT ENDPOINTS (Wymagają JWT)
# ─────────────────────────────────────────────────────────────
