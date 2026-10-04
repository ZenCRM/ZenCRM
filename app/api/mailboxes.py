from flask import Blueprint, abort, jsonify, request, send_file
from io import BytesIO
import re
import json
from sqlalchemy import or_, func, cast, Text
from ..extensions import db
from ..models.mailbox import Mailbox, MailMessage
from ..models.team import Team
from ..models.client import Client
from ..models.contact import Contact
from ..utils.deletion import current_user
from ..services.mailbox_service import encrypt_password, addresses, test_connection, sync_inbox, send_message, download_attachment, set_read_status
from ..utils.mail_html import sanitize_signature_html
from ..utils.auth_limits import auth_limit
from ..utils.mail_limits import mail_operation
from ..services.mailbox_lock import MailboxBusy

mailboxes_bp = Blueprint('mailboxes', __name__)


@mailboxes_bp.errorhandler(MailboxBusy)
def sync_busy(error):
    return jsonify(error='Synchronizacja tej skrzynki już trwa. Spróbuj ponownie później.'), 409


def visible_boxes():
    user = current_user()
    # Personal inboxes stay private, including from other administrators.
    teams = [t.id for t in user.teams]
    return Mailbox.query.filter(or_(Mailbox.user_id == user.id, Mailbox.team_id.in_(teams)))


def accessible(box_id, manage=False):
    box = visible_boxes().filter_by(id=box_id).first_or_404()
    if manage and box.team_id:
        team = db.session.get(Team, box.team_id)
        user = current_user()
        if user.role != 'admin' and team.leader_id != user.id:
            abort(403)
    return box


def payload():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValueError('Nieprawidłowe dane')
    return data


@mailboxes_bp.errorhandler(ValueError)
def invalid(error):
    db.session.rollback()
    return jsonify(error=str(error)), 400


def transport_error():
    db.session.rollback()
    return jsonify(error='Nie udało się połączyć z serwerem poczty. Sprawdź hosty, porty i hasło do poczty.'), 502


@mailboxes_bp.route('', methods=['GET'])
def list_boxes():
    return jsonify([b.to_dict() for b in visible_boxes().order_by(Mailbox.name).all()])


@mailboxes_bp.route('/unread', methods=['GET'])
def unread_count():
    total = MailMessage.query.filter(
        MailMessage.mailbox_id.in_(visible_boxes().with_entities(Mailbox.id)),
        MailMessage.folder == 'inbox', MailMessage.is_read.is_(False)).count()
    return jsonify(total=total)


@mailboxes_bp.route('', methods=['POST'])
@auth_limit(12, seconds=60, by_user=True, scope='mail-transport')
@mail_operation
def connect_box():
    data = payload()
    user = current_user()
    team_id = data.get('team_id') or None
    if team_id:
        try:
            team_id = int(team_id)
        except (ValueError, TypeError):
            raise ValueError('Wybierz istniejący zespół')
        team = db.session.get(Team, team_id)
        if not team or user.id not in [m.id for m in team.members] or (user.role != 'admin' and team.leader_id != user.id):
            abort(403)
    email = addresses(data.get('email', ''))
    if len(email) != 1:
        raise ValueError('Podaj jeden adres skrzynki')
    values = {}
    for key in ('name', 'username', 'imap_host', 'smtp_host'):
        value = str(data.get(key, '')).strip()
        if not value or len(value) > (120 if key == 'name' else 254) or any(c in value for c in '\r\n/\\'):
            raise ValueError('Uzupełnij nazwę, login i hosty serwerów')
        values[key] = value
    for key, default in (('imap_port', 993), ('smtp_port', 587)):
        try:
            values[key] = int(data.get(key, default))
        except (TypeError, ValueError):
            raise ValueError('Nieprawidłowy port')
        if not 1 <= values[key] <= 65535:
            raise ValueError('Nieprawidłowy port')
    security = data.get('smtp_security', 'starttls')
    if security not in ('ssl', 'starttls'):
        raise ValueError('Wybierz SSL lub STARTTLS')
    secret = data.get('password')
    if not isinstance(secret, str) or not secret or len(secret) > 4096:
        raise ValueError('Podaj hasło do poczty')
    box = Mailbox(**values, email=email[0], team_id=team_id, user_id=None if team_id else user.id,
                  password_encrypted=encrypt_password(secret), smtp_security=security, signature='')
    try:
        test_connection(box)
    except Exception:
        return transport_error()
    db.session.add(box)
    db.session.commit()
    return jsonify(box.to_dict()), 201


