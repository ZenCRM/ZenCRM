from ..utils.i18n import t
import hashlib
import secrets
import re
from urllib.parse import urlsplit
from datetime import datetime, timedelta
import os
from pathlib import Path
from flask import Blueprint, request, jsonify, abort, current_app, send_from_directory, send_file
from flask_jwt_extended import verify_jwt_in_request
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markupsafe import escape
from ..extensions import db
from ..models.workspace import PortalSpace, PortalMember, PortalSession, PortalItem, PortalReply
from ..utils.deletion import current_user, is_admin
from ..models.workspace import PortalConfiguration, PortalClientSpace
from ..models.client import Client
from ..models.document import Document
from ..models.offer import Offer
from ..models.service import Service
from ..models.ticket import Ticket, TicketMessage
from ..services.pdf_service import html_to_pdf
from ..services.ticket_service import apply_auto_assignment as _apply_auto_assignment
from ..utils.portal import portal_settings, MODULES

portal_bp = Blueprint('portal', __name__)
from ..utils.auth_limits import auth_limit


def admin():
    verify_jwt_in_request()
    user = current_user()
    if not user or not user.is_active or not is_admin():
        abort(403)
    return user


def access(space_id):
    token = request.headers.get('X-Portal-Token')
    if not token:
        admin()
        return None
    if not portal_settings()['enabled']:
        abort(403, description='Portal jest wyłączony')
    session = db.session.get(PortalSession, hashlib.sha256(token.encode()).hexdigest())
    if not session or session.expires_at <= datetime.utcnow():
        abort(401)
    member = db.session.get(PortalMember, session.member_id)
    if not member or not member.active or member.space_id != space_id:
        abort(403)
    mapping = PortalClientSpace.query.filter_by(space_id=space_id).first()
    if mapping:
        client = db.session.get(Client, mapping.client_id)
        if not client or client.deleted_at:
            abort(403)
    return member


def module_access(member, kind):
    if member and kind not in portal_settings()['modules']:
        abort(403, description='Moduł portalu jest wyłączony')


def text(data, key, limit, required=False):
    value = data.get(key, '')
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        abort(400, description=t('Nieprawidłowe pole: {field}', {'field': key}))
    return value if key == 'password' else value.strip()


# Checked for unknown emails so response time does not reveal which members exist.
UNKNOWN_MEMBER_PASSWORD_HASH = generate_password_hash(secrets.token_urlsafe(32))


@portal_bp.route('/login', methods=['POST'])
@auth_limit(30)
def login():
    if not portal_settings()['enabled']:
        return jsonify(error='Portal jest wyłączony'), 403
    data = request.get_json() or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))
    candidates = PortalMember.query.filter_by(email=email, active=True).all()
    if not candidates:
        check_password_hash(UNKNOWN_MEMBER_PASSWORD_HASH, password)
    matches = [member for member in candidates if check_password_hash(member.password_hash, password)]
    if len(matches) != 1:
        return jsonify(error='Nieprawidłowe dane logowania'), 401
    member = matches[0]
    mapping = PortalClientSpace.query.filter_by(space_id=member.space_id).first()
    if mapping:
        client = db.session.get(Client, mapping.client_id)
        if not client or client.deleted_at:
            return jsonify(error='Dostęp do portalu został wyłączony'), 403
    token = secrets.token_urlsafe(40)
    db.session.add(PortalSession(token_hash=hashlib.sha256(token.encode()).hexdigest(), member_id=member.id, expires_at=datetime.utcnow() + timedelta(hours=8)))
    PortalSession.query.filter(PortalSession.expires_at < datetime.utcnow()).delete()
    db.session.commit()
    return jsonify(token=token, space_id=member.space_id)


@portal_bp.route('/logout', methods=['POST'])
def logout():
    token_hash = hashlib.sha256(request.headers.get('X-Portal-Token', '').encode()).hexdigest()
    PortalSession.query.filter_by(token_hash=token_hash).delete()
    db.session.commit()
    return jsonify(ok=True)


