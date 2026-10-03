import unittest
from flask_jwt_extended import create_access_token
from jinja2.exceptions import SecurityError
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User
from app.models.sms import SmsDevice, SmsQueue
from app.services.render_service import render_template_string


class ApiSecurityTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'security-test-key-with-at-least-32-bytes'
            PUSH_ENABLED = False
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        self.app.add_url_rule('/api/security-regression-probe', 'security_probe', lambda: {'private': True})
        self.users = {}
        self.headers = {}
        for role in ('admin', 'employee'):
            user = User(email=role + '@example.com', first_name='Test', last_name='User', role=role, is_active=True)
            user.set_password('test-password')
            db.session.add(user)
            db.session.flush()
            self.users[role] = user
            self.headers[role] = {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_registration_requires_admin(self):
        payload = {'email': 'new@example.com', 'password': 'new-password'}
        self.assertEqual(self.client.post('/api/auth/register', json=payload).status_code, 401)
        self.assertEqual(self.client.post('/api/auth/register', json=payload, headers=self.headers['employee']).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/register', json=payload, headers=self.headers['admin']).status_code, 201)

    def test_disabled_login(self):
        self.users['employee'].is_active = False
        db.session.commit()
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'employee@example.com', 'password': 'test-password'}).status_code, 401)

    def test_template_sandbox_and_normal_render(self):
        self.assertEqual(render_template_string('Hello {{ client.name }}', {'client': {'name': 'Alice'}}), 'Hello Alice')
        with self.assertRaises(SecurityError):
            render_template_string('{{ cycler.__init__.__globals__.os.getcwd() }}', {})

    def test_device_cannot_report_another_devices_task(self):
        a = SmsDevice(name='A', token='test-device-a')
        b = SmsDevice(name='B', token='test-device-b')
        db.session.add_all([a, b])
        db.session.flush()
        task = SmsQueue(device_id=b.id, action='send_sms', status='processing',
                        phone_number='123456789', message='Security test')
        db.session.add(task)
        db.session.commit()
        response = self.client.post('/api/sms/report', json={'token': a.token, 'id': task.id, 'status': 'sent'})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(db.session.get(SmsQueue, task.id).status, 'processing')
        self.assertEqual(self.client.post('/api/sms/report', json={'token': b.token, 'id': task.id, 'status': 'sent'}).status_code, 200)

    def test_employee_does_not_receive_integration_secrets(self):
        db.session.add(SmsDevice(name='A', token='test-device-secret'))
        db.session.commit()
        response = self.client.get('/api/sms/devices', headers=self.headers['employee'])
        self.assertEqual(response.json, [])
        response = self.client.get('/api/tickets/settings', headers=self.headers['employee'])
        self.assertNotIn('helpdesk_webhook_token', response.json)

    def test_new_route_is_private_by_default(self):
        self.assertEqual(self.client.get('/api/security-regression-probe').status_code, 401)
        self.assertEqual(self.client.get('/api/security-regression-probe', headers=self.headers['employee']).status_code, 200)

    def test_inactive_and_deleted_accounts_cannot_read_or_refresh(self):
        from flask_jwt_extended import create_refresh_token
        refresh = {'Authorization': 'Bearer ' + create_refresh_token(identity=str(self.users['employee'].id))}
        self.users['employee'].is_active = False
        db.session.commit()
        for path in ('/api/clients', '/api/tasks', '/api/auth/me', '/api/tickets/settings'):
            self.assertEqual(self.client.get(path, headers=self.headers['employee']).status_code, 403, path)
        self.assertEqual(self.client.post('/api/auth/refresh', headers=refresh).status_code, 403)
        db.session.delete(self.users['employee'])
        db.session.commit()
        self.assertEqual(self.client.get('/api/clients', headers=self.headers['employee']).status_code, 401)

    def test_public_login_and_device_gateway_keep_working(self):
        self.assertEqual(self.client.get('/api/settings/public').status_code, 200)
        self.assertEqual(self.client.get('/api/portal/configuration').status_code, 200)
        self.assertEqual(self.client.get('/api/tickets/public/config').status_code, 200)
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'employee@example.com', 'password': 'test-password'}).status_code, 200)
        db.session.add(SmsDevice(name='A', token='test-device'))
        db.session.commit()
        self.assertEqual(self.client.get('/api/sms/next?token=test-device').status_code, 200)
        self.assertEqual(self.client.get('/api/sms/next?token=wrong').status_code, 403)

    def test_unknown_api_is_not_spa_html(self):
        self.assertEqual(self.client.get('/api/not-a-real-route').status_code, 404)

    def test_password_change_invalidates_token(self):
        res = self.client.post('/api/auth/login', json={'email': 'employee@example.com', 'password': 'test-password'})
        self.assertEqual(res.status_code, 200)
        token = res.json['access_token']
        headers = {'Authorization': f'Bearer {token}'}

        # Token works initially
        self.assertEqual(self.client.get('/api/security-regression-probe', headers=headers).status_code, 200)

        # Change password
        self.users['employee'].set_password('brand-new-password')
        db.session.commit()

        # Old token is immediately revoked
        self.assertEqual(self.client.get('/api/security-regression-probe', headers=headers).status_code, 401)

        # Old credentials fail
        self.assertEqual(self.client.post('/api/auth/login', json={'email': 'employee@example.com', 'password': 'test-password'}).status_code, 401)

        # New credentials succeed
        new_login = self.client.post('/api/auth/login', json={'email': 'employee@example.com', 'password': 'brand-new-password'})
        self.assertEqual(new_login.status_code, 200)
        new_headers = {'Authorization': f"Bearer {new_login.json['access_token']}"}
        self.assertEqual(self.client.get('/api/security-regression-probe', headers=new_headers).status_code, 200)

    def test_password_reset_flow(self):
        from app.models.auth_security import PasswordReset
        res = self.client.post('/api/auth/forgot-password', json={'email': 'employee@example.com'})
        self.assertEqual(res.status_code, 200)
        pr = PasswordReset.query.filter_by(user_id=self.users['employee'].id).first()
        self.assertIsNotNone(pr)

        # Short password fails
        self.assertEqual(self.client.post('/api/auth/reset-password', json={'token': 'invalid-token', 'password': 'short'}).status_code, 400)

        # Invalid token fails
        self.assertEqual(self.client.post('/api/auth/reset-password', json={'token': 'invalid-token-1234567890', 'password': 'new-valid-password-123'}).status_code, 400)

    def test_security_headers_present(self):
        res = self.client.get('/api/settings/public')
        self.assertEqual(res.headers.get('X-Content-Type-Options'), 'nosniff')
        self.assertEqual(res.headers.get('Referrer-Policy'), 'no-referrer')
        self.assertEqual(res.headers.get('Cache-Control'), 'no-store')
