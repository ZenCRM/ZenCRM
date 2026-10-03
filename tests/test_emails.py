import unittest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User
from app.models.email_template import EmailTemplate
from app.services.email_service import send_notification


class EmailNotificationsTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        user = User(id=1, email='admin@test.com', first_name='Admin', last_name='Test', role='admin')
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()

        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def auth_headers(self, uid=1):
        return {'Authorization': 'Bearer ' + create_access_token(identity=str(uid))}

    def test_seed_templates_and_list(self):
        EmailTemplate.seed_defaults()
        res = self.client.get('/api/emails/templates', headers=self.auth_headers(1))
        self.assertEqual(res.status_code, 200)
        templates = res.get_json()
        self.assertGreaterEqual(len(templates), 8)
        keys = {t['key'] for t in templates}
        self.assertIn('client_ticket_created', keys)
        self.assertIn('employee_new_ticket', keys)
        self.assertIn('employee_new_task', keys)
        self.assertIn('employee_client_assigned', keys)
        self.assertIn('password_reset', keys)

    def test_update_and_reset_template(self):
        EmailTemplate.seed_defaults()
        # Update
        res = self.client.put('/api/emails/templates/employee_new_task',
                              json={'subject': 'Własny temat zadania: {{task_title}}', 'body_html': '<p>Własna treść</p>'},
                              headers=self.auth_headers(1))
        self.assertEqual(res.status_code, 200)
        updated = res.get_json()
        self.assertEqual(updated['subject'], 'Własny temat zadania: {{task_title}}')

        # Reset
        res_reset = self.client.post('/api/emails/templates/employee_new_task/reset',
                                     headers=self.auth_headers(1))
        self.assertEqual(res_reset.status_code, 200)
        reset_tpl = res_reset.get_json()
        self.assertNotEqual(reset_tpl['subject'], 'Własny temat zadania: {{task_title}}')

    def test_user_email_preferences(self):
        u = db.session.get(User, 1)
        self.assertTrue(u.can_receive_email('ticket_assigned'))
        self.assertTrue(u.can_receive_email('task_assigned'))

        # Wyłącz powiadomienie o zadaniu
        u.email_notifications = '{"task_assigned": false, "ticket_assigned": true}'
        db.session.commit()
        self.assertFalse(u.can_receive_email('task_assigned'))
        self.assertTrue(u.can_receive_email('ticket_assigned'))

        # Test send_notification z wyłączonym powiadomieniem
        ok, msg = send_notification('employee_new_task', u.email, {'task_title': 'Test'}, user=u)
        self.assertFalse(ok)
        self.assertIn('Wyłączone w preferencjach', msg)

    def test_smtp_settings_api(self):
        res = self.client.get('/api/emails/smtp', headers=self.auth_headers(1))
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('smtp_host', data)
        self.assertIn('smtp_port', data)

        res_put = self.client.put('/api/emails/smtp', json={
            'smtp_host': 'smtp.testdomain.com',
            'smtp_port': 587,
            'smtp_user': 'test@testdomain.com',
            'smtp_from_email': 'test@testdomain.com',
            'smtp_from_name': 'Test CRM',
            'smtp_enabled': False,
        }, headers=self.auth_headers(1))
        self.assertEqual(res_put.status_code, 200)

        res_after = self.client.get('/api/emails/smtp', headers=self.auth_headers(1))
        self.assertEqual(res_after.get_json()['smtp_host'], 'smtp.testdomain.com')

    def test_smtp_connection_datetime_defined(self):
        from app.services.email_service import test_smtp_connection
        # Sprawdzamy czy test_smtp_connection nie rzuca NameError na datetime
        # (zwróci błąd sieci/połączenia, ale nie NameError: datetime)
        ok, msg = test_smtp_connection({
            'host': '127.0.0.1',
            'port': 2525,
            'user': '',
            'password': '',
            'from_email': 'crm@test.pl',
            'from_name': 'CRM',
            'encryption': 'none'
        }, 'test@recipient.pl')
        self.assertNotIn("name 'datetime' is not defined", msg)


if __name__ == '__main__':
    unittest.main()
