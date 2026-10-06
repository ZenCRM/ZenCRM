import mimetypes
import os
import sys
from pathlib import Path

# Slim images ship no /etc/mime.types and Python 3.11 has no built-in WebP type;
# without it the hero images would be served as application/octet-stream under nosniff.
mimetypes.add_type('image/webp', '.webp')

# Ensure project venv site-packages are accessible even if run from another Python interpreter
_proj_root = Path(__file__).resolve().parent.parent
_venv_lib = _proj_root / 'venv' / ('Lib' if os.name == 'nt' else 'lib')
if _venv_lib.is_dir():
    for _sp in _venv_lib.glob('**/site-packages'):
        if _sp.is_dir() and str(_sp) not in sys.path:
            sys.path.insert(0, str(_sp))

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix
try:
    from flask_cors import CORS
except ImportError:
    class CORS:
        def __init__(self, *args, **kwargs):
            pass

from .extensions import db, migrate, jwt, ma
from .config import Config


def create_app(config_class=Config):
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='', template_folder=frontend_dir)
    app.config.from_object(config_class)
    proxy_hops = app.config.get('TRUSTED_PROXY_HOPS', 0)
    if proxy_hops:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=proxy_hops, x_proto=proxy_hops, x_host=proxy_hops)
    from .utils.security_keys import configure_secrets
    configure_secrets(app)
    from .utils.i18n import init_i18n
    init_i18n(app)
    # Distinct delimiters preserve the Jinja examples in the document editor.
    app.jinja_env.block_start_string = '<%'
    app.jinja_env.block_end_string = '%>'
    app.jinja_env.variable_start_string = '[['
    app.jinja_env.variable_end_string = ']]'

    db.init_app(app)
    from .database import MIGRATIONS_DIR
    migrate.init_app(app, db, directory=MIGRATIONS_DIR, render_as_batch=True)
    jwt.init_app(app)
    ma.init_app(app)
    from .utils.api_security import init_api_security
    init_api_security(app)
    if app.config.get('CORS_ORIGINS'):
        CORS(app, resources={r'/api/*': {'origins': app.config['CORS_ORIGINS']}})
    else:
        CORS(app, resources={r'/api/*': {'origins': '*'}})

    from .bootstrap.routes import register_api
    from .bootstrap.frontend import register_frontend
    from .bootstrap.database import initialize_database

    register_api(app)
    from .plugins import init_plugins
    init_plugins(app)
    register_frontend(app, frontend_dir)
    initialize_database(app)

    from .services.push_service import start_push_worker
    start_push_worker(app)
    from .services.mailbox_worker import start_mail_worker
    start_mail_worker(app)

    return app
