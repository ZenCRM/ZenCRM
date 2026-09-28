import json
import secrets
from urllib.parse import urlsplit
from ..extensions import db
from ..models.setting import Setting

DEFAULT_HELPDESK_CATEGORIES = [
    {'id': 'technical', 'name': 'Pomoc techniczna'},
    {'id': 'billing', 'name': 'Rozliczenia i faktury'},
    {'id': 'bug', 'name': 'Zgłoszenie błędu'},
    {'id': 'general', 'name': 'Zapytanie ogólne'}
]

DEFAULT_HELPDESK_CONFIG = {
    'helpdesk_enabled': True,
    'helpdesk_path': '/pomoc',
    'helpdesk_title': 'Centrum Pomocy',
    'helpdesk_header_subtitle': 'Wsparcie i obsługa zgłoszeń',
    'helpdesk_badge': 'Zgłoszenie serwisowe',
    'helpdesk_heading': 'W czym możemy Ci pomóc?',
    'helpdesk_description': 'Wypełnij poniższy formularz. Otrzymasz unikalny link do śledzenia statusu zgłoszenia oraz powiadomienie e-mail.',
    'helpdesk_success_heading': 'Zgłoszenie zostało wysłane!',
    'helpdesk_success_description': 'Wysłaliśmy potwierdzenie na Twój adres e-mail wraz z bezpośrednim linkiem do śledzenia statusu zgłoszenia.',
    'helpdesk_footer_text': 'Obsługa klienta · Bezpieczny portal pomocy',
    'helpdesk_logo': '',
    'helpdesk_accent_color': '#018bfc',
    'helpdesk_categories': DEFAULT_HELPDESK_CATEGORIES,
    'helpdesk_auto_assign': True,
    'helpdesk_auto_assign_target': 'team',  # 'team' lub 'user'
    'helpdesk_default_team_id': None,
    'helpdesk_default_user_id': None,
    'helpdesk_webhook_enabled': True,
    'helpdesk_webhook_token': '',
}


def get_helpdesk_config():
    config = dict(DEFAULT_HELPDESK_CONFIG)
    keys = list(DEFAULT_HELPDESK_CONFIG.keys())
    settings = Setting.query.filter(Setting.key.in_(keys)).all()
    settings_dict = {s.key: s.value for s in settings}

    for k in keys:
        if k in settings_dict:
            raw = settings_dict[k]
            if k in ('helpdesk_enabled', 'helpdesk_auto_assign', 'helpdesk_webhook_enabled'):
                config[k] = (str(raw).lower() in ('true', '1', 'yes'))
            elif k == 'helpdesk_categories':
                try:
                    parsed = json.loads(raw) if isinstance(raw, str) else raw
                    config[k] = parsed if isinstance(parsed, list) else DEFAULT_HELPDESK_CATEGORIES
                except Exception:
                    config[k] = DEFAULT_HELPDESK_CATEGORIES
            elif k in ('helpdesk_default_team_id', 'helpdesk_default_user_id'):
                try:
                    config[k] = int(raw) if raw not in (None, '', 'null') else None
                except Exception:
                    config[k] = None
            else:
                config[k] = raw

    if not config.get('helpdesk_webhook_token'):
        token = secrets.token_hex(20)
        config['helpdesk_webhook_token'] = token
        save_helpdesk_config({'helpdesk_webhook_token': token})

    return config


def save_helpdesk_config(data):
    for k, v in data.items():
        if k in DEFAULT_HELPDESK_CONFIG:
            s = Setting.query.filter_by(key=k).first()
            if not s:
                s = Setting(key=k)
                db.session.add(s)
            if isinstance(v, (dict, list)):
                s.value = json.dumps(v, ensure_ascii=False)
            elif isinstance(v, bool):
                s.value = 'true' if v else 'false'
            elif v is None:
                s.value = ''
            else:
                s.value = str(v)
    db.session.commit()
    return get_helpdesk_config()


def helpdesk_path():
    path = get_helpdesk_config().get('helpdesk_path', '/pomoc')
    return urlsplit(path).path.rstrip('/') or '/pomoc'
