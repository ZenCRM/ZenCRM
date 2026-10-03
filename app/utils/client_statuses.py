import json
import re
from ..models.setting import Setting
from ..models.client import Client

DEFAULT_STATUSES = [
    {'id': 'active', 'label': 'Aktywny', 'accent': '#16a34a'},
    {'id': 'inactive', 'label': 'Nieaktywny', 'accent': '#64748b'},
    {'id': 'prospect', 'label': 'Potencjalny', 'accent': '#ca8a04'},
]


def get_statuses():
    try:
        return json.loads(Setting.get_value('client_statuses', 'null')) or DEFAULT_STATUSES
    except (ValueError, TypeError):
        return DEFAULT_STATUSES


def validate_statuses(statuses):
    if not isinstance(statuses, list) or not 1 <= len(statuses) <= 20:
        raise ValueError('Ustaw od 1 do 20 statusów klientów.')
    clean = []
    for status in statuses:
        if not isinstance(status, dict):
            raise ValueError('Nieprawidłowy status klienta.')
        key, label, color = status.get('id'), status.get('label'), status.get('accent')
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,19}', key):
            raise ValueError('Identyfikator statusu: do 20 małych liter, cyfr lub znaków podkreślenia.')
        if not isinstance(label, str) or not 1 <= len(label.strip()) <= 60:
            raise ValueError('Nazwa statusu musi mieć od 1 do 60 znaków.')
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('Wybierz poprawny kolor statusu.')
        clean.append({'id': key, 'label': label.strip(), 'accent': color})
    ids = {s['id'] for s in clean}
    if len(ids) != len(clean):
        raise ValueError('Statusy muszą mieć unikalne identyfikatory.')
    used = {s for (s,) in Client.query.with_entities(Client.status).distinct().all() if s}
    if used - ids:
        raise ValueError('Przenieś klientów z usuwanego statusu do innego statusu (także w archiwum).')
    return clean


def default_status(preferred='active'):
    statuses = get_statuses()
    return preferred if any(s['id'] == preferred for s in statuses) else statuses[0]['id']