@portal_bp.route('/spaces', methods=['GET', 'POST'])
def spaces():
    admin()
    if request.method == 'POST':
        data = request.get_json() or {}
        client = None
        if data.get('client_id') not in (None, ''):
            client = db.get_or_404(Client, data.get('client_id'))
            if client.deleted_at:
                return jsonify(error='Klient jest zarchiwizowany'), 400
            if db.session.get(PortalClientSpace, client.id):
                return jsonify(error='Ten klient ma już portal'), 409
        space = PortalSpace(name=client.name if client else text(data, 'name', 160, True), description=text(data, 'description', 10000))
        db.session.add(space)
        db.session.flush()
        if client:
            db.session.add(PortalClientSpace(client_id=client.id, space_id=space.id))
        db.session.commit()
        return jsonify({**space.to_dict(), 'client_id': client.id if client else None}), 201
    links = {m.space_id: m.client_id for m in PortalClientSpace.query.all()}
    clients = {c.id: c for c in Client.query.filter(Client.id.in_(list(links.values()))).all()} if links else {}
    return jsonify([{**s.to_dict(), 'name': clients[links[s.id]].name if links.get(s.id) in clients else s.name,
                     'client_id': links.get(s.id)} for s in PortalSpace.query.order_by(PortalSpace.id.desc()).all()])


@portal_bp.route('/tickets', methods=['GET'])
def all_tickets():
    admin()
    spaces_by_id = {space.id: space for space in PortalSpace.query.all()}
    mappings = {row.space_id: row.client_id for row in PortalClientSpace.query.all()}
    clients = {client.id: client for client in Client.query.filter(Client.deleted_at.is_(None)).all()}
    reply_counts = dict(db.session.query(PortalReply.item_id, db.func.count(PortalReply.id)).group_by(PortalReply.item_id).all())
    result = []
    for item in PortalItem.query.filter_by(kind='ticket').order_by(PortalItem.id.desc()).all():
        space = spaces_by_id.get(item.space_id)
        client_id = mappings.get(item.space_id)
        client = clients.get(client_id)
        result.append({**item.to_dict(), 'space_id': item.space_id,
                       'space_name': client.name if client else (space.name if space else ''),
                       'client_id': client_id, 'client_name': client.name if client else '',
                       'reply_count': reply_counts.get(item.id, 0)})
    return jsonify(result)


def shared_with_client(record):
    """Drafts are internal; a missing status is treated as a draft."""
    return (record.status or 'draft').strip().lower() != 'draft'


def shared_with_client_filter(model):
    return db.func.lower(db.func.trim(db.func.coalesce(model.status, 'draft'))) != 'draft'


@portal_bp.route('/spaces/<int:space_id>', methods=['GET', 'PUT', 'DELETE'])
def space_detail(space_id):
    member = access(space_id)
    space = db.get_or_404(PortalSpace, space_id)
    mapping = PortalClientSpace.query.filter_by(space_id=space_id).first()
    client = db.session.get(Client, mapping.client_id) if mapping else None
    if request.method == 'DELETE':
        if member:
            abort(403)
        admin()
        for item in PortalItem.query.filter_by(space_id=space_id).all():
            PortalReply.query.filter_by(item_id=item.id).delete()
            if item.storage_name:
                (storage() / item.storage_name).unlink(missing_ok=True)
            db.session.delete(item)
        for m in PortalMember.query.filter_by(space_id=space_id).all():
            PortalSession.query.filter_by(member_id=m.id).delete()
            db.session.delete(m)
        PortalClientSpace.query.filter_by(space_id=space_id).delete()
        db.session.delete(space)
        db.session.commit()
        return jsonify(ok=True)
    if request.method == 'PUT':
        if member:
            abort(403)
        data = request.get_json() or {}
        if not client:
            space.name = text(data, 'name', 160, True)
        space.description = text(data, 'description', 10000)
        db.session.commit()
    result = space.to_dict()
    result['client_id'] = mapping.client_id if mapping else None
    if client:
        result['name'] = client.name
    items_list = [i.to_dict() for i in PortalItem.query.filter_by(space_id=space_id).order_by(PortalItem.id.desc()).all()]

    # Dołącz dokumenty, oferty i usługi powiązanego klienta
    if mapping and mapping.client_id:
        client_id = mapping.client_id
        # 1. Dokumenty klienta
        docs = Document.query.filter_by(client_id=client_id, deleted_at=None).filter(shared_with_client_filter(Document)).order_by(Document.id.desc()).all()
        for d in docs:
            items_list.append({
                'id': f'doc_{d.id}',
                'space_id': space_id,
                'kind': 'document',
                'title': d.title,
                'content': d.content or f'Typ dokumentu: {d.type} · Status: {d.status}',
                'status': d.status,
                'filename': f'{d.title}.pdf' if (d.pdf_path or d.rendered_html or d.template_id or d.content) else None,
                'created_at': d.created_at.isoformat() if d.created_at else None,
                'is_client_record': True,
            })
        # 2. Oferty klienta
        offers = Offer.query.filter_by(client_id=client_id, deleted_at=None).filter(shared_with_client_filter(Offer)).order_by(Offer.id.desc()).all()
        for o in offers:
            items_list.append({
                'id': f'offer_{o.id}',
                'space_id': space_id,
                'kind': 'offer',
                'title': f'{o.title} ({o.number})',
                'content': f'Wartość oferty: {float(o.total_amount or 0):.2f} PLN' + (f' · Ważna do: {o.valid_until}' if o.valid_until else '') + f' · Status: {o.status}',
                'status': o.status,
                'filename': f'{o.number}.pdf' if (o.pdf_path or o.rendered_html or o.template_id or o.content) else None,
                'created_at': o.created_at.isoformat() if o.created_at else None,
                'is_client_record': True,
            })
        # 3. Usługi klienta
        services = Service.query.filter_by(client_id=client_id, deleted_at=None).order_by(Service.id.desc()).all()
        for s in services:
            items_list.append({
                'id': f'srv_{s.id}',
                'space_id': space_id,
                'kind': 'service',
                'title': s.name,
                'content': f'Status usługi: {s.status} · Cykl rozliczeń: {s.billing_cycle} · Kwota: {float(s.price or 0):.2f} PLN' + (f'\n{s.description}' if s.description else ''),
                'status': s.status,
                'filename': None,
                'created_at': s.created_at.isoformat() if s.created_at else None,
                'is_client_record': True,
            })

    if member:
        allowed = portal_settings()['modules']
        items_list = [i for i in items_list if i['kind'] in allowed]

    result['items'] = items_list
    return jsonify(result)


