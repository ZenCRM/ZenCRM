from ..utils.i18n import t
import json
import re
import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..extensions import db
from ..models.sms import SmsDevice, SmsQueue, PhoneCall, SmsMessage
from ..models.client import Client
from ..models.contact import Contact
from ..models.lead import Lead
from ..models.user import User
from ..models.activity import Activity


sms_bp = Blueprint('sms', __name__)


def normalize_phone_variants(phone):
    """
    Returns a set of normalized variants for a phone number:
    - cleaned digits (e.g. 48500600700)
    - 9-digit local version without 48 / 0048 / leading 0 (e.g. 500600700)
    - with 48 prefix
    - last 9 digits
    Handles variations with and without +48, 48, 0048, spaces, dashes.
    """
    if not phone:
        return set()
    raw = str(phone).strip()
    digits = re.sub(r'\D', '', raw)
    if not digits:
        return set()
    variants = {digits}
    if digits.startswith('0048') and len(digits) > 4:
        variants.add(digits[4:])
        variants.add('48' + digits[4:])
    elif digits.startswith('48') and len(digits) > 2:
        variants.add(digits[2:])
    elif len(digits) == 9:
        variants.add('48' + digits)
    if digits.startswith('0') and len(digits) == 10:
        variants.add(digits[1:])
        variants.add('48' + digits[1:])
    if len(digits) >= 9:
        variants.add(digits[-9:])
    return {v for v in variants if len(v) >= 6}


def phones_match(p1, p2):
    """Checks if two phone numbers match under any normalization variant."""
    if not p1 or not p2:
        return False
    v1 = normalize_phone_variants(p1)
    v2 = normalize_phone_variants(p2)
    return bool(v1 & v2)


def normalize_phone(phone):
    """Normalize phone number to digits only (last 9 digits for comparison)."""
    if not phone:
        return ''
    digits = re.sub(r'\D', '', str(phone))
    return digits[-9:] if len(digits) >= 9 else digits


def find_entities_by_phone(phone):
    """
    Find all Clients, Contacts, and Leads matching this phone number.
    Handles the case where one phone number is present in multiple places.
    Matches with and without 48, +48, 0048, spaces, etc.
    """
    target_variants = normalize_phone_variants(phone)
    if not target_variants:
        return {'clients': [], 'leads': [], 'contacts': []}

    matched_clients = []
    seen_client_ids = set()

    matched_contacts = []
    seen_contact_ids = set()

    matched_leads = []
    seen_lead_ids = set()

    # 1. Match directly against Clients
    clients = Client.query.filter(Client.deleted_at == None).all()
    for c in clients:
        if c.phone and (normalize_phone_variants(c.phone) & target_variants):
            if c.id not in seen_client_ids:
                seen_client_ids.add(c.id)
                matched_clients.append({
                    'id': c.id,
                    'name': c.name,
                    'company': c.company,
                    'phone': c.phone,
                    'type': 'client'
                })

    # 2. Match against Contacts (which can link to Client and/or Lead)
    contacts = Contact.query.filter(Contact.deleted_at == None).all()
    for ct in contacts:
        if ct.phone and (normalize_phone_variants(ct.phone) & target_variants):
            if ct.id not in seen_contact_ids:
                seen_contact_ids.add(ct.id)
                parent_c = db.session.get(Client, ct.client_id) if ct.client_id else None
                matched_contacts.append({
                    'id': ct.id,
                    'name': f"{ct.first_name} {ct.last_name}".strip(),
                    'first_name': ct.first_name,
                    'last_name': ct.last_name,
                    'phone': ct.phone,
                    'position': ct.position,
                    'client_id': ct.client_id,
                    'client_name': parent_c.name if (parent_c and not parent_c.deleted_at) else None,
                    'lead_id': ct.lead_id,
                    'type': 'contact'
                })

            # Add parent Client if not already added
            if ct.client_id and ct.client_id not in seen_client_ids:
                parent_c = db.session.get(Client, ct.client_id)
                if parent_c and not parent_c.deleted_at:
                    seen_client_ids.add(parent_c.id)
                    matched_clients.append({
                        'id': parent_c.id,
                        'name': parent_c.name,
                        'company': parent_c.company,
                        'phone': parent_c.phone,
                        'type': 'client'
                    })

            # Add parent Lead if not already added
            if ct.lead_id and ct.lead_id not in seen_lead_ids:
                parent_l = db.session.get(Lead, ct.lead_id)
                if parent_l and not parent_l.deleted_at:
                    seen_lead_ids.add(parent_l.id)
                    matched_leads.append({
                        'id': parent_l.id,
                        'title': parent_l.title,
                        'stage': parent_l.stage,
                        'type': 'lead'
                    })

    return {
        'clients': matched_clients,
        'leads': matched_leads,
        'contacts': matched_contacts
    }


def find_client_by_phone(phone):
    """Find primary matching client ID."""
    ents = find_entities_by_phone(phone)
    if ents['clients']:
        return ents['clients'][0]['id']
    return None


def create_telephony_activity(item_type, entity_type, entity_id, phone, direction, title_or_contact, duration_sec=0, body='', item_time=None, user_id=None, caller_name=None):
    """
    Creates an Activity record in the CRM associated with a client or lead,
    with created_at set to the actual call/message date (wg. daty).
    Avoids duplicate entries.
    """
    if not entity_id or not entity_type or not item_time:
        return None

    act_action = 'call' if item_type == 'call' else 'sms'
    time_min = item_time - timedelta(seconds=5)
    time_max = item_time + timedelta(seconds=5)

    existing = Activity.query.filter(
        Activity.entity_type == entity_type,
        Activity.entity_id == entity_id,
        Activity.action == act_action,
        Activity.created_at >= time_min,
        Activity.created_at <= time_max
    ).first()

    if existing:
        return existing

    if item_type == 'call':
        dir_label = {
            'incoming': 'Połączenie przychodzące',
            'outgoing': 'Połączenie wychodzące',
            'missed': 'Nieodebrane połączenie',
            'rejected': 'Odrzucone połączenie'
        }.get(direction, 'Połączenie telefoniczne')
        contact_str = f": {title_or_contact}" if title_or_contact else f": {phone}"
        dur_str = f" ({duration_sec}s)" if duration_sec else ""
        caller_str = f" [zlecone przez: {caller_name}]" if caller_name else ""
        desc = f"{dir_label}{contact_str}{dur_str}{caller_str}"
    else:
        dir_label = 'Odebrano SMS' if direction == 'received' else 'Wysłano SMS'
        contact_str = f" od: {title_or_contact}" if direction == 'received' else f" do: {title_or_contact}"
        snippet = f' - "{body[:75]}..."' if len(body) > 75 else (f' - "{body}"' if body else "")
        desc = f"{dir_label}{contact_str}{snippet}"

    act = Activity(
        action=act_action,
        description=desc,
        entity_type=entity_type,
        entity_id=entity_id,
        user_id=user_id,
        created_at=item_time,
        meta={'phone': phone, 'direction': direction, 'caller_name': caller_name}
    )
    db.session.add(act)
    return act


