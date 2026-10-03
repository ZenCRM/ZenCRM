"""Compatibility baseline captured from release 0.9.0.4 before refactoring."""
import json
from pathlib import Path
import unittest

from app import create_app
from app.config import Config
from app.extensions import db
from app.utils.api_security import PUBLIC, TOKEN_HANDLERS, PORTAL_HANDLERS
from app.utils.permissions import ENDPOINT_ACTIONS


class ContractConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    PUSH_ENABLED = False


def capture_contract():
    app = create_app(ContractConfig)
    with app.app_context():
        inspector = db.inspect(db.engine)
        schema = {
            table: {
                'columns': [
                    {key: str(column[key]) if key == 'type' else column[key]
                     for key in ('name', 'type', 'nullable', 'default', 'primary_key')}
                    for column in inspector.get_columns(table)
                ],
                'foreign_keys': inspector.get_foreign_keys(table),
                'unique_constraints': inspector.get_unique_constraints(table),
            }
            for table in sorted(inspector.get_table_names())
        }
        db.session.remove()
        db.engine.dispose()
    return {
        'routes': sorted([
            {'path': rule.rule, 'endpoint': rule.endpoint, 'methods': sorted(rule.methods)}
            for rule in app.url_map.iter_rules()
        ], key=lambda rule: (rule['path'], rule['endpoint'])),
        'before_request': [fn.__name__ for fn in app.before_request_funcs.get(None, [])],
        'after_request': [fn.__name__ for fn in app.after_request_funcs.get(None, [])],
        'public': {key: sorted(value) for key, value in sorted(PUBLIC.items())},
        'token_handlers': sorted(TOKEN_HANDLERS),
        'portal_handlers': sorted(PORTAL_HANDLERS),
        'permissions': dict(sorted(ENDPOINT_ACTIONS.items())),
        'schema': schema,
    }


class AppContractTests(unittest.TestCase):
    def test_release_contract_is_preserved(self):
        expected = json.loads(Path(__file__).with_name('fixtures').joinpath('app_contract.json').read_text())
        actual = capture_contract()
        for section in expected:
            with self.subTest(section=section):
                self.assertEqual(actual[section], expected[section])

    def test_repeated_factory_calls_preserve_registration(self):
        self.assertEqual(capture_contract(), capture_contract())
