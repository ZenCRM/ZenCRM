"""TLS-only transport with selective IMAP retrieval and sandboxed HTML."""
import base64
import hashlib
import ssl
import re
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from email.message import EmailMessage
from email.utils import getaddresses, make_msgid, parsedate_to_datetime
from html.parser import HTMLParser
from html import escape
from ..utils.mail_html import sanitize_mail_html, sanitize_signature_html
from ..utils.i18n import t
from .mailbox_imap import parse_structure, mime_parts, fetch_literal, text_part, decode_part, response_bytes
from .mailbox_transport import PublicSMTP, PublicSMTPSSL, PublicIMAP
from cryptography.fernet import Fernet
from flask import current_app
from ..extensions import db
from ..models.mailbox import MailMessage, Mailbox
from .mailbox_lock import claim_mailbox, release_mailbox, MailboxBusy


def cipher():
    secret = current_app.config.get('MAILBOX_ENCRYPTION_KEY') or current_app.config['SECRET_KEY']
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def encrypt_password(value):
    return cipher().encrypt(value.encode()).decode()


def password(box):
    return cipher().decrypt(box.password_encrypted.encode()).decode()


def smtp_connection(box):
    context = ssl.create_default_context()
    if box.smtp_security == 'ssl':
        conn = PublicSMTPSSL(box.smtp_host, box.smtp_port, timeout=20, context=context)
    else:
        conn = PublicSMTP(box.smtp_host, box.smtp_port, timeout=20)
        try:
            conn.starttls(context=context)
        except Exception:
            conn.close()
            raise
    try:
        conn.login(box.username, password(box))
    except Exception:
        conn.close()
        raise
    return conn


def imap_connection(box, deadline=None, remaining_bytes=64 * 1024 * 1024):
    conn = PublicIMAP(box.imap_host, box.imap_port, timeout=20, ssl_context=ssl.create_default_context(),
                      deadline=deadline, remaining_bytes=remaining_bytes)
    try:
        conn.login(box.username, password(box))
    except Exception:
        conn.logout()
        raise
    return conn


def test_connection(box):
    with imap_connection(box) as conn:
        if conn.select('INBOX', readonly=True)[0] != 'OK':
            raise ValueError('Nie można otworzyć skrzynki odbiorczej')
    with smtp_connection(box):
        pass


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('p', 'br', 'div', 'tr', 'li'):
            self.text.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


def message_body(msg):
    part = msg.get_body(preferencelist=('plain', 'html'))
    if not part:
        return ''
    value = part.get_content()
    if part.get_content_type() == 'text/html':
        parser = PlainHTML()
        parser.feed(value)
        value = ''.join(parser.text)
    return value[:200000]


def remote_epoch(conn):
    validity = conn.response('UIDVALIDITY')[1]
    if not validity or not validity[0]:
        raise ValueError('Serwer nie zwrócił UIDVALIDITY')
    return validity[0].decode()


def open_remote(conn, box, message, writable=False):
    if conn.select('INBOX', readonly=not writable)[0] != 'OK':
        raise ValueError('Nie można otworzyć skrzynki odbiorczej')
    epoch, _, uid = (message.remote_uid or '').partition(':')
    if not uid.isdigit() or epoch != remote_epoch(conn):
        raise ValueError('Wiadomość zmieniła identyfikator na serwerze. Zsynchronizuj skrzynkę ponownie.')
    return uid


def sync_inbox(box, all_messages=False, before_uid=None, claim_token=None):
    box_id = box.id
    owns_lease = claim_token is None
    if owns_lease:
        claim_token = claim_mailbox(box_id)
        if not claim_token:
            raise MailboxBusy()
    elif not Mailbox.query.filter_by(id=box_id, sync_claim_token=claim_token).filter(
            Mailbox.sync_claim_until > datetime.utcnow()).first():
        raise MailboxBusy()
    try:
        return _sync_inbox(box, all_messages, before_uid)
    except Exception:
        db.session.rollback()
        raise
    finally:
        if owns_lease:
            release_mailbox(box_id, claim_token)