def backfill_telephony_activities():
    """Ensure existing PhoneCalls and SmsMessages are reflected in Activities by date."""
    try:
        calls = PhoneCall.query.filter(PhoneCall.call_time != None).all()
        for c in calls:
            ents = find_entities_by_phone(c.number)
            c_name = ents['contacts'][0]['name'] if ents['contacts'] else None
            for cl in ents['clients']:
                create_telephony_activity('call', 'client', cl['id'], c.number, c.type, c_name or cl['name'], c.duration_sec, item_time=c.call_time)
            for ld in ents['leads']:
                create_telephony_activity('call', 'lead', ld['id'], c.number, c.type, c_name or ld['title'], c.duration_sec, item_time=c.call_time)

        msgs = SmsMessage.query.filter(SmsMessage.message_time != None).all()
        for m in msgs:
            ents = find_entities_by_phone(m.address)
            c_name = ents['contacts'][0]['name'] if ents['contacts'] else None
            for cl in ents['clients']:
                create_telephony_activity('sms', 'client', cl['id'], m.address, m.type, c_name or cl['name'], body=m.body, item_time=m.message_time)
            for ld in ents['leads']:
                create_telephony_activity('sms', 'lead', ld['id'], m.address, m.type, c_name or ld['title'], body=m.body, item_time=m.message_time)

        db.session.commit()
    except Exception:
        db.session.rollback()


def authenticate_device(token):
    """Verify that a device exists with the given token and is active."""
    if not token:
        return None
    device = SmsDevice.query.filter_by(token=token.strip(), is_active=True).first()
    if device:
        device.last_seen = datetime.utcnow()
    return device


# ═══════════════════════════════════════════════════════════════════════
# 1. MOBILE APP GATEWAY ENDPOINTS (Polled by phone)
# ═══════════════════════════════════════════════════════════════════════

def pending_task_ids(device, limit=20):
    """Oldest pending tasks addressed to this device or to any device."""
    rows = db.session.query(SmsQueue.id).filter(
        (SmsQueue.device_id == device.id) | (SmsQueue.device_id == None),
        SmsQueue.status == 'pending'
    ).order_by(SmsQueue.created_at.asc(), SmsQueue.id.asc()).limit(limit).all()
    return [task_id for (task_id,) in rows]


def claim_next_task(device):
    """Atomically move one pending task to processing so concurrent pollers never share it."""
    for task_id in pending_task_ids(device):
        claimed = SmsQueue.query.filter(
            SmsQueue.id == task_id,
            SmsQueue.status == 'pending',
            (SmsQueue.device_id == device.id) | (SmsQueue.device_id == None),
        ).update({
            SmsQueue.status: 'processing',
            SmsQueue.device_id: db.func.coalesce(SmsQueue.device_id, device.id),
        }, synchronize_session=False)
        db.session.commit()
        if claimed:
            return db.session.get(SmsQueue, task_id)
    return None


@sms_bp.route('/next.php', methods=['GET'])
@sms_bp.route('/next', methods=['GET'])
def get_next_task():
    """Aplikacja mobilna co ~5 sekund odpytuje o kolejne zlecenie."""
    token = (request.headers.get('X-Device-Token') or request.args.get('token', '')).strip()
    device = authenticate_device(token)
    if not device:
        return jsonify({'error': 'Invalid token'}), 403

    task = claim_next_task(device)
    if not task:
        db.session.commit()
        return Response('null', mimetype='application/json', status=200)

    if task.action == 'make_call':
        return jsonify({
            'action': 'make_call',
            'id': task.id,
            'to': task.phone_number,
            'number': task.phone_number
        }), 200

    if task.action == 'send_sms':
        return jsonify({
            'id': task.id,
            'to': task.phone_number,
            'text': task.message
        }), 200

    if task.action == 'get_stats':
        return jsonify({
            'action': 'get_stats',
            'id': task.id
        }), 200

    payload = {}
    if task.payload:
        try:
            payload = json.loads(task.payload)
        except Exception:
            payload = {}

    if task.action == 'get_full_history':
        res_history = {
            'action': 'get_full_history',
            'id': task.id,
            'limit': payload.get('limit', 500)
        }
        if payload.get('start_date'):
            res_history['start_date'] = payload.get('start_date')
        if payload.get('end_date'):
            res_history['end_date'] = payload.get('end_date')
        return jsonify(res_history), 200

    if task.action == 'get_sms_history':
        return jsonify({
            'action': 'get_sms_history',
            'id': task.id,
            'number': payload.get('number', task.phone_number),
            'limit': payload.get('limit', 100)
        }), 200

    if task.action == 'get_sms_history_by_date':
        return jsonify({
            'action': 'get_sms_history_by_date',
            'id': task.id,
            'start_date': payload.get('start_date'),
            'end_date': payload.get('end_date'),
            'limit': payload.get('limit', 100)
        }), 200

    return jsonify({
        'id': task.id,
        'to': task.phone_number,
        'text': task.message
    }), 200


@sms_bp.route('/report.php', methods=['POST'])
@sms_bp.route('/report', methods=['POST'])
def report_sms_status():
    """Potwierdzenie wysyłki SMS przez telefon."""
    data = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()
    device = authenticate_device(token)
    if not device:
        return jsonify({'error': 'Invalid token'}), 403

    task_id = data.get('id')
    status = data.get('status', 'sent')
    if status not in ('sent', 'failed', 'called'):
        return jsonify({'error': 'Invalid status'}), 400

    task = db.session.get(SmsQueue, task_id) if task_id else None
    if task and (task.device_id != device.id or task.status != 'processing'):
        return jsonify({'error': 'Brak dostępu'}), 403
    if task:
        task.status = status
        task.sent_at = datetime.utcnow()
        if status == 'failed':
            task.error_message = data.get('error', 'Błąd modułu GSM lub brak uprawnień')

        if task.action == 'make_call' and status == 'called':
            now_dt = datetime.utcnow()
            ents = find_entities_by_phone(task.phone_number)
            c_name = ents['contacts'][0]['name'] if ents['contacts'] else None
            u_caller = db.session.get(User, task.user_id) if task.user_id else None
            u_name = f"{u_caller.first_name} {u_caller.last_name}".strip() if u_caller else None
            for cl in ents['clients']:
                create_telephony_activity('call', 'client', cl['id'], task.phone_number, 'outgoing', c_name or cl['name'], duration_sec=0, item_time=now_dt, user_id=task.user_id, caller_name=u_name)
            for ld in ents['leads']:
                create_telephony_activity('call', 'lead', ld['id'], task.phone_number, 'outgoing', c_name or ld['title'], duration_sec=0, item_time=now_dt, user_id=task.user_id, caller_name=u_name)

        elif task.action == 'send_sms' and status == 'sent':
            now_ms = int(datetime.utcnow().timestamp() * 1000)
            now_dt = datetime.utcnow()
            client_id = task.client_id or find_client_by_phone(task.phone_number)
            msg = SmsMessage(
                device_id=device.id,
                address=task.phone_number,
                body=task.message,
                type='sent',
                timestamp=now_ms,
                message_time=now_dt,
                date_formatted=now_dt.strftime('%Y-%m-%d %H:%M:%S'),
                client_id=client_id
            )
            db.session.add(msg)

    db.session.commit()
    return jsonify({'success': True}), 200


