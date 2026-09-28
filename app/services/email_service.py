import logging
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from ..models.setting import Setting
from ..models.email_template import EmailTemplate

logger = logging.getLogger('zencrm.emails')


def get_smtp_config():
    """Pobiera konfigurację serwera SMTP z bazy settings."""
    return {
        'enabled': Setting.get_value('smtp_enabled', 'false') == 'true',
        'host': (Setting.get_value('smtp_host', '') or '').strip(),
        'port': int(Setting.get_value('smtp_port', '587') or 587),
        'user': (Setting.get_value('smtp_user', '') or '').strip(),
        'password': (Setting.get_value('smtp_password', '') or '').strip(),
        'from_email': (Setting.get_value('smtp_from_email', '') or '').strip() or 'powiadomienia@zencrm.pl',
        'from_name': (Setting.get_value('smtp_from_name', '') or '').strip() or Setting.get_value('brand_name', 'ZenCRM'),
        'encryption': (Setting.get_value('smtp_encryption', 'tls') or 'tls').strip().lower(),
    }


def send_email(to_email, subject, body_html, to_name=None):
    """
    Wysyła wiadomość e-mail. Jeśli SMTP jest wyłączone lub nieskonfigurowane,
    zapisuje log i bezpiecznie zwraca True (aby nie przerywać procesów CRM).
    """
    if not to_email or '@' not in to_email:
        logger.warning(f"Nieprawidłowy adres e-mail odbiorcy: {to_email}")
        return False, "Nieprawidłowy adres e-mail"

    cfg = get_smtp_config()

    if not cfg['enabled'] or not cfg['host']:
        logger.info(f"[E-MAIL SYMULACJA / SMTP WYŁĄCZONE] Do: {to_email} | Temat: {subject}")
        return True, "Zalogowano powiadomienie (SMTP wyłączone)"

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        from_display = str(Header(cfg['from_name'], 'utf-8'))
        msg['From'] = formataddr((from_display, cfg['from_email']))
        to_display = str(Header(to_name or to_email, 'utf-8'))
        msg['To'] = formataddr((to_display, to_email))

        # Plain text fallback
        import re
        plain_text = re.sub(r'<[^>]+>', ' ', body_html).strip()
        part1 = MIMEText(plain_text, 'plain', 'utf-8')
        part2 = MIMEText(body_html, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)

        port = cfg['port']
        encryption = cfg['encryption']

        if encryption == 'ssl' or port == 465:
            server = smtplib.SMTP_SSL(cfg['host'], port, timeout=10)
        else:
            server = smtplib.SMTP(cfg['host'], port, timeout=10)
            if encryption == 'tls':
                server.starttls()

        if cfg['user'] and cfg['password']:
            server.login(cfg['user'], cfg['password'])

        server.sendmail(cfg['from_email'], [to_email], msg.as_string())
        server.quit()
        logger.info(f"Wysłano e-mail do {to_email}: {subject}")
        return True, "Wysłano pomyślnie"
    except Exception as e:
        logger.error(f"Błąd wysyłania e-maila do {to_email}: {e}")
        return False, str(e)


def render_template(template_key, context):
    """Renderuje szablon e-mail podstawiając zmienne {{zmienna}}."""
    tpl = EmailTemplate.get_by_key(template_key)
    if not tpl:
        # Fallback na wypadek braku wpisu w bazie
        from ..models.email_template import DEFAULT_TEMPLATES
        fallback = next((t for t in DEFAULT_TEMPLATES if t['key'] == template_key), None)
        if not fallback:
            return f"Powiadomienie ZenCRM", "<p>Powiadomienie z systemu ZenCRM.</p>"
        subject = fallback['subject']
        body_html = fallback['body_html']
    else:
        subject = tpl.subject
        body_html = tpl.body_html

    # Domyślne zmienne globalne
    company_name = Setting.get_value('company_name', Setting.get_value('brand_name', 'ZenCRM'))
    company_email = Setting.get_value('company_email', 'kontakt@zencrm.pl')
    logo_path = Setting.get_value('brand_logo_light', '') or Setting.get_value('helpdesk_logo', '') or '/logo.png'

    base_url = (Setting.get_value('company_www', '') or '').strip()
    if base_url and not base_url.startswith('http'):
        base_url = 'https://' + base_url
    if not base_url:
        try:
            from flask import request
            if request and hasattr(request, 'host_url'):
                base_url = request.host_url.rstrip('/')
        except Exception:
            base_url = ''

    if logo_path.startswith('http'):
        company_logo_url = logo_path
    elif base_url:
        company_logo_url = f"{base_url.rstrip('/')}/{logo_path.lstrip('/')}"
    else:
        company_logo_url = logo_path

    logo_img_tag = f'<img src="{company_logo_url}" alt="{company_name}" style="max-height: 48px; max-width: 220px; object-fit: contain; display: inline-block;" />'
    logo_header = f'<div style="text-align: left; margin-bottom: 24px; padding-bottom: 16px; border-bottom: 1px solid #e5e7eb;">{logo_img_tag}</div>'

    ctx = {
        'company_name': company_name,
        'company_email': company_email,
        'company_logo': logo_img_tag,
        'company_logo_url': company_logo_url,
        **context
    }

    # Jeśli szablon nie ma {{company_logo}} ani <img, wstawiamy nagłówek z logo
    if '{{company_logo}}' not in body_html and '<img' not in body_html:
        first_gt = body_html.find('>')
        if first_gt != -1 and body_html.strip().startswith('<div'):
            body_html = body_html[:first_gt+1] + logo_header + body_html[first_gt+1:]
        else:
            body_html = logo_header + body_html

    for key, val in ctx.items():
        placeholder = f"{{{{{key}}}}}"
        str_val = str(val if val is not None else '')
        subject = subject.replace(placeholder, str_val)
        body_html = body_html.replace(placeholder, str_val)

    return subject, body_html


