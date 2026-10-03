import unittest

from flask_jwt_extended import create_access_token
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.setting import Setting
from app.models.user import User


class SettingsAccessTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'settings-test-secret-key-at-least-32-bytes'
            PUSH_ENABLED = False
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        self.headers = {}
        for role in ('admin', 'employee'):
            user = User(email=role + '@example.com', first_name='Test',
                        last_name='User', role=role, is_active=True)
            user.set_password('test-password')
            db.session.add(user)
            db.session.flush()
            self.headers[role] = {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}
        for key in ('smtp_password', 'helpdesk_webhook_token', 'brand_secret', 'company_nip'):
            Setting.set_value(key, 'private-test-value', 'general')
        Setting.set_value('required_standard_fields', '{"client":["name"]}', 'general')
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_anonymous_cannot_read_private_settings(self):
        for path in ('/api/settings', '/api/settings/full', '/api/settings/ui'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 401, path)
            self.assertNotIn('private-test-value', response.get_data(as_text=True))

    def test_public_contains_only_login_branding(self):
        response = self.client.get('/api/settings/public')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['brand_name'], 'ZenCRM')
        self.assertNotIn('private-test-value', response.get_data(as_text=True))
        self.assertNotIn('required_standard_fields', response.json)
        self.assertEqual(response.headers['Cache-Control'], 'no-store')

    def test_employee_gets_ui_without_secrets(self):
        response = self.client.get('/api/settings/ui', headers=self.headers['employee'])
        self.assertEqual(response.status_code, 200)
        self.assertIn('required_standard_fields', response.json)
        self.assertNotIn('private-test-value', response.get_data(as_text=True))
        for path in ('/api/settings', '/api/settings/full'):
            self.assertEqual(self.client.get(path, headers=self.headers['employee']).status_code, 403)

    def test_admin_and_inactive_account(self):
        for path in ('/api/settings', '/api/settings/full'):
            response = self.client.get(path, headers=self.headers['admin'])
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers['Cache-Control'], 'no-store')
        User.query.filter_by(role='admin').one().is_active = False
        db.session.commit()
        for path in ('/api/settings', '/api/settings/full', '/api/settings/ui'):
            self.assertEqual(self.client.get(path, headers=self.headers['admin']).status_code, 403)