@sms_bp.route('/stats.php', methods=['POST'])
@sms_bp.route('/stats', methods=['POST'])
def receive_stats():
    """Odbieranie raportu statystyk."""
    data = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()
    device = authenticate_device(token)
    if not device:
        return jsonify({'error': 'Invalid token'}), 403

    today = data.get('today')
    week = data.get('week')

    if today is not None:
        device.today_stats = json.dumps(today)
    if week is not None:
        device.week_stats = json.dumps(week)
    device.stats_updated_at = datetime.utcnow()

    req_id = data.get('request_id')
    if req_id:
        task = db.session.get(SmsQueue, req_id)
        if task and task.device_id == device.id and task.action == 'get_stats' and task.status == 'processing':
            task.status = 'completed'
            task.sent_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'success': True}), 200


@sms_bp.route('/history.php', methods=['POST'])
@sms_bp.route('/history', methods=['POST'])
def receive_call_history():
    """Odbieranie bilingu / historii połączeń z telefonu."""
    data = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()
    device = authenticate_device(token)
    if not device:
        return jsonify({'error': 'Invalid token'}), 403

    history = data.get('history', [])
    inserted_count = 0

    for item in history:
        number = str(item.get('number', '')).strip()
        if not number:
            continue
        ts = item.get('timestamp')

        existing = PhoneCall.query.filter_by(
            device_id=device.id,
            number=number,
            timestamp=ts
        ).first() if ts else None

        if not existing:
            call_time = None
            if ts:
                try:
                    call_time = datetime.utcfromtimestamp(ts / 1000.0)
                except Exception:
                    pass

            if device.sync_from:
                sync_from_ms = int(device.sync_from.timestamp() * 1000)
                if (call_time and call_time < device.sync_from) or (ts and ts < sync_from_ms):
                    continue

            ents = find_entities_by_phone(number)
            client_id = ents['clients'][0]['id'] if ents['clients'] else None

            call = PhoneCall(
                device_id=device.id,
                number=number,
                name=item.get('name'),
                type=item.get('type', 'incoming'),
                timestamp=ts,
                call_time=call_time,
                date_formatted=item.get('date_formatted'),
                duration_sec=item.get('duration_sec', 0),
                duration_formatted=item.get('duration_formatted'),
                client_id=client_id
            )
            db.session.add(call)
            inserted_count += 1

            # Zapisz do aktywności wg. daty
            c_name = ents['contacts'][0]['name'] if ents['contacts'] else None
            for cl in ents['clients']:
                create_telephony_activity('call', 'client', cl['id'], number, call.type, c_name or cl['name'], call.duration_sec, item_time=call_time)
            for ld in ents['leads']:
                create_telephony_activity('call', 'lead', ld['id'], number, call.type, c_name or ld['title'], call.duration_sec, item_time=call_time)

    req_id = data.get('request_id')
    if req_id:
        task = db.session.get(SmsQueue, req_id)
        if task and task.device_id == device.id and task.action == 'get_full_history' and task.status == 'processing':
            task.status = 'completed'
            task.sent_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'success': True, 'inserted': inserted_count}), 200


@sms_bp.route('/sms_history.php', methods=['POST'])
@sms_bp.route('/sms_history', methods=['POST'])
def receive_sms_history():
    """Odbieranie historii SMS z telefonu."""
    data = request.get_json(silent=True) or {}
    token = data.get('token', '').strip()
    device = authenticate_device(token)
    if not device:
        return jsonify({'error': 'Invalid token'}), 403

    sms_list = data.get('sms_history', [])
    inserted_count = 0

    for item in sms_list:
        addr = str(item.get('address', '')).strip()
        body = item.get('body', '')
        ts = item.get('timestamp')
        m_type = item.get('type', 'received')

        if not addr:
            continue

        existing = SmsMessage.query.filter_by(
            device_id=device.id,
            address=addr,
            timestamp=ts,
            type=m_type
        ).first() if ts else None

        if not existing:
            msg_time = None
            if ts:
                try:
                    msg_time = datetime.utcfromtimestamp(ts / 1000.0)
                except Exception:
                    pass

            if device.sync_from:
                sync_from_ms = int(device.sync_from.timestamp() * 1000)
                if (msg_time and msg_time < device.sync_from) or (ts and ts < sync_from_ms):
                    continue

            ents = find_entities_by_phone(addr)
            client_id = ents['clients'][0]['id'] if ents['clients'] else None

            msg = SmsMessage(
                device_id=device.id,
                address=addr,
                body=body,
                type=m_type,
                timestamp=ts,
                message_time=msg_time,
                date_formatted=item.get('date_formatted'),
                client_id=client_id
            )
            db.session.add(msg)
            inserted_count += 1

            # Zapisz do aktywności wg. daty
            c_name = ents['contacts'][0]['name'] if ents['contacts'] else None
            for cl in ents['clients']:
                create_telephony_activity('sms', 'client', cl['id'], addr, m_type, c_name or cl['name'], body=body, item_time=msg_time)
            for ld in ents['leads']:
                create_telephony_activity('sms', 'lead', ld['id'], addr, m_type, c_name or ld['title'], body=body, item_time=msg_time)

    req_id = data.get('request_id')
    if req_id:
        task = db.session.get(SmsQueue, req_id)
        if task and task.device_id == device.id and task.action in ('get_sms_history', 'get_sms_history_by_date') and task.status == 'processing':
            task.status = 'completed'
            task.sent_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'success': True, 'inserted': inserted_count}), 200


# ═══════════════════════════════════════════════════════════════════════
# 2. CRM MANAGEMENT API (Zabezpieczone JWT)
# ═══════════════════════════════════════════════════════════════════════

def get_user_accessible_device_ids():
    """Zwraca listę ID telefonów należących do bieżącego użytkownika (każdy widzi tylko swój telefon)."""
    from ..utils.deletion import current_user
    curr_u = current_user()
    curr_u_id = curr_u.id if curr_u else None
    if not curr_u_id:
        return []
    devs = SmsDevice.query.filter_by(user_id=curr_u_id).all()
    return [d.id for d in devs]