@mailboxes_bp.route('/<int:box_id>', methods=['PUT'])
@auth_limit(12, seconds=60, by_user=True, scope='mail-transport')
@mail_operation
def update_box(box_id):
    box = accessible(box_id, manage=True)
    data = payload()
    if any(key in data and str(data[key]).strip().lower() != getattr(box, key).lower()
           for key in ('imap_host', 'smtp_host')) and not data.get('password'):
        raise ValueError('Przy zmianie serwera wpisz ponownie hasło do poczty')
    if 'sync_interval_minutes' in data:
        interval = data['sync_interval_minutes']
        if type(interval) is not int or interval not in (5, 10, 15, 30, 60):
            raise ValueError('Wybierz częstotliwość: 5, 10, 15, 30 lub 60 minut')
        box.sync_interval_minutes = interval
        from datetime import datetime, timedelta
        box.next_sync_at = datetime.utcnow() + timedelta(minutes=interval)
    signature_format = data.get('signature_format', box.signature_format)
    connection_changed = False
    for key in ('name', 'username', 'imap_host', 'smtp_host'):
        if key not in data:
            continue
        value = str(data[key]).strip()
        if not value or len(value) > (120 if key == 'name' else 254) or any(c in value for c in '\r\n/\\'):
            raise ValueError('Uzupełnij nazwę, login i hosty serwerów')
        connection_changed |= key != 'name' and value != getattr(box, key)
        setattr(box, key, value)
    for key in ('imap_port', 'smtp_port'):
        if key not in data:
            continue
        try:
            port = int(data[key])
        except (ValueError, TypeError):
            raise ValueError('Nieprawidłowy port')
        if not 1 <= port <= 65535:
            raise ValueError('Nieprawidłowy port')
        connection_changed |= port != getattr(box, key)
        setattr(box, key, port)
    if 'smtp_security' in data:
        if data['smtp_security'] not in ('ssl', 'starttls'):
            raise ValueError('Wybierz SSL lub STARTTLS')
        connection_changed |= data['smtp_security'] != box.smtp_security
        box.smtp_security = data['smtp_security']
    if signature_format not in ('text', 'html'):
        raise ValueError('Wybierz format stopki: tekst lub HTML')
    if 'signature' in data:
        if not isinstance(data['signature'], str) or len(data['signature']) > 100000:
            raise ValueError('Stopka może mieć do 100 000 znaków')
        box.signature = sanitize_signature_html(data['signature']) if signature_format == 'html' else data['signature']
    box.signature_format = signature_format
    if signature_format == 'html':
        box.signature = sanitize_signature_html(box.signature)
    if data.get('password'):
        if not isinstance(data['password'], str) or len(data['password']) > 4096:
            raise ValueError('Nieprawidłowe hasło')
        box.password_encrypted = encrypt_password(data['password'])
        connection_changed = True
    if connection_changed:
        try:
            test_connection(box)
        except Exception:
            return transport_error()
    db.session.commit()
    return jsonify(box.to_dict())


@mailboxes_bp.route('/<int:box_id>', methods=['DELETE'])
def disconnect_box(box_id):
    db.session.delete(accessible(box_id, manage=True))
    db.session.commit()
    return '', 204


def links(message):
    emails = [message.sender] if message.folder == 'inbox' else (message.recipients or []) + (message.cc or []) + (message.bcc or [])
    emails = [a.strip().lower() for a in emails]
    clients = Client.query.filter(Client.deleted_at.is_(None), func.lower(func.trim(Client.email)).in_(emails)).all()
    contacts = Contact.query.filter(Contact.deleted_at.is_(None), func.lower(func.trim(Contact.email)).in_(emails)).all()
    client_ids = {c.id for c in clients}
    for c in contacts:
        client = db.session.get(Client, c.client_id) if c.client_id else None
        if client and not client.deleted_at and client.id not in client_ids:
            clients.append(client)
            client_ids.add(client.id)
    return {'clients': [{'id': c.id, 'name': c.name} for c in clients],
            'contacts': [{'id': c.id, 'name': (c.first_name + ' ' + (c.last_name or '')).strip()} for c in contacts]}


@mailboxes_bp.route('/clients/<int:client_id>/messages', methods=['GET'])
def client_messages(client_id):
    client = Client.query.filter_by(id=client_id, deleted_at=None).first_or_404()
    contacts = Contact.query.filter_by(client_id=client_id, deleted_at=None).all()
    emails = sorted({value.strip().lower() for value in [client.email] + [c.email for c in contacts] if value and value.strip()})
    matches = []
    for email in emails:
        outgoing = or_(*[func.lower(cast(getattr(MailMessage, field), Text)).contains(json.dumps(email), autoescape=True) for field in ('recipients', 'cc', 'bcc')])
        matches.append(or_((MailMessage.folder == 'inbox') & (func.lower(func.trim(MailMessage.sender)) == email), (MailMessage.folder == 'sent') & outgoing))
    query = MailMessage.query.filter(MailMessage.mailbox_id.in_(visible_boxes().with_entities(Mailbox.id)), or_(*matches) if matches else False)
    page = max(1, request.args.get('page', 1, type=int) or 1)
    result = query.order_by(MailMessage.created_at.desc(), MailMessage.id.desc()).paginate(page=page, per_page=30, error_out=False)
    boxes = {b.id: b for b in visible_boxes().all()}
    return jsonify(items=[{**m.to_dict(), 'body': m.body[:200], 'body_html': '', 'mailbox_name': boxes[m.mailbox_id].name} for m in result.items], total=result.total, pages=result.pages, emails=emails)


