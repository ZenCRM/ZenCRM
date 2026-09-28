from urllib.parse import urlsplit
from ..extensions import db
from ..models.workspace import PortalConfiguration

MODULES = ('document', 'offer', 'ticket', 'service', 'info')
DEFAULTS = {'address': '/portal.html', 'logo': '', 'login_background': '',
            'enabled': True, 'modules': list(MODULES)}


def portal_settings():
    row = db.session.get(PortalConfiguration, 1)
    return {**DEFAULTS, **(row.data if row else {})}


def portal_path():
    return urlsplit(portal_settings()['address']).path.rstrip('/') or '/portal.html'