@portal_bp.route('/spaces/<int:space_id>/members', methods=['GET', 'POST'])
def members(space_id):
    admin()
    db.get_or_404(PortalSpace, space_id)
    if request.method == 'POST':
        data = request.get_json() or {}
        email = text(data, 'email', 200, True).lower()
        password = text(data, 'password', 200, True)
        if '@' not in email or len(password) < 10:
            return jsonify(error='Podaj email i hasło min. 10 znaków'), 400
        if PortalMember.query.filter_by(email=email).first():
            return jsonify(error='Konto z tym adresem email już istnieje'), 409
        member = PortalMember(space_id=space_id, email=email, password_hash=generate_password_hash(password))
        db.session.add(member)
        db.session.commit()
        try:
            from ..services.email_service import send_notification, staff_link_base_url
            from ..utils.portal import portal_path
            portal_url = f"{staff_link_base_url()}{portal_path()}"
            client_name = email.split('@')[0]
            send_notification('client_portal_access', email, {
                'client_name': client_name,
                'portal_url': portal_url,
                'login_email': email,
                'password': password,
            }, recipient_name=client_name)
        except Exception:
            pass
        return jsonify(member.to_dict()), 201
    return jsonify([m.to_dict() for m in PortalMember.query.filter_by(space_id=space_id).all()])


@portal_bp.route('/spaces/<int:space_id>/members/<int:member_id>', methods=['PUT'])
def change_member(space_id, member_id):
    admin()
    member = PortalMember.query.filter_by(id=member_id, space_id=space_id).first_or_404()
    data = request.get_json() or {}
    if 'active' in data:
        if not isinstance(data['active'], bool):
            abort(400)
        member.active = data['active']
    if data.get('password'):
        password = text(data, 'password', 200, True)
        if len(password) < 10:
            abort(400)
        member.password_hash = generate_password_hash(password)
    PortalSession.query.filter_by(member_id=member_id).delete()
    db.session.commit()
    return jsonify(member.to_dict())


@portal_bp.route('/spaces/<int:space_id>/items', methods=['POST'])
def create_item(space_id):
    member = access(space_id)
    db.get_or_404(PortalSpace, space_id)
    data = request.get_json() or {}
    kind = data.get('kind')
    module_access(member, kind)
    if kind not in ('ticket', 'info') or (member and kind != 'ticket'):
        abort(403)
    item = PortalItem(space_id=space_id, kind=kind, title=text(data, 'title', 200, True), content=text(data, 'content', 50000))
    db.session.add(item)

    if kind == 'ticket':
        mapping = PortalClientSpace.query.filter_by(space_id=space_id).first()
        client_id = mapping.client_id if mapping else None
        client = db.session.get(Client, client_id) if client_id else None
        contact_email = member.email if member else (client.email if client else 'portal@klient')
        contact_name = client.name if client else contact_email.split('@')[0]
        tck = Ticket(
            ticket_number=Ticket.generate_number(),
            title=item.title,
            description=item.content,
            client_id=client_id,
            contact_name=contact_name,
            contact_email=contact_email,
            contact_phone=client.phone if client else None,
            category='general',
            priority='medium',
            status='new',
            token=Ticket.generate_token(),
            source='portal'
        )
        _apply_auto_assignment(tck, client)
        msg = TicketMessage(
            sender_type='client',
            sender_name=contact_name,
            sender_email=contact_email,
            content=item.content,
            is_internal=False
        )
        tck.messages.append(msg)
        db.session.add(tck)

    db.session.commit()
    return jsonify(item.to_dict()), 201