@mailboxes_bp.route('/<int:box_id>/messages', methods=['GET'])
def list_messages(box_id):
    accessible(box_id)
    query = MailMessage.query.filter_by(mailbox_id=box_id)
    folder = request.args.get('folder', 'inbox')
    if folder not in ('inbox', 'sent'):
        raise ValueError('Nieprawidłowy folder')
    query = query.filter_by(folder=folder)
    unread = MailMessage.query.filter_by(mailbox_id=box_id, folder='inbox', is_read=False).count()
    read_filter = request.args.get('status', '')
    if read_filter in ('read', 'unread'):
        query = query.filter_by(is_read=read_filter == 'read')
    term = request.args.get('q', '').strip()[:200]
    if term:
        query = query.filter(or_(MailMessage.subject.contains(term, autoescape=True), MailMessage.sender.contains(term, autoescape=True), MailMessage.body.contains(term, autoescape=True)))
    page = max(1, request.args.get('page', 1, type=int) or 1)
    result = query.order_by(MailMessage.created_at.desc(), MailMessage.id.desc()).paginate(page=page, per_page=30, error_out=False)
    return jsonify(items=[{**m.to_dict(), 'body': m.body[:160], 'body_html': '', 'links': links(m)} for m in result.items], total=result.total, pages=result.pages, unread=unread)


@mailboxes_bp.route('/<int:box_id>/messages/<int:message_id>', methods=['GET'])
def get_message(box_id, message_id):
    box = accessible(box_id)
    msg = MailMessage.query.filter_by(id=message_id, mailbox_id=box_id).first_or_404()
    # Read marking is a separate action so transport failures never hide the message.
    return jsonify({**msg.to_dict(), 'links': links(msg)})


@mailboxes_bp.route('/<int:box_id>/sync', methods=['POST'])
@auth_limit(12, seconds=60, by_user=True, scope='mail-transport')
@mail_operation
def sync(box_id):
    box = accessible(box_id)
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        raise ValueError('Nieprawidłowe ustawienia synchronizacji')
    all_messages = data.get('all_messages', False)
    if not isinstance(all_messages, bool):
        raise ValueError('Nieprawidłowy zakres synchronizacji')
    before_uid = data.get('before_uid')
    if before_uid is not None and (not isinstance(before_uid, int) or before_uid <= 0):
        raise ValueError('Nieprawidłowy punkt synchronizacji')
    try:
        result = sync_inbox(box, all_messages=all_messages, before_uid=before_uid)
        return jsonify(**result, mailbox=box.to_dict())
    except MailboxBusy:
        raise
    except ValueError:
        db.session.rollback()
        raise
    except Exception:
        return transport_error()


@mailboxes_bp.route('/<int:box_id>/messages/<int:message_id>/read', methods=['PUT'])
@auth_limit(60, seconds=60, by_user=True, scope='mail-read-status')
@mail_operation
def mark_read(box_id, message_id):
    box = accessible(box_id)
    msg = MailMessage.query.filter_by(id=message_id, mailbox_id=box_id).first_or_404()
    data = payload()
    if not isinstance(data.get('is_read'), bool):
        raise ValueError('Podaj status odczytania')
    try:
        set_read_status(box, msg, data['is_read'])
        return jsonify(id=msg.id, is_read=msg.is_read)
    except ValueError:
        raise
    except Exception:
        return transport_error()


@mailboxes_bp.route('/<int:box_id>/messages/<int:message_id>/attachments/<part_id>', methods=['GET'])
@auth_limit(12, seconds=60, by_user=True, scope='mail-transport')
@mail_operation
def get_attachment(box_id, message_id, part_id):
    box = accessible(box_id)
    msg = MailMessage.query.filter_by(id=message_id, mailbox_id=box_id).first_or_404()
    try:
        raw, filename = download_attachment(box, msg, part_id)
    except ValueError:
        raise
    except Exception:
        return transport_error()
    filename = re.sub(r'[\\/\x00-\x1f\x7f]', '_', filename).strip('.') or 'załącznik'
    return send_file(BytesIO(raw), mimetype='application/octet-stream', as_attachment=True, download_name=filename)


@mailboxes_bp.route('/<int:box_id>/send', methods=['POST'])
@auth_limit(12, seconds=60, by_user=True, scope='mail-transport')
@mail_operation
def send(box_id):
    box = accessible(box_id)
    data = payload()
    try:
        message, refused = send_message(box, data)
        return jsonify(message=message.to_dict(), refused=refused), 201
    except ValueError:
        raise
    except Exception:
        return transport_error()
