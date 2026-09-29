"""Request localization using the same catalogs as the browser.

Only system messages are passed here, never record names or user content.
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from flask import has_request_context, request


@lru_cache(maxsize=4)
def catalog(locale):
    try:
        source = (Path(__file__).resolve().parents[2] / 'frontend' / 'locales' / f'{locale}.js').read_text(encoding='utf-8')
        start = source.index('{', source.index('window.ZenLocales.'))
        raw_json = source[start:source.rfind('}') + 1]
        # Remove trailing commas before closing braces/brackets to allow flexible JS objects
        cleaned = re.sub(r',\s*([}\]])', r'\1', raw_json)
        return json.loads(cleaned)
    except Exception:
        try:
            return json.loads(raw_json)
        except Exception:
            return {}


def browser_catalogs():
    from ..models.translation import TranslationLanguage, TranslationEntry
    languages = {'pl': {'name': 'Polski', 'base': 'pl'}, 'en': {'name': 'English', 'base': 'en'}}
    for row in TranslationLanguage.query.all():
        languages[row.code] = {'name': row.name, 'base': row.base_locale}
    overrides = {}
    for row in TranslationEntry.query.all():
        overrides.setdefault(row.locale, {})[row.key] = row.value
    return {'languages': languages, 'overrides': overrides}


def language():
    if not has_request_context():
        return 'pl'
    from ..models.translation import TranslationLanguage
    codes = ['pl', 'en'] + [row.code for row in TranslationLanguage.query.all()]
    return request.accept_languages.best_match(codes) or 'pl'


def t(key, params=None, locale=None):
    if not isinstance(key, str):
        return key
    try:
        from ..models.translation import TranslationLanguage, TranslationEntry
        selected = locale or language()
        custom = TranslationEntry.query.filter_by(locale=selected, key=key).first()
        base = TranslationLanguage.query.filter_by(code=selected).first()
        fallback = base.base_locale if base else selected
        cat = catalog(fallback)
        inherited = TranslationEntry.query.filter_by(locale=fallback, key=key).first() if fallback != selected else None
        result = custom.value if custom else inherited.value if inherited else cat.get(key, catalog('pl').get(key, key))
    except Exception:
        result = key
    return re.sub(r'\{([^{}]+)\}', lambda match: str(params[match[1]]) if params and match[1] in params else match[0], result)


def default_email(template_key, field, value):
    """Translate only a pristine bundled template, before inserting user values."""
    from ..models.email_template import DEFAULT_TEMPLATES
    default = next((row for row in DEFAULT_TEMPLATES if row['key'] == template_key), None)
    if not default or value != default.get(field):
        return value
    if field != 'body_html':
        return t(value)

    def replace(match):
        text = match[1]
        key = text.strip()
        return '>' + text.replace(key, t(key), 1) + '<' if key else match[0]
    return re.sub(r'>([^<>]+)<', replace, value)


def activity_text(description, action, meta=None):
    """Localize system prefixes in persisted history, preserving the user suffix.

    Existing activity rows predate i18n. These prefixes are emitted by CRM event
    writers; free-form descriptions are returned unchanged.
    """
    if not description:
        return description
    prefixes = {
        'created': ['Utworzono klienta: ', 'Utworzono lead: ', 'Utworzono dokument: ', 'Utworzono ofertę: ', 'Utworzony z leada: '],
        'deleted': ['Przeniesiono do archiwum: '],
        'archived': ['Przeniesiono klienta do archiwum: '],
        'restored': ['Przywrócono z archiwum: '],
        'converted': ['Przekonwertowano na klienta: '],
        'contact_added': ['Dodano kontakt: '],
    }
    for prefix in prefixes.get(action, []):
        if description.startswith(prefix):
            return t(prefix + '{name}', {'name': description[len(prefix):]})
    if action in ('comment', 'call', 'email'):
        match = re.match(r'^(Notatka|Telefon|E-mail)(?: · (odebrane|nieodebrane|wychodzący|przychodzący))?: ([\s\S]*)$', description)
        if match:
            key = '{kind} · {status}: {content}' if match[2] else '{kind}: {content}'
            return t(key, {'kind': t(match[1]), 'status': t(match[2]), 'content': match[3]})
    if action == 'sms':
        for prefix in ('Odebrano SMS od: ', 'Wysłano SMS do: '):
            if description.startswith(prefix):
                return t(prefix + '{contact}{snippet}', {'contact': description[len(prefix):], 'snippet': ''})
    if action == 'call':
        match = re.match(r'^(Połączenie przychodzące|Połączenie wychodzące|Nieodebrane połączenie|Odrzucone połączenie|Połączenie telefoniczne): ([\s\S]*)$', description)
        if match:
            suffix = match[2]
            caller = (meta or {}).get('caller_name')
            ending = f' [zlecone przez: {caller}]' if caller else ''
            if ending and suffix.endswith(ending):
                suffix = suffix[:-len(ending)] + t(' [zlecone przez: {name}]', {'name': caller})
            return t('{kind}: {contact}{duration}{caller}', {'kind': t(match[1]), 'contact': suffix, 'duration': '', 'caller': ''})
        if description.startswith('Zlecono połączenie z telefonu (') and meta:
            caller = t(' przez: {name}', {'name': meta['caller_name']}) if meta.get('caller_name') else ''
            return t('Zlecono połączenie z telefonu ({device}) na numer {phone}{caller}', {'device': meta.get('device_name', ''), 'phone': meta.get('phone', ''), 'caller': caller})
    system_events = {'Utworzono', 'Zaktualizowano', 'Zaktualizowano lead', 'Zmieniono zespół',
                     'Utworzono projekt', 'Zaktualizowano projekt', 'Usunięto projekt'}
    return t(description) if description in system_events else description


def init_i18n(app):
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(HTTPException)
    def localized_http_error(error):
        if not request.path.startswith('/api/'):
            return error
        defaults = {400: 'Żądanie jest nieprawidłowe.', 401: 'Wymagane logowanie.',
                    403: 'Brak dostępu', 404: 'Nie znaleziono zasobu.',
                    405: 'Ta operacja nie jest dozwolona.'}
        description = error.description
        if description == type(error).description:
            description = defaults.get(error.code, 'Wystąpił błąd serwera.')
        response = error.get_response()
        response.data = app.json.dumps({'error': t(description)})
        response.content_type = 'application/json'
        return response

    @app.after_request
    def translate_api_messages(response):
        if request.path.startswith('/api/') and response.is_json:
            data = response.get_json(silent=True)
            if isinstance(data, dict):
                changed = False
                # A model (e.g. SmsTask) can also have a user-authored `message`.
                # Only success envelopes and message-only responses contain copy.
                fields = ['error']
                if data.get('ok') is True or data.get('success') is True or set(data) == {'message'}:
                    fields.append('message')
                for field in fields:
                    if isinstance(data.get(field), str):
                        value = t(data[field])
                        changed |= value != data[field]
                        data[field] = value
                if changed:
                    response.set_data(app.json.dumps(data))
                response.vary.add('Accept-Language')
        return response