@sms_bp.route('/devices', methods=['GET'])
@jwt_required()
def list_devices():
    """Lista wszystkich telefonów należących do bieżącego użytkownika."""
    from ..utils.deletion import current_user
    curr_u = current_user()
    curr_u_id = curr_u.id if curr_u else None
    if not curr_u_id:
        return jsonify([]), 200

    devices = SmsDevice.query.filter_by(user_id=curr_u_id).order_by(SmsDevice.created_at.desc()).all()
    result = []
    for d in devices:
        item = d.to_dict()
        item['pending_tasks'] = SmsQueue.query.filter_by(device_id=d.id, status='pending').count()
        item['total_calls'] = PhoneCall.query.filter_by(device_id=d.id).count()
        item['total_messages'] = SmsMessage.query.filter_by(device_id=d.id).count()
        result.append(item)
    return jsonify(result), 200


@sms_bp.route('/devices', methods=['POST'])
@jwt_required()
def add_device():
    """Dodaj nowy telefon do CRM (przypisany do bieżącego użytkownika)."""
    from ..utils.deletion import current_user
    data = request.get_json(silent=True) or {}
    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Nazwa urządzenia jest wymagana'}), 400

    token = f'zen_sms_{secrets.token_hex(16)}'

    if SmsDevice.query.filter_by(token=token).first():
        return jsonify({'error': 'Urządzenie z tym tokenem już istnieje'}), 400

    phone = data.get('phone_number', '').strip() or None
    sync_from_raw = data.get('sync_from')
    sync_from_dt = None
    if sync_from_raw:
        try:
            sync_from_dt = datetime.strptime(str(sync_from_raw)[:10], '%Y-%m-%d')
        except Exception:
            pass

    curr_u = current_user()
    if not curr_u:
        return jsonify({'error': 'Brak identyfikatora użytkownika'}), 401

    device = SmsDevice(
        name=name,
        phone_number=phone,
        token=token,
        user_id=curr_u.id,
        is_active=bool(data.get('is_active', True)),
        sync_from=sync_from_dt
    )
    db.session.add(device)
    db.session.commit()
    return jsonify(device.to_dict()), 201


@sms_bp.route('/devices/<int:device_id>', methods=['PUT'])
@jwt_required()
def update_device(device_id):
    """Edycja parametrów własnego telefonu."""
    from ..utils.deletion import current_user
    device = db.session.get(SmsDevice, device_id)
    if not device:
        return jsonify({'error': 'Urządzenie nie istnieje'}), 404

    curr_u = current_user()
    if not curr_u or device.user_id != curr_u.id:
        return jsonify({'error': 'Brak uprawnień do edycji tego telefonu'}), 403

    data = request.get_json(silent=True) or {}
    if 'name' in data:
        device.name = data['name'].strip()
    if 'phone_number' in data:
        device.phone_number = data['phone_number'].strip() or None
    if 'is_active' in data:
        device.is_active = bool(data['is_active'])

    if 'sync_from' in data:
        sync_from_raw = data.get('sync_from')
        if sync_from_raw:
            try:
                device.sync_from = datetime.strptime(str(sync_from_raw)[:10], '%Y-%m-%d')
            except Exception:
                device.sync_from = None
        else:
            device.sync_from = None

        if device.sync_from:
            sync_from_ms = int(device.sync_from.timestamp() * 1000)
            PhoneCall.query.filter(
                PhoneCall.device_id == device.id,
                (PhoneCall.call_time < device.sync_from) | (PhoneCall.timestamp < sync_from_ms)
            ).delete(synchronize_session=False)
            SmsMessage.query.filter(
                SmsMessage.device_id == device.id,
                (SmsMessage.message_time < device.sync_from) | (SmsMessage.timestamp < sync_from_ms)
            ).delete(synchronize_session=False)

    if data.get('regenerate_token'):
        device.token = f'zen_sms_{secrets.token_hex(16)}'

    db.session.commit()
    return jsonify(device.to_dict()), 200


@sms_bp.route('/devices/<int:device_id>', methods=['DELETE'])
@jwt_required()
def delete_device(device_id):
    """Usunięcie własnego urządzenia z CRM."""
    from ..utils.deletion import current_user
    device = db.session.get(SmsDevice, device_id)
    if not device:
        return jsonify({'error': 'Urządzenie nie istnieje'}), 404

    curr_u = current_user()
    if not curr_u or device.user_id != curr_u.id:
        return jsonify({'error': 'Brak uprawnień do usunięcia tego telefonu'}), 403

    db.session.delete(device)
    db.session.commit()
    return jsonify({'ok': True}), 200


# ─── SYNCHRONIZACJA (PRZYCISK NA PASKU GŁÓWNYM) ───

@sms_bp.route('/sync', methods=['POST'])
@jwt_required()
def trigger_sync():
    """
    Automatyczna synchronizacja:
    - Przy pierwszym razie: pobiera pełną historię połączeń (limit 1000) i SMS (365 dni)
    - Przy kolejnych razach: pobiera ostatnie połączenia (limit 200) i SMS od momentu ostatniej synchronizacji
    """
    allowed_dev_ids = get_user_accessible_device_ids()
    q = SmsDevice.query.filter_by(is_active=True)
    if allowed_dev_ids is not None:
        q = q.filter(SmsDevice.id.in_(allowed_dev_ids))
    devices = q.all()
    if not devices:
        return jsonify({'error': 'Brak podłączonych aktywnych telefonów. Dodaj telefon w zakładce Telefonia & SMS.'}), 400

    queued_tasks = 0
    now = datetime.utcnow()
    now_ms = int(now.timestamp() * 1000)

    for dev in devices:
        min_start_ms = int(dev.sync_from.timestamp() * 1000) if dev.sync_from else None
        if not dev.last_sync_at:
            # Pierwsza synchronizacja: pobierz wszystko
            payload_calls = {'limit': 1000}
            if min_start_ms:
                payload_calls['start_date'] = min_start_ms
                payload_calls['end_date'] = now_ms

            task_calls = SmsQueue(
                device_id=dev.id,
                action='get_full_history',
                payload=json.dumps(payload_calls),
                status='pending'
            )
            # 365 dni wstecz lub od sync_from
            if min_start_ms:
                start_date_ms = min_start_ms
            else:
                start_date_ms = int((now - timedelta(days=365)).timestamp() * 1000)

            task_sms = SmsQueue(
                device_id=dev.id,
                action='get_sms_history_by_date',
                payload=json.dumps({
                    'start_date': start_date_ms,
                    'end_date': now_ms,
                    'limit': 500
                }),
                status='pending'
            )
            db.session.add_all([task_calls, task_sms])
            queued_tasks += 2
        else:
            # Kolejna synchronizacja: pobierz ostatnie
            task_calls = SmsQueue(
                device_id=dev.id,
                action='get_full_history',
                payload=json.dumps({'limit': 200}),
                status='pending'
            )
            # Od momentu poprzedniej synchronizacji minus 2 godziny marginesu
            prev_sync_ms = int((dev.last_sync_at - timedelta(hours=2)).timestamp() * 1000)
            start_date_ms = max(min_start_ms, prev_sync_ms) if min_start_ms else prev_sync_ms
            task_sms = SmsQueue(
                device_id=dev.id,
                action='get_sms_history_by_date',
                payload=json.dumps({
                    'start_date': start_date_ms,
                    'end_date': now_ms,
                    'limit': 200
                }),
                status='pending'
            )
            db.session.add_all([task_calls, task_sms])
            queued_tasks += 2

        dev.last_sync_at = now

    backfill_telephony_activities()
    db.session.commit()
    return jsonify({
        'success': True,
        'queued_tasks': queued_tasks,
        'devices_count': len(devices)
    }), 200