def _sync_inbox(box, all_messages, before_uid):
    imported = skipped = processed = 0
    deadline = time.monotonic() + 60
    stack = ExitStack()
    conn = None
    remaining_bytes = 64 * 1024 * 1024

    def close_connection():
        nonlocal conn, stack, remaining_bytes
        if conn is not None:
            if isinstance(getattr(conn, 'remaining_bytes', None), int):
                remaining_bytes = min(remaining_bytes, conn.remaining_bytes)
            # A rejected literal leaves unread protocol data: never reuse it.
            try:
                conn.shutdown()
            except Exception:
                pass
        try:
            stack.close()
        except Exception:
            pass
        conn, stack = None, ExitStack()

    try:
        # Assign before selecting so an initialization failure also closes the socket.
        conn = stack.enter_context(imap_connection(box, deadline=deadline, remaining_bytes=remaining_bytes))
        conn.deadline = deadline
        if conn.select('INBOX', readonly=True)[0] != 'OK':
            raise ValueError('Nie można otworzyć skrzynki odbiorczej')
        epoch = remote_epoch(conn)
        status, data = conn.uid('search', None, 'ALL')
        if status != 'OK':
            raise ValueError('Nie udało się pobrać listy wiadomości')
        all_uids = sorted({int(v) for v in (data[0] or b'').split()})
        available = [v for v in all_uids if not before_uid or v < before_uid]
        batch = list(reversed(available[-50:])) if all_messages else available[-100:]
        for numeric_uid in batch:
            if time.monotonic() >= deadline:
                break
            uid = str(numeric_uid)
            remote_uid = epoch + ':' + uid
            record = MailMessage.query.filter_by(mailbox_id=box.id, remote_uid=remote_uid).first()
            if record and record.content_version == -1:
                skipped += 1
                processed += 1
                continue
            if conn is None:
                conn = stack.enter_context(imap_connection(box, deadline=deadline, remaining_bytes=remaining_bytes))
                conn.deadline = deadline
                if conn.select('INBOX', readonly=True)[0] != 'OK' or remote_epoch(conn) != epoch:
                    raise RuntimeError('Mailbox changed while synchronizing')
            try:
                if record and record.content_version >= 2:
                    status, flags = conn.uid('fetch', uid, '(FLAGS)')
                    if status != 'OK':
                        raise RuntimeError('Could not refresh message flags')
                    record.is_read = b'\\Seen' in response_bytes(flags)
                else:
                    is_new = record is None
                    _import_message(conn, box.id, uid, remote_uid, record)
                    imported += int(is_new)
            except (ValueError, TypeError, LookupError, IndexError, RecursionError):
                db.session.rollback()
                record = MailMessage.query.filter_by(mailbox_id=box.id, remote_uid=remote_uid).first()
                if record is None:
                    record = MailMessage(mailbox_id=box.id, remote_uid=remote_uid, sender='')
                    db.session.add(record)
                record.content_version = -1
                record.subject = t('Wiadomość pominięta ze względów bezpieczeństwa')
                record.body = t('Wiadomość przekracza limity lub ma nieprawidłowy format. Otwórz ją w swojej aplikacji pocztowej.')
                record.body_html, record.attachments = '', []
                record.is_read = True
                skipped += 1
                close_connection()
            # Each UID is durable even if a later network operation fails.
            db.session.commit()
            processed += 1
        box.uid_validity = epoch
        box.last_sync_at = datetime.utcnow()
        db.session.commit()
        completed = batch[:processed]
        return {'imported': imported, 'skipped': skipped, 'processed': processed,
                'remaining': max(0, len(available) - processed), 'total': len(all_uids),
                'next_before_uid': min(completed) if all_messages and completed and len(available) > processed else None}
    finally:
        close_connection()


def _import_message(conn, box_id, uid, remote_uid, record):
    status, payload = conn.uid('fetch', uid, '(BODYSTRUCTURE FLAGS)')
    if status != 'OK':
        raise RuntimeError('Could not fetch message structure')
    parts = mime_parts(parse_structure(payload))
    attachments = [p for p in parts if p['attachment']]
    plain, html = [], []
    text_bytes = 0
    for part in parts:
        if part['attachment']:
            continue
        if not 0 <= part['size'] <= 2 * 1024 * 1024:
            raise ValueError('Część tekstowa wiadomości przekracza 2 MB')
        value = text_part(conn, uid, part)
        text_bytes += len(value.encode('utf-8'))
        if text_bytes > 8 * 1024 * 1024:
            raise ValueError('Łączna treść tekstowa wiadomości przekracza 8 MB')
        (html if part['content_type'] == 'text/html' else plain).append(value)
    msg = BytesParser(policy=policy.default).parsebytes(fetch_literal(conn, uid, 'HEADER'))
    date = datetime.utcnow()
    try:
        date = parsedate_to_datetime(str(msg['Date'])).astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, TypeError, OverflowError):
        pass
    senders = getaddresses([str(msg.get('From', ''))])
    body_html = sanitize_mail_html('\n'.join(html))
    parser = PlainHTML()
    parser.feed(body_html)
    body = '\n'.join(plain) if plain else ''.join(parser.text)
    if record is None:
        record = MailMessage(mailbox_id=box_id, remote_uid=remote_uid)
        db.session.add(record)
    record.message_id = str(msg.get('Message-ID', ''))[:998]
    record.sender = (senders[0][1] if senders else '')[:254]
    record.recipients = [a.lower() for _, a in getaddresses([str(msg.get('To', ''))])]
    record.cc = [a.lower() for _, a in getaddresses([str(msg.get('Cc', ''))])]
    record.subject = str(msg.get('Subject', ''))[:2000]
    record.body, record.body_html = body[:1000000], body_html
    record.is_read = b'\\Seen' in response_bytes(payload)
    record.attachments, record.content_version = attachments, 2
    record.created_at = date


