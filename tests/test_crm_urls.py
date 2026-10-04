import unittest
from unittest.mock import patch
from flask_jwt_extended import create_access_token
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.setting import Setting
from app.models.user import User
from app.services.email_service import render_template, staff_link_base_url
from app.utils.urls import normalize_crm_url, public_base_url


class CrmUrlTests(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            PUBLIC_BASE_URL = 'https://env.example.com'
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        user = User(email='admin@url.test', first_name='Admin', last_name='Test', role='admin', is_active=True)
        user.set_password('test-password-123')
        db.session.add(user)
        db.session.commit()
        self.headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    def test_setting_overrides_environment_and_company_website(self):
        Setting.set_value('company_www', 'https://marketing.example.com', 'company')
        self.assertEqual(public_base_url(), 'https://env.example.com')
        self.client.get('/api/settings/public')
        full = self.client.get('/api/settings/full', headers=self.headers).json
        self.assertEqual(next(row['value'] for row in full if row['key'] == 'crm_base_url'), public_base_url())
        response = self.client.put('/api/settings', json={'crm_base_url': 'https://crm.example.com:8443/'}, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(public_base_url(), 'https://crm.example.com:8443')
        for endpoint in ['/api/settings/public', '/api/settings/ui', '/api/portal/configuration', '/api/tickets/public/config']:
            response = self.client.get(endpoint, headers=self.headers)
            self.assertEqual(response.json['crm_base_url'], public_base_url(), endpoint)
        with self.app.test_request_context('/', base_url='https://wrong.example.com'):
            self.assertEqual(staff_link_base_url(), public_base_url())

    def test_invalid_values_do_not_change_saved_origin(self):
        self.client.put('/api/settings', json={'crm_base_url': 'crm.example.com'}, headers=self.headers)
        for value in ['javascript:alert(1)', 'https://user:pass@example.com', 'https://example.com/subpath', 'https://example.com?x=1', 'https://example.com#x', 'https://example.com:99999', 'https://evil\\example.com', 'https://example.com\n/path', 42]:
            response = self.client.put('/api/settings', json={'crm_base_url': value}, headers=self.headers)
            self.assertEqual(response.status_code, 400, value)
            self.assertEqual(public_base_url(), 'https://crm.example.com')
        self.assertEqual(normalize_crm_url('http://localhost:8000/'), 'http://localhost:8000')

    def test_company_website_is_never_used_as_crm_origin(self):
        self.app.config['PUBLIC_BASE_URL'] = ''
        Setting.set_value('company_www', 'https://marketing.example.com', 'company')
        self.assertEqual(public_base_url(), '')

    def test_confirmation_mail_contains_configured_ticket_link(self):
        self.client.put('/api/settings', json={'crm_base_url': 'https://crm.example.com'}, headers=self.headers)
        with patch('app.services.email_service.send_notification') as send:
            response = self.client.post('/api/tickets/public/submit', json={'email': 'visitor@example.com', 'title': 'Help', 'description': 'Details', 'category': 'general'}, headers={'Host': 'wrong.example.com'})
        self.assertEqual(response.status_code, 201)
        context = send.call_args_list[0].args[2]
        link = 'https://crm.example.com/pomoc?ticket=' + response.json['token']
        self.assertEqual(context['ticket_url'], link)
        _, html = render_template('client_ticket_created', context)
        self.assertIn('href="' + link + '"', html)
        self.assertIn('https://crm.example.com/logo.png', html)
        self.assertIn(b'hd-submit-view', self.client.get('/pomoc').data)
