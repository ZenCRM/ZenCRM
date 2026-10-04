"""Compatibility baseline captured from release 0.9.0.4 before refactoring."""
import json
import re
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
                # Reflection order is not a semantic part of the schema (batch
                # migrations can rebuild unnamed constraints in either order).
                'foreign_keys': sorted(inspector.get_foreign_keys(table),
                                       key=lambda fk: tuple(fk['constrained_columns'])),
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

    def test_rendered_page_serves_all_component_scripts(self):
        app = create_app(ContractConfig)
        try:
            client = app.test_client()
            response = client.get('/')
            self.assertEqual(response.status_code, 200)
            scripts = re.findall(r'<script[^>]+src="(/js/[^\"]+)"', response.get_data(as_text=True))
            self.assertTrue(scripts)
            for script in scripts:
                with self.subTest(script=script):
                    with client.get(script) as result:
                        self.assertEqual(result.status_code, 200)
                        self.assertIn(result.mimetype, ('text/javascript', 'application/javascript'))
        finally:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