# ─── HISTORIA POŁĄCZEŃ I SMS DLA DOWOLNEGO REKORDU (KLIENT, LEAD, KONTAKT) ───

@sms_bp.route('/entity-history', methods=['GET'])
@jwt_required()
def get_entity_history():
    """
    Pobiera historię połączeń i SMS dla klienta, leada, kontaktu lub numeru telefonu.
    Zwraca wszystkie dopasowane połączenia i wiadomości, nawet jeśli kontakt występuje w 2 miejscach.
    """
    entity_type = request.args.get('type')  # 'client', 'lead', 'contact'
    entity_id = request.args.get('id', type=int)
    phone_param = request.args.get('phone', '').strip()

    phones = []
    if phone_param:
        phones.append(phone_param)

    if entity_type == 'client' and entity_id:
        c = db.session.get(Client, entity_id)
        if c and c.phone:
            phones.append(c.phone)
        cts = Contact.query.filter_by(client_id=entity_id, deleted_at=None).all()
        for ct in cts:
            if ct.phone:
                phones.append(ct.phone)

    elif entity_type == 'lead' and entity_id:
        l = db.session.get(Lead, entity_id)
        if l:
            if l.client_id:
                c = db.session.get(Client, l.client_id)
                if c and c.phone:
                    phones.append(c.phone)
            cts = Contact.query.filter_by(lead_id=entity_id, deleted_at=None).all()
            for ct in cts:
                if ct.phone:
                    phones.append(ct.phone)

    elif entity_type == 'contact' and entity_id:
        ct = db.session.get(Contact, entity_id)
        if ct and ct.phone:
            phones.append(ct.phone)

    target_variants = set()
    for p in phones:
        target_variants.update(normalize_phone_variants(p))

    unique_phones = list(dict.fromkeys([p.strip() for p in phones if p and str(p).strip()]))
    if not target_variants:
        return jsonify({'calls': [], 'messages': [], 'phones': unique_phones, 'phone_numbers': unique_phones}), 200

    accessible_devices = get_user_accessible_device_ids()
    all_calls = PhoneCall.query.outerjoin(SmsDevice, PhoneCall.device_id == SmsDevice.id).filter(
        PhoneCall.device_id.in_(accessible_devices),
        db.or_(
            SmsDevice.sync_from == None,
            PhoneCall.call_time == None,
            PhoneCall.call_time >= SmsDevice.sync_from
        )
    ).order_by(PhoneCall.timestamp.desc(), PhoneCall.id.desc()).all()
    matched_calls = []
    for c in all_calls:
        if normalize_phone_variants(c.number) & target_variants:
            cd = c.to_dict()
            ents = find_entities_by_phone(c.number)
            cd['entities'] = ents
            cd['contact'] = ents['contacts'][0] if ents['contacts'] else None
            matched_calls.append(cd)

    all_messages = SmsMessage.query.outerjoin(SmsDevice, SmsMessage.device_id == SmsDevice.id).filter(
        SmsMessage.device_id.in_(accessible_devices),
        db.or_(
            SmsDevice.sync_from == None,
            SmsMessage.message_time == None,
            SmsMessage.message_time >= SmsDevice.sync_from
        )
    ).order_by(SmsMessage.timestamp.desc(), SmsMessage.id.desc()).all()
    matched_messages = []
    for m in all_messages:
        if normalize_phone_variants(m.address) & target_variants:
            md = m.to_dict()
            ents = find_entities_by_phone(m.address)
            md['entities'] = ents
            md['contact'] = ents['contacts'][0] if ents['contacts'] else None
            matched_messages.append(md)

    return jsonify({
        'calls': matched_calls,
        'messages': matched_messages,
        'phones': unique_phones,
        'phone_numbers': unique_phones
    }), 200


# ─── WYSYŁKA SMS ───

@sms_bp.route('/send', methods=['POST'])
@jwt_required()
def send_sms():
    """Wstawienie wiadomości SMS do kolejki wysyłkowej."""
    from ..utils.deletion import current_user
    curr_u = current_user()
    curr_u_id = curr_u.id if curr_u else None
    if not curr_u_id:
        return jsonify({'error': 'Brak identyfikatora użytkownika'}), 401

    data = request.get_json(silent=True) or {}
    phone_number = str(data.get('phone_number', '')).strip()
    message = str(data.get('message', '')).strip()

    if not phone_number:
        return jsonify({'error': 'Numer telefonu jest wymagany'}), 400
    if not message:
        return jsonify({'error': 'Treść wiadomości nie może być pusta'}), 400

    device_id = data.get('device_id')
    if device_id:
        device = db.session.get(SmsDevice, device_id)
        if not device or not device.is_active:
            return jsonify({'error': 'Wybrane urządzenie nie jest aktywne'}), 400
        if device.user_id != curr_u_id:
            return jsonify({'error': 'Nie masz uprawnień do wysyłania z tego telefonu'}), 403
    else:
        user_devices = SmsDevice.query.filter_by(user_id=curr_u_id, is_active=True).all()
        if not user_devices:
            return jsonify({'error': 'Brak podłączonego aktywnego telefonu'}), 400
        device = next((d for d in user_devices if d.is_online), user_devices[0])
        device_id = device.id

    client_id = data.get('client_id')
    if not client_id:
        client_id = find_client_by_phone(phone_number)

    task = SmsQueue(
        device_id=device_id,
        phone_number=phone_number,
        message=message,
        action='send_sms',
        status='pending',
        client_id=client_id,
        user_id=curr_u_id
    )
    db.session.add(task)
    db.session.commit()

    return jsonify(task.to_dict()), 201


# ─── ZLECENIE WYKONANIA POŁĄCZENIA ───