@portal_bp.route('/spaces/<int:space_id>/items/<int:item_id>', methods=['PUT', 'DELETE'])
def update_item(space_id, item_id):
    admin()
    item = PortalItem.query.filter_by(id=item_id, space_id=space_id).first_or_404()
    if request.method == 'DELETE':
        PortalReply.query.filter_by(item_id=item_id).delete()
        if item.storage_name:
            (storage() / item.storage_name).unlink(missing_ok=True)
        db.session.delete(item)
    else:
        data = request.get_json() or {}
        for key, limit in [('title', 200), ('content', 50000)]:
            if key in data:
                setattr(item, key, text(data, key, limit, key == 'title'))
        if 'status' in data:
            if data['status'] not in ('open', 'in_progress', 'closed'):
                abort(400)
            item.status = data['status']
    db.session.commit()
    return jsonify(ok=True)


@portal_bp.route('/spaces/<int:space_id>/items/<int:item_id>/replies', methods=['GET', 'POST'])
def replies(space_id, item_id):
    member = access(space_id)
    module_access(member, 'ticket')
    item = PortalItem.query.filter_by(id=item_id, space_id=space_id, kind='ticket').first_or_404()
    if request.method == 'POST':
        if item.status == 'closed':
            return jsonify(error='Ticket jest zamknięty'), 400
        data = request.get_json() or {}
        reply = PortalReply(item_id=item.id, author=member.email if member else 'Obsługa', content=text(data, 'content', 10000, True))
        db.session.add(reply)
        db.session.commit()
    return jsonify([r.to_dict() for r in PortalReply.query.filter_by(item_id=item_id).order_by(PortalReply.id).all()])


def storage():
    directory = Path(current_app.instance_path) / 'portal_files'
    directory.mkdir(parents=True, exist_ok=True)
    return directory


@portal_bp.route('/spaces/<int:space_id>/items/<string:item_id>/file', methods=['GET', 'POST'])
def attachment(space_id, item_id):
    member = access(space_id)
    mapping = PortalClientSpace.query.filter_by(space_id=space_id).first()
    client_id = mapping.client_id if mapping else None

    # 1. Obsługa dokumentu klienta
    if item_id.startswith('doc_'):
        if client_id is None:
            abort(404)
        try:
            doc_id = int(item_id.split('_')[1])
        except (ValueError, IndexError):
            abort(404)
        doc = db.session.get(Document, doc_id)
        if not doc or doc.deleted_at or doc.client_id != client_id or not shared_with_client(doc):
            abort(404)
        module_access(member, 'document')
        if doc.pdf_path and os.path.exists(doc.pdf_path):
            return send_file(doc.pdf_path, as_attachment=True, download_name=f'{doc.title}.pdf')
        if doc.rendered_html or doc.content:
            pdf_dir = Path(current_app.instance_path) / 'generated_docs'
            pdf_dir.mkdir(parents=True, exist_ok=True)
            pdf_tmp = str(pdf_dir / f'doc_{doc.id}.pdf')
            html_to_pdf(doc.rendered_html or f'<pre>{escape(doc.content)}</pre>', pdf_tmp)
            if os.path.exists(pdf_tmp):
                return send_file(pdf_tmp, as_attachment=True, download_name=f'{doc.title}.pdf')
        abort(404)

    # 2. Obsługa oferty klienta
    if item_id.startswith('offer_'):
        if client_id is None:
            abort(404)
        try:
            off_id = int(item_id.split('_')[1])
        except (ValueError, IndexError):
            abort(404)
        off = db.session.get(Offer, off_id)
        if not off or off.deleted_at or off.client_id != client_id or not shared_with_client(off):
            abort(404)
        module_access(member, 'offer')
        if off.pdf_path and os.path.exists(off.pdf_path):
            return send_file(off.pdf_path, as_attachment=True, download_name=f'{off.number}.pdf')
        if off.rendered_html or off.content:
            pdf_dir = Path(current_app.instance_path) / 'generated_offers'
            pdf_dir.mkdir(parents=True, exist_ok=True)
            pdf_tmp = str(pdf_dir / f'offer_{off.id}.pdf')
            html_to_pdf(off.rendered_html or f'<pre>{escape(off.content)}</pre>', pdf_tmp)
            if os.path.exists(pdf_tmp):
                return send_file(pdf_tmp, as_attachment=True, download_name=f'{off.number}.pdf')
        abort(404)

    # 3. Standardowy PortalItem
    try:
        real_id = int(item_id)
    except ValueError:
        abort(404)
    item = PortalItem.query.filter_by(id=real_id, space_id=space_id).first_or_404()
    module_access(member, item.kind)
    if request.method == 'GET':
        if not item.storage_name:
            abort(404)
        return send_from_directory(storage(), item.storage_name, as_attachment=True, download_name=item.filename)
    if member:
        abort(403)
    request.max_content_length = 21 * 1024 * 1024
    upload = request.files.get('file')
    if not upload or not upload.filename:
        abort(400)
    content = upload.stream.read(20 * 1024 * 1024 + 1)
    if len(content) > 20 * 1024 * 1024:
        return jsonify(error='Plik może mieć maksymalnie 20 MB'), 413
    name = secrets.token_hex(24)
    (storage() / name).write_bytes(content)
    if item.storage_name:
        (storage() / item.storage_name).unlink(missing_ok=True)
    item.storage_name = name
    item.filename = secure_filename(upload.filename) or 'dokument'
    db.session.commit()
    return jsonify(item.to_dict())


