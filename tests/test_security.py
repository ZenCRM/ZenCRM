"""Regression checks for the public security boundaries."""
import tempfile
import unittest
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import jwt
from flask_jwt_extended import create_access_token
from pypdf import PdfReader

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.ticket import Ticket, TicketMessage
from app.models.user import User
from app.models.comment import Comment
from app.models.document import Document
from app.models.lead import Lead
from app.models.setting import Setting
from app.models.task import Task
from app.models.workspace import PortalSpace, PortalMember, PortalSession
from app.models.sms import SmsDevice, PhoneCall, SmsMessage
from app.api.push import validate_subscription
from app.services.email_service import render_template
from app.services.pdf_service import html_to_pdf
from app.api.public import rendered_html_response
from app.utils.sanitize import apply_payload


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    PUSH_ENABLED = False
    SECRET_KEY = 'twoj-sekret'
    JWT_SECRET_KEY = 'twoj-jwt-sekret'
    PUBLIC_BASE_URL = 'https://crm.example.com'


class SecurityRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)
        cls.client = cls.app.test_client()
        with cls.app.app_context():
            users = []
            for name, role in [('admin', 'admin'), ('alice', 'employee'), ('bob', 'employee')]:
                user = User(email=f'{name}@example.com', first_name=name,
                            last_name='Test', role=role, is_active=True)
                user.set_password('long-password-123')
                db.session.add(user)
                users.append(user)
            db.session.commit()
            cls.ids = [user.id for user in users]
            cls.tokens = [create_access_token(identity=str(user.id)) for user in users]

    def auth(self, index):
        return {'Authorization': f'Bearer {self.tokens[index]}'}

    def test_placeholder_keys_are_replaced(self):
        self.assertGreaterEqual(len(self.app.config['SECRET_KEY']), 32)
        self.assertGreaterEqual(len(self.app.config['JWT_SECRET_KEY']), 32)
        self.assertNotEqual(self.app.config['JWT_SECRET_KEY'], 'twoj-jwt-sekret')

    def test_token_without_password_version_is_rejected(self):
        now = datetime.now(timezone.utc)
        token = jwt.encode({
            'sub': str(self.ids[0]), 'type': 'access',
            'fresh': False, 'jti': 'forged-test',
            'iat': now, 'nbf': now, 'exp': now + timedelta(minutes=5),
        }, self.app.config['JWT_SECRET_KEY'], algorithm='HS256')
        denied = self.client.get('/api/users', headers={'Authorization': f'Bearer {token}'})
        self.assertEqual(denied.status_code, 401)

    def test_other_users_comment_cannot_be_changed(self):
        with self.app.app_context():
            comment = Comment(content='Original', entity_type='client', entity_id=1,
                              user_id=self.ids[1])
            db.session.add(comment)
            db.session.commit()
            comment_id = comment.id
        url = f'/api/comments/{comment_id}'
        self.assertEqual(self.client.put(url, json={'content': 'Tampered'},
                                         headers=self.auth(2)).status_code, 403)
        self.assertEqual(self.client.delete(url, headers=self.auth(2)).status_code, 403)

    def test_self_password_change_requires_current_password(self):
        url = f'/api/users/{self.ids[2]}'
        denied = self.client.put(url, json={'password': 'replacement-password'},
                                 headers=self.auth(2))
        self.assertEqual(denied.status_code, 403)
        changed = self.client.put(url, json={'password': 'replacement-password',
                                             'current_password': 'long-password-123'},
                                  headers=self.auth(2))
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(self.client.get('/api/users', headers=self.auth(2)).status_code, 401)

    def test_unmapped_portal_space_cannot_download_unassigned_document(self):
        portal_token = 'portal-test-token'
        with self.app.app_context():
            space = PortalSpace(name='Unmapped')
            doc = Document(title='Unassigned', content='Private', client_id=None)
            db.session.add_all([space, doc])
            db.session.flush()
            member = PortalMember(space_id=space.id, email='portal@example.com',
                                  password_hash='unused', active=True)
            db.session.add(member)
            db.session.flush()
            db.session.add(PortalSession(token_hash=hashlib.sha256(portal_token.encode()).hexdigest(),
                                         member_id=member.id,
                                         expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)))
            db.session.commit()
            path = f'/api/portal/spaces/{space.id}/items/doc_{doc.id}/file'
        response = self.client.get(path, headers={'X-Portal-Token': portal_token})
        self.assertEqual(response.status_code, 404)

    def test_entity_history_only_contains_own_device(self):
        with self.app.app_context():
            own = SmsDevice(name='Alice phone', user_id=self.ids[1], token='device-alice')
            other = SmsDevice(name='Bob phone', user_id=self.ids[2], token='device-bob')
            db.session.add_all([own, other])
            db.session.flush()
            db.session.add_all([
                PhoneCall(device_id=own.id, number='123456789', type='incoming', timestamp=1),
                PhoneCall(device_id=other.id, number='123456789', type='incoming', timestamp=2),
                SmsMessage(device_id=own.id, address='123456789', body='Own', type='received', timestamp=1),
                SmsMessage(device_id=other.id, address='123456789', body='Private', type='received', timestamp=2),
            ])
            db.session.commit()
            other_call_id = PhoneCall.query.filter_by(device_id=other.id).one().id
        response = self.client.get('/api/sms/entity-history?phone=123456789', headers=self.auth(1))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json['calls']), 1)
        self.assertEqual(len(response.json['messages']), 1)
        self.assertNotIn('Private', response.get_data(as_text=True))
        self.assertEqual(self.client.put(f'/api/sms/calls/{other_call_id}/note',
                                         json={'note': 'Tampered'}, headers=self.auth(1)).status_code, 404)

    def test_push_endpoint_rejects_backslash_host_confusion(self):
        with self.assertRaises(ValueError):
            validate_subscription({'endpoint': 'https://evil.example\\.push.apple.com/path'})

    def test_rendered_html_is_sandboxed(self):
        with self.app.app_context():
            response = rendered_html_response('<script>alert(1)</script>')
            self.assertIn('sandbox;', response.headers['Content-Security-Policy'])
            self.assertNotIn('allow-scripts', response.headers['Content-Security-Policy'])

    def test_pdf_cannot_attach_local_file(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / 'secret.txt'
            secret.write_text('server secret', encoding='utf-8')
            output = Path(directory) / 'out.pdf'
            markup = f'<h1>Safe</h1><a rel="attachment" href="{secret.as_uri()}">file</a>'
            self.assertEqual(html_to_pdf(markup, str(output)), str(output))
            self.assertEqual(PdfReader(str(output)).attachments, {})

    def test_pdf_fallback_cannot_read_local_file(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / 'secret.txt'
            secret.write_text('server secret', encoding='utf-8')
            output = Path(directory) / 'fallback.pdf'
            markup = f'<img src="{secret.as_uri()}"><p>Safe</p>'
            with patch.dict(sys.modules, {'weasyprint': None}):
                result = html_to_pdf(markup, str(output))
            if result:
                self.assertNotIn(b'server secret', output.read_bytes())
                self.assertEqual(PdfReader(str(output)).attachments, {})
            else:
                self.assertFalse(output.exists())

    def test_email_values_are_html_escaped(self):
        with self.app.app_context():
            _, html = render_template('employee_new_ticket', {
                'ticket_title': '<img src=x onerror=alert(1)>',
                'ticket_number': 'TIC-2026-0001',
            })
            self.assertNotIn('<img src=x onerror=alert(1)>', html)
            self.assertIn('&lt;img', html)

    def test_public_ticket_ignores_priority_and_host(self):
        with patch('app.services.email_service.send_notification') as send:
            result = self.client.post('/api/tickets/public/submit', json={
                'email': 'visitor@example.com', 'title': 'Help',
                'description': 'Please help', 'category': 'general',
                'priority': 'urgent', 'source': 'internal',
            }, headers={'Host': 'attacker.example'})
        self.assertEqual(result.status_code, 201)
        with self.app.app_context():
            ticket = Ticket.query.filter_by(token=result.json['token']).one()
            self.assertEqual((ticket.priority, ticket.source), ('medium', 'helpdesk'))
        self.assertTrue(send.called)
        self.assertIn('https://crm.example.com/', send.call_args_list[0].args[2]['ticket_url'])
        self.assertNotIn('attacker.example', str(send.call_args_list))

    def test_public_ticket_hides_staff_email(self):
        with self.app.app_context():
            ticket = Ticket(ticket_number='TIC-2026-9001', title='Question',
                            description='Question', contact_email='private@example.com',
                            token=Ticket.generate_token(), category='general')
            db.session.add(ticket)
            db.session.flush()
            db.session.add(TicketMessage(ticket_id=ticket.id, sender_type='agent',
                                         sender_name='Agent', sender_email='staff@example.com',
                                         content='Reply', is_internal=False))
            db.session.commit()
            token = ticket.token
        response = self.client.get(f'/api/tickets/public/track/{token}')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('staff@example.com', response.get_data(as_text=True))
        self.assertNotIn('user_id', response.get_data(as_text=True))


    def test_payload_cannot_set_server_managed_fields(self):
        document = Document(title='Contract', type='contract')
        apply_payload(document, {'created_by': self.ids[0], 'file_path': '/etc/passwd', 'title': 'Renamed'})
        self.assertEqual((document.title, document.created_by, document.file_path), ('Renamed', None, None))
        lead = Lead(title='Prospect')
        apply_payload(lead, {'converted_to_client_id': 1})
        self.assertIsNone(lead.converted_to_client_id)

    def test_profile_avatar_cannot_point_to_external_url(self):
        url = f'/api/users/{self.ids[2]}'
        response = self.client.put(url, json={'avatar_url': 'https://tracker.example/pixel.png'}, headers=self.auth(2))
        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertIsNone(db.session.get(User, self.ids[2]).avatar_url)
        self.assertEqual(self.client.put(url, json={'avatar_url': ''}, headers=self.auth(2)).status_code, 200)

    def test_webhook_rejects_non_ascii_token_without_crashing(self):
        with self.app.app_context():
            Setting.set_value('lead_webhook_token', 'expected-webhook-token')
            db.session.commit()
        response = self.client.post('/api/leads/webhook', json={'name': 'Lead'},
                                    headers={'X-Webhook-Token': 'zażółć'.encode().decode('latin-1')})
        self.assertEqual(response.status_code, 401)

    def test_unknown_login_email_still_checks_a_password_hash(self):
        with patch('app.api.auth.check_password_hash', return_value=False) as check:
            response = self.client.post('/api/auth/login', json={'email': 'nobody@example.com', 'password': 'guess'})
        self.assertEqual(response.status_code, 401)
        self.assertTrue(check.called)
        with self.app.app_context():
            dormant = User(email='dormant@example.com', first_name='Dormant', last_name='User', role='employee', is_active=False)
            dormant.set_password('long-password-123')
            db.session.add(dormant)
            db.session.commit()
        with patch('app.models.user.check_password_hash', return_value=False) as check:
            response = self.client.post('/api/auth/login', json={'email': 'dormant@example.com', 'password': 'guess'})
        self.assertEqual(response.status_code, 401)
        self.assertTrue(check.called)
        with patch('app.api.portal.check_password_hash', return_value=False) as check:
            response = self.client.post('/api/portal/login', json={'email': 'nobody@example.com', 'password': 'guess'})
        self.assertEqual(response.status_code, 401)
        self.assertTrue(check.called)

    def test_task_assignees_must_be_existing_active_users(self):
        with self.app.app_context():
            task = Task(title='Assigned work')
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        url = f'/api/task-assignees/task/{task_id}/set'
        for user_ids in ('1', [999999], ['x'], [True]):
            response = self.client.post(url, json={'user_ids': user_ids}, headers=self.auth(0))
            self.assertEqual(response.status_code, 400, user_ids)
        self.assertEqual(self.client.post(url, json={'user_ids': [self.ids[1]]}, headers=self.auth(0)).status_code, 200)
        with self.app.app_context():
            inactive = User(email='former@example.com', first_name='Former', last_name='Staff', role='employee', is_active=True)
            inactive.set_password('long-password-123')
            db.session.add(inactive)
            db.session.commit()
            inactive_id = inactive.id
        self.assertEqual(self.client.post(url, json={'user_ids': [self.ids[1], inactive_id]}, headers=self.auth(0)).status_code, 200)
        with self.app.app_context():
            db.session.get(User, inactive_id).is_active = False
            db.session.commit()
        # An already assigned user who was deactivated must not block further changes.
        response = self.client.post(url, json={'user_ids': [self.ids[1], inactive_id, self.ids[2]]}, headers=self.auth(0))
        self.assertEqual(response.status_code, 200)

    def test_phone_actions_are_allowlisted_and_validated(self):
        with self.app.app_context():
            device = SmsDevice(name='Action phone', token='ACTION_PHONE_TOKEN', user_id=self.ids[1], is_active=True)
            db.session.add(device)
            db.session.commit()
            device_id = device.id
        def trigger(payload):
            return self.client.post('/api/sms/actions/trigger', json={'device_id': device_id, **payload}, headers=self.auth(1))
        self.assertEqual(trigger({'action': 'wipe_phone'}).status_code, 400)
        self.assertEqual(trigger({'action': ['get_stats']}).status_code, 400)
        response = self.client.post('/api/sms/actions/trigger', data='{"device_id": %d, "action": "get_sms_history", "phone_number": "+48500100200", "limit": Infinity}' % device_id,
                                    content_type='application/json', headers=self.auth(1))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(trigger({'action': 'get_sms_history', 'phone_number': '+48500100200', 'limit': 'many'}).status_code, 400)
        self.assertEqual(trigger({'action': 'get_sms_history_by_date', 'start_date': 'yesterday', 'end_date': 1}).status_code, 400)
        self.assertEqual(trigger({'action': 'get_stats'}).status_code, 201)

    def test_staff_notification_links_use_configured_origin(self):
        with self.app.app_context():
            task = Task(title='Linked work')
            db.session.add(task)
            db.session.commit()
            task_id = task.id
        with patch('app.services.email_service.send_notification') as send:
            response = self.client.post(f'/api/task-assignees/task/{task_id}/set', json={'user_ids': [self.ids[2]]},
                                        headers={**self.auth(0), 'Host': 'attacker.example'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(send.call_args.args[2]['crm_task_url'], 'https://crm.example.com/#tasks')

if __name__ == '__main__':
    unittest.main()