@sms_bp.route('/call', methods=['POST'])
@jwt_required()
def make_call():
    """Wstawienie zlecenia wykonania połączenia do kolejki telefonu."""
    from ..utils.deletion import current_user
    curr_u = current_user()
    curr_u_id = curr_u.id if curr_u else None
    if not curr_u_id:
        return jsonify({'error': 'Brak identyfikatora użytkownika'}), 401

    data = request.get_json(silent=True) or {}
    phone_number = str(data.get('phone_number', '')).strip()

    if not phone_number:
        return jsonify({'error': 'Numer telefonu jest wymagany'}), 400

    device_id = data.get('device_id')
    if device_id:
        device = db.session.get(SmsDevice, device_id)
        if not device or not device.is_active:
            return jsonify({'error': 'Wybrane urządzenie nie jest aktywne'}), 400
        if device.user_id != curr_u_id:
            return jsonify({'error': 'Nie masz uprawnień do dzwonienia z tego telefonu'}), 403
    else:
        user_devices = SmsDevice.query.filter_by(user_id=curr_u_id, is_active=True).all()
        if not user_devices:
            return jsonify({'error': 'Brak podłączonych aktywnych telefonów. Dodaj telefon w zakładce Telefonia & SMS.'}), 400
        device = next((d for d in user_devices if d.is_online), user_devices[0])
        device_id = device.id

    client_id = data.get('client_id')
    if not client_id:
        client_id = find_client_by_phone(phone_number)

    user_name = f"{curr_u.first_name} {curr_u.last_name}".strip() if curr_u else None

    task = SmsQueue(
        device_id=device_id,
        phone_number=phone_number,
        message=None,
        action='make_call',
        status='pending',
        client_id=client_id,
        user_id=curr_u_id
    )
    db.session.add(task)

    # Zapisz zdarzenie w aktywności od razu po kliknięciu "Połącz"
    now_dt = datetime.utcnow()
    caller_info = f" przez: {user_name}" if user_name else (f" przez użytkownika #{curr_u_id}" if curr_u_id else "")
    dev_name = device.name or "telefon Android"
    ents = find_entities_by_phone(phone_number)
    target_clients = set()
    if client_id:
        target_clients.add(client_id)
    for cl in ents.get('clients', []):
        target_clients.add(cl['id'])

    for c_id in target_clients:
        act = Activity(
            action='call',
            description=f"Zlecono połączenie z telefonu ({dev_name}) na numer {phone_number}{caller_info}",
            entity_type='client',
            entity_id=c_id,
            user_id=curr_u_id,
            created_at=now_dt,
            meta={'phone': phone_number, 'device_id': device.id, 'device_name': dev_name, 'caller_name': user_name, 'direction': 'outgoing'}
        )
        db.session.add(act)

    for ld in ents.get('leads', []):
        act = Activity(
            action='call',
            description=f"Zlecono połączenie z telefonu ({dev_name}) na numer {phone_number}{caller_info}",
            entity_type='lead',
            entity_id=ld['id'],
            user_id=curr_u_id,
            created_at=now_dt,
            meta={'phone': phone_number, 'device_id': device.id, 'device_name': dev_name, 'caller_name': user_name, 'direction': 'outgoing'}
        )
        db.session.add(act)

    db.session.commit()

    return jsonify({
        'success': True,
        'task': task.to_dict(),
        'device_name': device.name,
        'caller_name': user_name,
        'message': t('Zlecono połączenie z {phone} na telefonie {device}', {'phone': phone_number, 'device': device.name})
    }), 201


# ─── TRIGGER AKCJI DLA TELEFONU ───

@sms_bp.route('/actions/trigger', methods=['POST'])
@jwt_required()
def trigger_action():
    """Zlecenie akcji na telefonie (np. get_stats, get_full_history, get_sms_history, get_sms_history_by_date)."""
    data = request.get_json(silent=True) or {}
    action = data.get('action')
    device_id = data.get('device_id')

    if not action:
        return jsonify({'error': 'Brak akcji'}), 400

    from ..utils.deletion import current_user
    curr_u = current_user()
    curr_u_id = curr_u.id if curr_u else None
    if not curr_u_id:
        return jsonify({'error': 'Brak identyfikatora użytkownika'}), 401

    if not device_id:
        user_devices = SmsDevice.query.filter_by(user_id=curr_u_id, is_active=True).all()
        if not user_devices:
            return jsonify({'error': 'Brak podłączonego aktywnego telefonu'}), 400
        device = next((d for d in user_devices if d.is_online), user_devices[0])
        device_id = device.id
    else:
        device = db.session.get(SmsDevice, device_id)
        if not device:
            return jsonify({'error': 'Urządzenie nie istnieje'}), 404
        if device.user_id != curr_u_id:
            return jsonify({'error': 'Brak uprawnień do tego telefonu'}), 403

    payload = {}
    phone_number = data.get('phone_number')

    if action == 'get_full_history':
        limit = data.get('limit', 500)
        try:
            limit = int(limit)
        except Exception:
            limit = 500
        payload['limit'] = limit

    if action == 'get_sms_history':
        if not phone_number:
            return jsonify({'error': 'Podaj numer telefonu do pobrania historii SMS'}), 400
        payload['number'] = phone_number
        payload['limit'] = int(data.get('limit', 100))

    if action == 'get_sms_history_by_date':
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        if not start_date or not end_date:
            return jsonify({'error': 'Wymagane daty początkowa i końcowa'}), 400
        payload['start_date'] = int(start_date)
        payload['end_date'] = int(end_date)
        payload['limit'] = int(data.get('limit', 100))

    task = SmsQueue(
        device_id=device_id,
        phone_number=phone_number,
        action=action,
        payload=json.dumps(payload) if payload else None,
        status='pending'
    )
    db.session.add(task)
    db.session.commit()

    return jsonify(task.to_dict()), 201


# ─── POŁĄCZENIA ───

@sms_bp.route('/calls', methods=['GET'])
@jwt_required()
def list_calls():
    """Lista połączeń zarejestrowanych z własnego telefonu z multi-dopasowaniem podmiotów."""
    search = request.args.get('search', '').strip()
    call_type = request.args.get('type', '').strip()
    device_id = request.args.get('device_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    allowed_dev_ids = get_user_accessible_device_ids()
    if not allowed_dev_ids:
        return jsonify({
            'calls': [],
            'total': 0,
            'pages': 0,
            'current_page': page
        }), 200

    q = PhoneCall.query.outerjoin(SmsDevice, PhoneCall.device_id == SmsDevice.id).filter(
        PhoneCall.device_id.in_(allowed_dev_ids),
        db.or_(
            SmsDevice.sync_from == None,
            PhoneCall.call_time == None,
            PhoneCall.call_time >= SmsDevice.sync_from
        )
    )

    if device_id and device_id in allowed_dev_ids:
        q = q.filter(PhoneCall.device_id == device_id)
    if call_type and call_type != 'all':
        q = q.filter(PhoneCall.type == call_type)
    if search:
        search_like = f'%{search}%'
        q = q.filter(
            (PhoneCall.number.ilike(search_like)) |
            (PhoneCall.name.ilike(search_like))
        )

    paginated = q.order_by(PhoneCall.timestamp.desc(), PhoneCall.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    calls_data = []
    for c in paginated.items:
        cd = c.to_dict()
        ents = find_entities_by_phone(c.number)
        cd['entities'] = ents
        cd['contact'] = ents['contacts'][0] if ents['contacts'] else None
        calls_data.append(cd)

    return jsonify({
        'calls': calls_data,
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page
    }), 200


@sms_bp.route('/calls/<int:call_id>/note', methods=['PUT'])
@jwt_required()
def update_call_note(call_id):
    call = db.session.get(PhoneCall, call_id)
    if not call or call.device_id not in get_user_accessible_device_ids():
        return jsonify({'error': 'Połączenie nie istnieje'}), 404
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'error': 'Nieprawidłowy opis'}), 400
    note = data.get('note')
    if not isinstance(note, str) or len(note) > 5000:
        return jsonify({'error': 'Opis musi być tekstem o długości do 5000 znaków'}), 400
    call.note = note.strip()
    db.session.commit()
    return jsonify(call.to_dict()), 200