@portal_bp.route('/configuration', methods=['GET', 'PUT'])
def configuration():
    if request.method == 'GET':
        response = jsonify(portal_settings())
        response.headers['Cache-Control'] = 'no-store'
        return response
    admin()
    data = request.get_json() or {}
    config = portal_settings()
    address = text(data, 'address', 500, True)
    try:
        parsed = urlsplit(address)
    except ValueError:
        return jsonify(error='Nieprawidłowy adres portalu'), 400
    if (parsed.scheme not in ('', 'http', 'https') or parsed.query or parsed.fragment
            or parsed.username or parsed.password or (parsed.scheme and not parsed.netloc)
            or (not parsed.scheme and parsed.netloc)
            or not re.fullmatch(r'/[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*/?|/portal\.html', parsed.path)
            or parsed.path.split('/')[1] in ('api', 'js', 'css', 'views', 'locales', 'vendor')):
        return jsonify(error='Podaj adres HTTP(S) ze ścieżką portalu, np. /portal lub https://firma.pl/portal'), 400
    if not isinstance(data.get('enabled'), bool) or not isinstance(data.get('modules'), list) or any(m not in MODULES for m in data['modules']):
        return jsonify(error='Nieprawidłowe ustawienia modułów'), 400
    for key in ('logo', 'login_background'):
        value = text(data, key, 1000)
        try:
            url = urlsplit(value)
        except ValueError:
            return jsonify(error='Nieprawidłowy adres obrazu'), 400
        if value and not ((url.scheme in ('http', 'https') and url.netloc and not url.username and not url.password) or (value.startswith('/') and not value.startswith('//') and not url.scheme and not url.netloc)):
            return jsonify(error='Nieprawidłowy adres obrazu'), 400
        config[key] = value
    config.update(address=address.rstrip('/'), enabled=data['enabled'], modules=list(dict.fromkeys(data['modules'])))
    row = db.session.get(PortalConfiguration, 1)
    if row is None:
        row = PortalConfiguration(id=1)
        db.session.add(row)
    row.data = config
    if not config['enabled']:
        PortalSession.query.delete()
    db.session.commit()
    return jsonify(config)


