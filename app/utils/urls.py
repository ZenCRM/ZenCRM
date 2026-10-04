"""Canonical CRM origin for public links, independent of the company website."""
import re
from urllib.parse import urlsplit
from flask import current_app
from ..models.setting import Setting


def normalize_crm_url(value):
    if not isinstance(value, str):
        raise ValueError('Podaj poprawny adres CRM, np. https://crm.twojadomena.pl.')
    value = value.strip()
    if not value:
        return ''
    if '://' not in value:
        value = 'https://' + value
    try:
        parsed = urlsplit(value)
        port = parsed.port
        valid = (parsed.scheme in ('http', 'https') and parsed.hostname
                 and not parsed.username and not parsed.password
                 and parsed.path in ('', '/') and not parsed.query and not parsed.fragment
                 and not re.search(r'''[\s\\<>"'\x00-\x1f\x7f]''', value)
                 and (port is None or 1 <= port <= 65535))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('Podaj poprawny adres CRM, np. https://crm.twojadomena.pl.')
    return f'{parsed.scheme}://{parsed.netloc}'


def public_base_url():
    value = Setting.get_value('crm_base_url', '') or current_app.config.get('PUBLIC_BASE_URL', '')
    try:
        return normalize_crm_url(value)
    except ValueError:
        return ''
