"""Strict, bounded declarations. Applications cannot register executable core code."""
import json
import re
from urllib.parse import urlsplit
from flask import current_app, has_request_context, request

SCOPES = {
    'clients.read': 'Odczyt przypisanych klientów',
    'clients.write': 'Edycja przypisanych klientów',
    'tasks.read': 'Odczyt przypisanych zadań',
    'reports.read': 'Podsumowanie dostępnych rekordów',
    'storage': 'Własne dane aplikacji',
    'app.config': 'Odczyt wspólnej konfiguracji aplikacji',
    'events.clients': 'Zdarzenia dostępnych klientów',
}
OPERATIONS = {
    'clients.list': 'clients.read', 'clients.get': 'clients.read',
    'clients.update': 'clients.write', 'tasks.list': 'tasks.read',
    'reports.summary': 'reports.read', 'storage.get': 'storage',
    'storage.put': 'storage', 'storage.delete': 'storage',
    'app.config.get': 'app.config',
}
PLACEMENTS = {'app.page', 'dashboard.widget', 'client.detail.tab'}
EVENTS = {'client.created.v1', 'client.updated.v1', 'client.archived.v1'}
IDENTIFIER = re.compile(r'^[a-z][a-z0-9-]{0,39}$')


def bounded_json(value, maximum=32768):
    try:
        raw = json.dumps(value, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, RecursionError):
        raise ValueError('Nieprawidłowe dane JSON.') from None
    if len(raw.encode('utf-8')) > maximum:
        raise ValueError('Dane aplikacji przekraczają limit rozmiaru.')
    return value


def text(value, maximum=120):
    if not isinstance(value, str) or not value.strip() or len(value) > maximum or any(ord(c) < 32 for c in value):
        raise ValueError('Nieprawidłowy tekst w definicji aplikacji.')
    return value.strip()


def https_url(value):
    text(value, 2048)
    try:
        parts = urlsplit(value)
        if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.fragment or parts.port not in (None, 443):
            raise ValueError
        if re.search(r'[\s\\]', value) or '%' in parts.netloc or parts.hostname.endswith('.'):
            raise ValueError
        # No embedded credentials, query credentials, fragments, or ambiguous host encodings.
        origin = 'https://' + parts.netloc.lower()
    except ValueError:
        raise ValueError('Adres aplikacji musi używać HTTPS na porcie 443.') from None
    base = current_app.config.get('PUBLIC_BASE_URL', '').rstrip('/')
    host = urlsplit(base).hostname if base else (urlsplit(request.host_url).hostname if has_request_context() else None)
    if host and host.lower() == parts.hostname.lower():
        raise ValueError('Interfejs aplikacji wymaga osobnej domeny.')
    return origin


def scope_list(value, allowed=None):
    allowed = set(SCOPES if allowed is None else allowed)
    if not isinstance(value, list) or not value or len(value) > 20 or any(not isinstance(s, str) or s not in allowed for s in value) or len(set(value)) != len(value):
        raise ValueError('Nieprawidłowy zakres uprawnień aplikacji.')
    return sorted(value)


def validate_manifest(value):
    bounded_json(value)
    fields = {'manifest_version', 'id', 'name', 'version', 'api_version', 'type', 'scopes',
              'placements', 'views', 'redirect_uris', 'event_url', 'description'}
    if not isinstance(value, dict) or set(value) - fields:
        raise ValueError('Nieznane pola manifestu aplikacji.')
    if type(value.get('manifest_version')) is not int or type(value.get('api_version')) is not int or value.get('manifest_version') != 1 or value.get('api_version') != 1:
        raise ValueError('Nieobsługiwana wersja API aplikacji.')
    if not isinstance(value.get('id'), str) or not IDENTIFIER.fullmatch(value['id']):
        raise ValueError('Nieprawidłowy identyfikator aplikacji.')
    kind = value.get('type')
    if kind not in ('declarative', 'remote'):
        raise ValueError('Nieobsługiwany typ aplikacji.')
    result = {**value, 'name': text(value.get('name')), 'version': text(value.get('version'), 32),
              'scopes': scope_list(value.get('scopes'))}
    if not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', result['version']):
        raise ValueError('Wersja aplikacji musi mieć format x.y.z.')
    if value.get('description'):
        result['description'] = text(value['description'], 1000)
    placements = value.get('placements', [])
    if not isinstance(placements, list) or len(placements) > 8:
        raise ValueError('Nieprawidłowe miejsca osadzenia aplikacji.')
    seen = set()
    for placement in placements:
        if not isinstance(placement, dict) or set(placement) - {'id', 'slot', 'label', 'operation', 'url'}:
            raise ValueError('Nieprawidłowe miejsce osadzenia aplikacji.')
        pid = placement.get('id')
        if not isinstance(pid, str) or not IDENTIFIER.fullmatch(pid) or pid in seen or not isinstance(placement.get('slot'), str) or placement['slot'] not in PLACEMENTS:
            raise ValueError('Nieprawidłowe miejsce osadzenia aplikacji.')
        seen.add(pid)
        text(placement.get('label'))
        if kind == 'declarative':
            operation = placement.get('operation')
            if operation not in ('reports.summary', 'clients.list', 'tasks.list') or OPERATIONS[operation] not in result['scopes'] or 'url' in placement:
                raise ValueError('Nieprawidłowa operacja widżetu.')
        else:
            if 'operation' in placement:
                raise ValueError('Nieprawidłowa operacja widżetu.')
            https_url(placement.get('url'))
    result['placements'] = placements
    views = value.get('views', [])
    if not isinstance(views, list) or len(views) > 8:
        raise ValueError('Nieprawidłowe widoki aplikacji.')
    page_ids = {p['id'] for p in placements if p['slot'] == 'app.page'}
    seen_views = set()
    for view in views:
        if not isinstance(view, dict) or set(view) != {'id', 'label', 'placement'}:
            raise ValueError('Nieprawidłowe widoki aplikacji.')
        vid, placement = view['id'], view['placement']
        if not isinstance(vid, str) or not IDENTIFIER.fullmatch(vid) or vid in seen_views or not isinstance(placement, str) or placement not in page_ids:
            raise ValueError('Widok wymaga unikalnego identyfikatora i miejsca app.page.')
        text(view['label'])
        seen_views.add(vid)
    redirects = value.get('redirect_uris', [])
    if not isinstance(redirects, list) or len(redirects) > 5 or any(not isinstance(url, str) for url in redirects) or len(set(redirects)) != len(redirects):
        raise ValueError('Nieprawidłowe adresy powrotu aplikacji.')
    for url in redirects:
        https_url(url)
        if urlsplit(url).query:
            raise ValueError('Adres powrotu nie może zawierać parametrów.')
    result['redirect_uris'] = redirects
    if value.get('event_url'):
        if kind != 'remote' or not {'clients.read', 'events.clients'} <= set(result['scopes']):
            raise ValueError('Zdarzenia wymagają odczytu klientów i aplikacji zewnętrznej.')
        https_url(value['event_url'])
        if urlsplit(value['event_url']).query:
            raise ValueError('Adres zdarzeń nie może zawierać parametrów.')
    return result
