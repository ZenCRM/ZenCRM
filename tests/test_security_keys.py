import tempfile
import unittest
from flask import Flask
from app.utils.security_keys import configure_secrets


class SecurityKeysTest(unittest.TestCase):
    def test_default_keys_are_random_persistent_and_distinct(self):
        with tempfile.TemporaryDirectory() as directory:
            apps = [Flask(__name__, instance_path=directory) for _ in range(2)]
            for app in apps:
                app.config.update(SECRET_KEY='dev-secret', JWT_SECRET_KEY='jwt-dev-secret')
                configure_secrets(app)
            for key in ('SECRET_KEY', 'JWT_SECRET_KEY'):
                self.assertEqual(apps[0].config[key], apps[1].config[key])
                self.assertEqual(len(apps[0].config[key]), 64)
            self.assertNotEqual(apps[0].config['SECRET_KEY'], apps[0].config['JWT_SECRET_KEY'])

    def test_explicit_keys_are_preserved(self):
        app = Flask(__name__)
        app.config.update(SECRET_KEY='a' * 32, JWT_SECRET_KEY='b' * 32)
        configure_secrets(app)
        self.assertEqual(app.config['SECRET_KEY'], 'a' * 32)
        self.assertEqual(app.config['JWT_SECRET_KEY'], 'b' * 32)

    def test_explicit_mailbox_key_must_be_strong(self):
        app = Flask(__name__)
        app.config.update(SECRET_KEY='a' * 32, JWT_SECRET_KEY='b' * 32, MAILBOX_ENCRYPTION_KEY='short')
        with self.assertRaises(RuntimeError):
            configure_secrets(app)
        app.config['MAILBOX_ENCRYPTION_KEY'] = 'c' * 32
        configure_secrets(app)
        self.assertEqual(app.config['MAILBOX_ENCRYPTION_KEY'], 'c' * 32)
