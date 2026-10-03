import io
import unittest
from contextlib import redirect_stdout
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User
from seed import seed_admin


class InitialSetupTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            PUSH_ENABLED = False
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_seed_admin_initializes_db_without_hardcoded_user(self):
        with redirect_stdout(io.StringIO()) as output:
            self.assertTrue(seed_admin())
        self.assertEqual(User.query.count(), 0)
        self.assertIn('Nowa instalacja', output.getvalue())

    def test_setup_status_and_public_settings_on_empty_db(self):
        seed_admin()
        status_res = self.client.get('/api/auth/setup-status')
        self.assertEqual(status_res.status_code, 200)
        self.assertTrue(status_res.json['needs_setup'])
        self.assertFalse(status_res.json['has_users'])

        settings_res = self.client.get('/api/settings/public')
        self.assertEqual(settings_res.status_code, 200)
        self.assertTrue(settings_res.json['needs_setup'])

    def test_setup_admin_flow_and_lockdown(self):
        seed_admin()

        # Invalid email
        res = self.client.post('/api/auth/setup', json={'email': 'invalid', 'password': 'password123'})
        self.assertEqual(res.status_code, 400)

        # Short password
        res = self.client.post('/api/auth/setup', json={'email': 'admin@firma.pl', 'password': 'short'})
        self.assertEqual(res.status_code, 400)

        # Successful setup
        setup_payload = {
            'first_name': 'Jan',
            'last_name': 'Kowalski',
            'email': 'admin@firma.pl',
            'password': 'StrongPassword123'
        }
        res = self.client.post('/api/auth/setup', json=setup_payload)
        self.assertEqual(res.status_code, 201)
        self.assertTrue(res.json['ok'])
        self.assertIn('access_token', res.json)
        self.assertEqual(res.json['user']['email'], 'admin@firma.pl')
        self.assertEqual(res.json['user']['role'], 'admin')

        # User is saved and active in DB
        user = User.query.one()
        self.assertEqual(user.email, 'admin@firma.pl')
        self.assertEqual(user.role, 'admin')
        self.assertTrue(user.is_active)
        self.assertTrue(user.check_password('StrongPassword123'))

        # Setup is now locked down - cannot be run again
        res_blocked = self.client.post('/api/auth/setup', json={
            'email': 'hacker@firma.pl',
            'password': 'AnotherPassword123'
        })
        self.assertEqual(res_blocked.status_code, 403)
        self.assertEqual(User.query.count(), 1)

        # Setup status reflects completed setup
        status_res = self.client.get('/api/auth/setup-status')
        self.assertFalse(status_res.json['needs_setup'])
        self.assertTrue(status_res.json['has_users'])

        # seed_admin returns False and does not touch existing user
        with redirect_stdout(io.StringIO()) as output:
            self.assertFalse(seed_admin())
        self.assertIn('Baza danych gotowa', output.getvalue())