@portal_bp.route('/branding', methods=['POST'])
def upload_branding():
    admin()
    request.max_content_length = 6 * 1024 * 1024
    file = request.files.get('file')
    if not file:
        abort(400)
    content = file.stream.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024:
        return jsonify(error='Obraz może mieć maksymalnie 5 MB'), 413
    ext = ('png' if content.startswith(b'\x89PNG\r\n\x1a\n') else
           'jpg' if content.startswith(b'\xff\xd8\xff') else
           'gif' if content.startswith((b'GIF87a', b'GIF89a')) else
           'webp' if content.startswith(b'RIFF') and content[8:12] == b'WEBP' else None)
    if not ext:
        return jsonify(error='Dozwolone obrazy: PNG, JPG, GIF, WEBP'), 400
    directory = Path(current_app.instance_path) / 'portal_branding'
    directory.mkdir(parents=True, exist_ok=True)
    filename = secrets.token_hex(20) + '.' + ext
    (directory / filename).write_bytes(content)
    return jsonify(url='/api/portal/branding/' + filename)


@portal_bp.route('/branding/<filename>')
def branding(filename):
    return send_from_directory(Path(current_app.instance_path) / 'portal_branding', filename)


def client_space(client_id):
    try:
        client_id = int(client_id)
    except (ValueError, TypeError):
        abort(400, description='Wybierz klienta')
    client = db.get_or_404(Client, client_id)
    if client.deleted_at:
        abort(400, description='Klient jest zarchiwizowany')
    mapping = db.session.get(PortalClientSpace, client_id)
    if not mapping:
        space = PortalSpace(name=client.name, description='')
        db.session.add(space)
        db.session.flush()
        mapping = PortalClientSpace(client_id=client_id, space_id=space.id)
        db.session.add(mapping)
        db.session.flush()
    return mapping


def member_data(member):
    mapping = PortalClientSpace.query.filter_by(space_id=member.space_id).first()
    client = db.session.get(Client, mapping.client_id) if mapping else None
    return {**member.to_dict(), 'space_id': member.space_id,
            'client_id': mapping.client_id if mapping else None,
            'client_name': client.name if client else ''}


@portal_bp.route('/members', methods=['GET', 'POST'])
def portal_members():
    admin()
    if request.method == 'GET':
        return jsonify([member_data(m) for m in PortalMember.query.order_by(PortalMember.email).all()])
    data = request.get_json() or {}
    return save_portal_member(data)


@portal_bp.route('/members/<int:member_id>', methods=['PUT', 'DELETE'])
def portal_member(member_id):
    admin()
    member = db.get_or_404(PortalMember, member_id)
    if request.method == 'DELETE':
        PortalSession.query.filter_by(member_id=member.id).delete()
        db.session.delete(member)
        db.session.commit()
        return jsonify(ok=True)
    return save_portal_member(request.get_json() or {}, member)


def save_portal_member(data, member=None):
    email = text(data, 'email', 200, True).lower()
    password = text(data, 'password', 200)
    if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', email) or (not member and len(password) < 10) or (password and len(password) < 10) or not isinstance(data.get('active', True), bool):
        return jsonify(error='Podaj poprawny email i hasło min. 10 znaków'), 400
    mapping = client_space(data.get('client_id'))
    duplicate = PortalMember.query.filter_by(email=email).first()
    if duplicate and (not member or duplicate.id != member.id):
        db.session.rollback()
        return jsonify(error='Konto z tym adresem email już istnieje'), 409
    is_new = (member is None)
    if member is None:
        member = PortalMember()
        db.session.add(member)
    else:
        PortalSession.query.filter_by(member_id=member.id).delete()
    member.space_id = mapping.space_id
    member.email = email
    member.active = data.get('active', True)
    if password:
        member.password_hash = generate_password_hash(password)
    db.session.commit()

    if is_new and password:
        try:
            from ..services.email_service import send_notification, staff_link_base_url
            from ..utils.portal import portal_path
            portal_url = f"{staff_link_base_url()}{portal_path()}"
            client_name = email.split('@')[0]
            send_notification('client_portal_access', email, {
                'client_name': client_name,
                'portal_url': portal_url,
                'login_email': email,
                'password': password,
            }, recipient_name=client_name)
        except Exception:
            pass

    return jsonify(member_data(member))


@portal_bp.route('/spaces/<int:space_id>/client', methods=['PUT'])
def assign_space_client(space_id):
    admin()
    db.get_or_404(PortalSpace, space_id)
    data = request.get_json() or {}
    client = db.get_or_404(Client, data.get('client_id'))
    if client.deleted_at:
        abort(400)
    if db.session.get(PortalClientSpace, client.id) or PortalClientSpace.query.filter_by(space_id=space_id).first():
        return jsonify(error='Klient lub przestrzeń jest już przypisany'), 409
    db.session.add(PortalClientSpace(client_id=client.id, space_id=space_id))
    db.session.commit()
    return jsonify(ok=True)