# ─── WIADOMOŚCI SMS ───

@sms_bp.route('/messages', methods=['GET'])
@jwt_required()
def list_messages():
    """Lista wiadomości SMS (odebrane i wysłane) z powiązaniami do klientów i kontaktów."""
    search = request.args.get('search', '').strip()
    msg_type = request.args.get('type', '').strip()
    address = request.args.get('address', '').strip()
    device_id = request.args.get('device_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    allowed_dev_ids = get_user_accessible_device_ids()
    if not allowed_dev_ids:
        return jsonify({
            'messages': [],
            'total': 0,
            'pages': 0,
            'current_page': page
        }), 200

    q = SmsMessage.query.outerjoin(SmsDevice, SmsMessage.device_id == SmsDevice.id).filter(
        SmsMessage.device_id.in_(allowed_dev_ids),
        db.or_(
            SmsDevice.sync_from == None,
            SmsMessage.message_time == None,
            SmsMessage.message_time >= SmsDevice.sync_from
        )
    )

    if device_id and device_id in allowed_dev_ids:
        q = q.filter(SmsMessage.device_id == device_id)
    if msg_type and msg_type != 'all':
        q = q.filter(SmsMessage.type == msg_type)
    if address:
        norm = normalize_phone(address)
        q = q.filter(SmsMessage.address.ilike(f'%{norm}%'))
    if search:
        search_like = f'%{search}%'
        q = q.filter(
            (SmsMessage.address.ilike(search_like)) |
            (SmsMessage.body.ilike(search_like))
        )

    paginated = q.order_by(SmsMessage.timestamp.desc(), SmsMessage.id.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    messages_data = []
    for m in paginated.items:
        md = m.to_dict()
        ents = find_entities_by_phone(m.address)
        md['entities'] = ents
        md['contact'] = ents['contacts'][0] if ents['contacts'] else None
        messages_data.append(md)

    return jsonify({
        'messages': messages_data,
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': page
    }), 200


@sms_bp.route('/threads', methods=['GET'])
@jwt_required()
def list_threads():
    """Wątki konwersacji pogrupowane po numerze telefonu z pełnymi powiązaniami."""
    allowed_dev_ids = get_user_accessible_device_ids()
    if not allowed_dev_ids:
        return jsonify([]), 200

    q = SmsMessage.query.outerjoin(SmsDevice, SmsMessage.device_id == SmsDevice.id).filter(
        SmsMessage.device_id.in_(allowed_dev_ids),
        db.or_(
            SmsDevice.sync_from == None,
            SmsMessage.message_time == None,
            SmsMessage.message_time >= SmsDevice.sync_from
        )
    )
    all_msgs = q.order_by(SmsMessage.timestamp.desc(), SmsMessage.id.desc()).all()
    threads_map = {}

    for m in all_msgs:
        key = normalize_phone(m.address)
        if not key:
            key = m.address

        if key not in threads_map:
            entities = find_entities_by_phone(m.address)
            threads_map[key] = {
                'address': m.address,
                'entities': entities,
                'client': entities['clients'][0] if entities['clients'] else None,
                'contact': entities['contacts'][0] if entities['contacts'] else None,
                'lead': entities['leads'][0] if entities['leads'] else None,
                'last_message': m.body,
                'last_type': m.type,
                'last_time': m.date_formatted or (m.message_time.isoformat() if m.message_time else None),
                'total_messages': 1,
                'received_count': 1 if m.type == 'received' else 0,
                'sent_count': 1 if m.type == 'sent' else 0,
            }
        else:
            threads_map[key]['total_messages'] += 1
            if m.type == 'received':
                threads_map[key]['received_count'] += 1
            else:
                threads_map[key]['sent_count'] += 1

    return jsonify(list(threads_map.values())), 200


# ─── KOLEJKA ZADAŃ ───

@sms_bp.route('/queue', methods=['GET'])
@jwt_required()
def list_queue():
    """Lista ostatnich i oczekujących zadań w kolejce."""
    allowed_dev_ids = get_user_accessible_device_ids()
    from ..utils.deletion import current_user
    curr_u = current_user()
    curr_u_id = curr_u.id if curr_u else None
    if not allowed_dev_ids and not curr_u_id:
        return jsonify([]), 200

    q = SmsQueue.query
    if allowed_dev_ids:
        q = q.filter(db.or_(SmsQueue.device_id.in_(allowed_dev_ids), SmsQueue.user_id == curr_u_id))
    else:
        q = q.filter(SmsQueue.user_id == curr_u_id)

    tasks = q.order_by(SmsQueue.created_at.desc()).limit(100).all()
    return jsonify([t.to_dict() for t in tasks]), 200


@sms_bp.route('/queue/<int:task_id>', methods=['DELETE'])
@jwt_required()
def cancel_queue_task(task_id):
    """Anulowanie oczekującego zadania."""
    from ..utils.deletion import current_user
    task = db.session.get(SmsQueue, task_id)
    if not task:
        return jsonify({'error': 'Zadanie nie istnieje'}), 404

    curr_u = current_user()
    curr_u_id = curr_u.id if curr_u else None
    allowed_dev_ids = get_user_accessible_device_ids()
    if task.user_id != curr_u_id and task.device_id not in allowed_dev_ids:
        return jsonify({'error': 'Brak uprawnień do anulowania tego zadania'}), 403

    if task.status in ('sent', 'completed'):
        return jsonify({'error': 'Zadanie zostało już zrealizowane'}), 400

    db.session.delete(task)
    db.session.commit()
    return jsonify({'ok': True}), 200


# ─── STATYSTYKI OBLICZANE Z DANYCH BAZY ───

@sms_bp.route('/stats-summary', methods=['GET'])
@jwt_required()
def get_stats_summary():
    """Statystyki obliczane w 100% ze wszystkich połączeń i SMS-ów zgromadzonych w bazie CRM dla własnego telefonu."""
    allowed_dev_ids = get_user_accessible_device_ids()
    if not allowed_dev_ids:
        devices = []
    else:
        devices = SmsDevice.query.filter(SmsDevice.id.in_(allowed_dev_ids)).all()
    total_devices = len(devices)
    online_devices = sum(1 for d in devices if d.is_online)

    now = datetime.utcnow()
    today_start = datetime(now.year, now.month, now.day)
    today_start_ms = int(today_start.timestamp() * 1000)

    week_start = now - timedelta(days=7)
    week_start_ms = int(week_start.timestamp() * 1000)

    month_start = now - timedelta(days=30)
    month_start_ms = int(month_start.timestamp() * 1000)

    # 1. Połączenia
    if not allowed_dev_ids:
        calls_all = []
    else:
        calls_q = PhoneCall.query.outerjoin(SmsDevice, PhoneCall.device_id == SmsDevice.id).filter(
            PhoneCall.device_id.in_(allowed_dev_ids),
            db.or_(
                SmsDevice.sync_from == None,
                PhoneCall.call_time == None,
                PhoneCall.call_time >= SmsDevice.sync_from
            )
        )
        calls_all = calls_q.all()
    total_calls = len(calls_all)
    incoming_calls = sum(1 for c in calls_all if c.type == 'incoming')
    outgoing_calls = sum(1 for c in calls_all if c.type == 'outgoing')
    missed_calls = sum(1 for c in calls_all if c.type == 'missed')
    rejected_calls = sum(1 for c in calls_all if c.type == 'rejected')
    total_duration_sec = sum(c.duration_sec or 0 for c in calls_all)

    # Dzisiejsze
    today_calls_list = [c for c in calls_all if (c.timestamp and c.timestamp >= today_start_ms) or (c.call_time and c.call_time >= today_start)]
    today_calls_count = len(today_calls_list)
    today_incoming = sum(1 for c in today_calls_list if c.type == 'incoming')
    today_outgoing = sum(1 for c in today_calls_list if c.type == 'outgoing')
    today_missed = sum(1 for c in today_calls_list if c.type == 'missed')
    today_rejected = sum(1 for c in today_calls_list if c.type == 'rejected')
    today_duration_sec = sum(c.duration_sec or 0 for c in today_calls_list)

    # Ostatnie 7 dni
    week_calls_list = [c for c in calls_all if (c.timestamp and c.timestamp >= week_start_ms) or (c.call_time and c.call_time >= week_start)]
    week_calls_count = len(week_calls_list)
    week_duration_sec = sum(c.duration_sec or 0 for c in week_calls_list)

    # Ostatnie 30 dni
    month_calls_list = [c for c in calls_all if (c.timestamp and c.timestamp >= month_start_ms) or (c.call_time and c.call_time >= month_start)]
    month_calls_count = len(month_calls_list)
    month_duration_sec = sum(c.duration_sec or 0 for c in month_calls_list)

    # 2. SMS-y
    if not allowed_dev_ids:
        sms_all = []
    else:
        sms_q = SmsMessage.query.outerjoin(SmsDevice, SmsMessage.device_id == SmsDevice.id).filter(
            SmsMessage.device_id.in_(allowed_dev_ids),
            db.or_(
                SmsDevice.sync_from == None,
                SmsMessage.message_time == None,
                SmsMessage.message_time >= SmsDevice.sync_from
            )
        )
        sms_all = sms_q.all()
    total_sms = len(sms_all)
    sms_received = sum(1 for m in sms_all if m.type == 'received')
    sms_sent = sum(1 for m in sms_all if m.type == 'sent')

    today_sms_list = [m for m in sms_all if (m.timestamp and m.timestamp >= today_start_ms) or (m.message_time and m.message_time >= today_start)]
    today_sms_count = len(today_sms_list)
    today_sms_sent = sum(1 for m in today_sms_list if m.type == 'sent')
    today_sms_received = sum(1 for m in today_sms_list if m.type == 'received')

    week_sms_list = [m for m in sms_all if (m.timestamp and m.timestamp >= week_start_ms) or (m.message_time and m.message_time >= week_start)]
    week_sms_count = len(week_sms_list)

    def fmt_dur(sec):
        h = sec // 3600
        m = (sec % 3600) // 60
        s = sec % 60
        return f"{h}h {m}m {s}s" if h else f"{m}m {s}s"

    # 3. Top kontakty
    number_counts = {}
    for c in calls_all:
        norm = normalize_phone(c.number)
        if norm:
            if norm not in number_counts:
                number_counts[norm] = {'number': c.number, 'name': c.name, 'calls': 0, 'sms': 0, 'duration': 0}
            number_counts[norm]['calls'] += 1
            number_counts[norm]['duration'] += (c.duration_sec or 0)
            if not number_counts[norm]['name'] and c.name:
                number_counts[norm]['name'] = c.name

    for m in sms_all:
        norm = normalize_phone(m.address)
        if norm:
            if norm not in number_counts:
                number_counts[norm] = {'number': m.address, 'name': None, 'calls': 0, 'sms': 0, 'duration': 0}
            number_counts[norm]['sms'] += 1

    top_contacts = sorted(number_counts.values(), key=lambda x: (x['calls'] + x['sms']), reverse=True)[:8]
    for tc in top_contacts:
        tc['entities'] = find_entities_by_phone(tc['number'])
        tc['duration_formatted'] = fmt_dur(tc['duration'])

    pending_tasks = SmsQueue.query.filter_by(status='pending').count()

    return jsonify({
        'total_devices': total_devices,
        'online_devices': online_devices,
        'pending_tasks': pending_tasks,
        'all_time': {
            'calls_total': total_calls,
            'calls_incoming': incoming_calls,
            'calls_outgoing': outgoing_calls,
            'calls_missed': missed_calls,
            'calls_rejected': rejected_calls,
            'duration_sec': total_duration_sec,
            'duration_formatted': fmt_dur(total_duration_sec),
            'sms_total': total_sms,
            'sms_sent': sms_sent,
            'sms_received': sms_received,
        },
        'today': {
            'calls_total': today_calls_count,
            'calls_incoming': today_incoming,
            'calls_outgoing': today_outgoing,
            'calls_missed': today_missed,
            'calls_rejected': today_rejected,
            'duration_sec': today_duration_sec,
            'duration_formatted': fmt_dur(today_duration_sec),
            'sms_total': today_sms_count,
            'sms_sent': today_sms_sent,
            'sms_received': today_sms_received,
        },
        'week': {
            'calls_total': week_calls_count,
            'duration_sec': week_duration_sec,
            'duration_formatted': fmt_dur(week_duration_sec),
            'sms_total': week_sms_count,
        },
        'month': {
            'calls_total': month_calls_count,
            'duration_sec': month_duration_sec,
            'duration_formatted': fmt_dur(month_duration_sec),
        },
        'top_contacts': top_contacts,
        'devices': [d.to_dict() for d in devices],
        'aggregated_today': {
            'calls_total': today_calls_count,
            'duration_total_sec': today_duration_sec,
            'sms_sent': today_sms_sent,
            'sms_received': today_sms_received,
        },
        'aggregated_week': {
            'calls_total': week_calls_count,
            'duration_total_sec': week_duration_sec,
            'sms_total': week_sms_count,
        }
    }), 200