def send_notification(template_key, recipient_email, context, user=None, recipient_name=None):
    """
    Wysyła powiadomienie na podstawie klucza szablonu.
    Jeśli podano użytkownika (user), sprawdza jego preferencje can_receive_email(template_key).
    """
    if user:
        # Mapowanie szablonu na klucz preferencji użytkownika
        pref_key_map = {
            'employee_new_ticket': 'ticket_assigned',
            'employee_ticket_reply': 'ticket_reply',
            'employee_new_task': 'task_assigned',
            'employee_client_assigned': 'client_assigned',
        }
        pref_key = pref_key_map.get(template_key, template_key)
        if not user.can_receive_email(pref_key):
            logger.info(f"Pominięto wysyłkę {template_key} do {user.email} (wyłączone w preferencjach)")
            return False, "Wyłączone w preferencjach użytkownika"
        if not recipient_email:
            recipient_email = user.email
        if not recipient_name:
            recipient_name = f"{user.first_name} {user.last_name}".strip()

    if not recipient_email:
        return False, "Brak adresu e-mail odbiorcy"

    subject, body_html = render_template(template_key, context)
    return send_email(recipient_email, subject, body_html, to_name=recipient_name)


def test_smtp_connection(cfg, test_recipient):
    """Testuje połączenie SMTP wysyłając próbny e-mail."""
    if not test_recipient or '@' not in test_recipient:
        return False, "Podaj poprawny adres e-mail do testu"

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header("ZenCRM - Test konfiguracji SMTP", 'utf-8')
        from_display = str(Header(cfg.get('from_name') or 'ZenCRM Test', 'utf-8'))
        msg['From'] = formataddr((from_display, cfg.get('from_email') or 'test@zencrm.pl'))
        msg['To'] = test_recipient

        html = (
            "<div style='font-family: Arial, sans-serif; padding: 20px; color: #1f2937;'>"
            "<h2 style='color: #10b981;'>Konfiguracja SMTP działa poprawnie!</h2>"
            "<p>To jest testowa wiadomość potwierdzająca prawidłowe ustawienia serwera poczty wychodzącej w ZenCRM.</p>"
            "<p style='color: #6b7280; font-size: 12px;'>Data testu: " + datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC') + "</p>"
            "</div>"
        )
        msg.attach(MIMEText(html, 'html', 'utf-8'))

        port = int(cfg.get('port') or 587)
        encryption = (cfg.get('encryption') or 'tls').lower()

        if encryption == 'ssl' or port == 465:
            server = smtplib.SMTP_SSL(cfg['host'], port, timeout=10)
        else:
            server = smtplib.SMTP(cfg['host'], port, timeout=10)
            if encryption == 'tls':
                server.starttls()

        if cfg.get('user') and cfg.get('password'):
            server.login(cfg['user'], cfg['password'])

        server.sendmail(cfg.get('from_email') or 'test@zencrm.pl', [test_recipient], msg.as_string())
        server.quit()
        return True, "Wiadomość testowa została wysłana pomyślnie!"
    except Exception as e:
        return False, f"Błąd połączenia SMTP: {str(e)}"
