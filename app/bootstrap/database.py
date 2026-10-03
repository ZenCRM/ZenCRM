"""Prepare the versioned schema and seed defaults during application startup."""
from ..database import prepare_database


def initialize_database(app):
    if app.config.get('PREPARE_DATABASE', True):
        with app.app_context():
            prepare_database()