def download_attachment(box, message, part_id):
    attachment = next((p for p in (message.attachments or []) if p['part'] == part_id), None)
    if not attachment or not message.remote_uid:
        raise ValueError('Załącznik nie istnieje')
    if attachment['size'] > 50 * 1024 * 1024:
        raise ValueError('Załącznik przekracza limit pobierania 50 MB')
    with imap_connection(box) as conn:
        uid = open_remote(conn, box, message)
        raw = fetch_literal(conn, uid, attachment['part'], max_bytes=50 * 1024 * 1024)
    return decode_part(raw, attachment), attachment['filename']


def set_read_status(box, message, is_read):
    if message.remote_uid:
        with imap_connection(box) as conn:
            uid = open_remote(conn, box, message, writable=True)
            operation = '+FLAGS.SILENT' if is_read else '-FLAGS.SILENT'
            if conn.uid('store', uid, operation, r'(\Seen)')[0] != 'OK':
                raise ValueError('Serwer nie pozwolił zmienić statusu wiadomości')
    message.is_read = is_read
    db.session.commit()


def addresses(value):
    if not isinstance(value, str) or '\r' in value or '\n' in value:
        raise ValueError('Nieprawidłowy adres e-mail')
    parsed = [addr.lower() for _, addr in getaddresses([value])]
    if not parsed or len(parsed) > 20 or any(not re.fullmatch(r'[^\s@<>;,]+@[^\s@<>;,]+\.[^\s@<>;,]+', a) for a in parsed):
        raise ValueError('Podaj poprawne adresy odbiorców, oddzielone przecinkami')
    return parsed


def optional_addresses(value):
    return addresses(value) if value else []


def send_message(box, data):
    recipients = optional_addresses(data.get('to', ''))
    cc = optional_addresses(data.get('cc', ''))
    bcc = optional_addresses(data.get('bcc', ''))
    envelope = list(dict.fromkeys(recipients + cc + bcc))
    if not envelope or len(envelope) > 50:
        raise ValueError('Podaj od 1 do 50 odbiorców w polach Do, DW lub UDW')
    subject = str(data.get('subject', '')).strip()
    body = str(data.get('body', '')).strip()
    if not subject or (not body and not data.get('forward_message_id')) or len(subject) > 998 or len(body) > 200000 or '\n' in subject or '\r' in subject:
        raise ValueError('Podaj temat i treść wiadomości (temat do 998 znaków)')
    body_html = '<div style="white-space:pre-wrap">' + escape(body) + '</div>'
    forward_id = data.get('forward_message_id')
    if forward_id:
        original = MailMessage.query.filter_by(id=forward_id, mailbox_id=box.id).first()
        if not original:
            raise ValueError('Przekazywana wiadomość nie istnieje w tej skrzynce')
        quoted = t('Od: {sender}\nDo: {recipients}\nTemat: {subject}\n\n', {
            'sender': original.sender, 'recipients': ', '.join(original.recipients), 'subject': original.subject,
        })
        forwarded_label = t('Przekazana wiadomość')
        body += '\n\n---------- ' + forwarded_label + ' ----------\n' + quoted + original.body
        body_html += '<hr><p><strong>' + escape(forwarded_label) + '</strong></p><pre>' + escape(quoted) + '</pre>'
        body_html += sanitize_mail_html(original.body_html) if original.body_html else '<pre>' + escape(original.body) + '</pre>'
    if data.get('include_signature', True) and box.signature:
        if box.signature_format == 'html':
            signature_html = sanitize_signature_html(box.signature, fragment=True)
            parser = PlainHTML()
            parser.feed(signature_html)
            body += '\n\n-- \n' + ''.join(parser.text)
            body_html += '<br><div>' + signature_html + '</div>'
        else:
            body += '\n\n-- \n' + box.signature
            body_html += '<br><div style="white-space:pre-wrap">' + escape(box.signature) + '</div>'
    msg = EmailMessage()
    msg['From'] = box.email
    if recipients:
        msg['To'] = ', '.join(recipients)
    if cc:
        msg['Cc'] = ', '.join(cc)
    # UDW only enters the SMTP envelope; it never enters message headers.
    msg['Subject'] = subject
    msg['Message-ID'] = make_msgid()
    reply_id = data.get('reply_to_id')
    if reply_id:
        original = MailMessage.query.filter_by(id=reply_id, mailbox_id=box.id).first()
        if not original:
            raise ValueError('Wiadomość, na którą odpowiadasz, nie istnieje w tej skrzynce')
        if original.message_id and re.fullmatch(r'<[^<>\r\n]+>', original.message_id):
            msg['In-Reply-To'] = original.message_id
            msg['References'] = original.message_id
    msg.set_content(body)
    msg.add_alternative(body_html, subtype='html')
    with smtp_connection(box) as conn:
        refused = conn.send_message(msg, from_addr=box.email, to_addrs=envelope)
    record = MailMessage(mailbox_id=box.id, folder='sent', sender=box.email,
                         recipients=[r for r in recipients if r not in refused],
                         cc=[r for r in cc if r not in refused], bcc=[r for r in bcc if r not in refused],
                         subject=subject, body=body, body_html=body_html, content_version=1,
                         is_read=True, message_id=msg['Message-ID'])
    db.session.add(record)
    db.session.commit()
    return record, list(refused)
