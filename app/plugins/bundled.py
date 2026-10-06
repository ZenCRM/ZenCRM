"""Reviewed, local applications. No downloads, executable packages or implicit grants."""
from copy import deepcopy

ALL_USERS = 'all-active-users'


def definition(app_id, name, description, scope, operation, category, badge, dashboard=False):
    placements = [{'id': 'main', 'slot': 'app.page', 'label': name, 'operation': operation}]
    if dashboard:
        placements.append({'id': 'dashboard', 'slot': 'dashboard.widget', 'label': name, 'operation': operation})
    return {'manifest': {'manifest_version': 1, 'api_version': 1, 'id': app_id, 'name': name,
                         'description': description, 'version': '1.0.0', 'type': 'declarative',
                         'scopes': [scope], 'placements': placements, 'redirect_uris': []},
            'category': category, 'badge': badge}


BUNDLED = {
    item['manifest']['id']: item for item in [
        definition('zencrm-google-drive', 'Google Drive',
                   'Połącz konto Google, zapisuj pliki i raporty w folderze ZenCRM oraz otwieraj je na Dysku Google. Dostęp tylko do plików tej integracji.',
                   'drive.files', 'drive.status', 'Integracje', 'GD'),
        definition('zencrm-report-studio', 'Studio raportów',
                   'Twórz raporty klientów i zadań, analizuj statusy, priorytety i zaległości. Filtruj okres i eksportuj wyniki do CSV.',
                   'reports.read', 'reports.aggregate', 'Raporty', 'SR'),
        definition('zencrm-work-summary', 'Podsumowanie pracy',
                   'Liczba dostępnych klientów i otwartych zadań. Podsumowanie także na pulpicie.',
                   'reports.read', 'reports.summary', 'Raporty', 'RP', True),
        definition('zencrm-client-directory', 'Katalog klientów',
                   'Podręczna lista klientów, do których masz dostęp, z nazwą firmy i statusem.',
                   'clients.read', 'clients.list', 'Sprzedaż', 'KL'),
        definition('zencrm-task-list', 'Lista zadań',
                   'Lista przypisanych zadań z aktualnym statusem, zawsze w granicach Twoich uprawnień.',
                   'tasks.read', 'tasks.list', 'Organizacja pracy', 'ZA'),
    ]
}


def bundled_metadata(app):
    item = BUNDLED.get(app.id)
    # An ID alone never establishes trust or grants access to all users.
    if item and app.manifest == item['manifest']:
        return {'bundled': True, 'publisher': 'ZenCRM', 'category': item['category'], 'badge': item['badge']}
    return {'bundled': False, 'category': 'Integracje', 'badge': 'AP'}


def seed_bundled():
    """Run inside the database startup lock. Preserve all administrator decisions on restart."""
    from ..extensions import db
    from .models import PluginApp
    for app_id, item in BUNDLED.items():
        if db.session.get(PluginApp, app_id) is None:
            manifest = deepcopy(item['manifest'])
            db.session.add(PluginApp(id=app_id, manifest=manifest, installed=True, enabled=True,
                                    approved_scopes=manifest['scopes'][:], allowed_users=[ALL_USERS]))
    db.session.commit()
