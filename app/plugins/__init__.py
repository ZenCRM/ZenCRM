"""Optional applications with explicit user consent and isolated execution."""


def init_plugins(app):
    from . import models  # Register metadata before schema preparation.
    from .api import plugins_bp
    from .integration_api import integration_bp
    app.register_blueprint(plugins_bp, url_prefix='/api/plugins')
    app.register_blueprint(integration_bp, url_prefix='/api/plugin-api/v1')
    # Definitions live in the database. Never mutate process-global core registries.
    app.extensions['plugins'] = {'api_version': 1}
