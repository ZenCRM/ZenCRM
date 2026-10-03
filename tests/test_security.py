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
from app.models.workspace import PortalSpace, PortalMember, PortalSession
from app.models.sms import SmsDevice, PhoneCall, SmsMessage
from app.api.push import validate_subscription
from app.services.email_service import render_template
from app.services.pdf_service import html_to_pdf
from app.api.public import rendered_html_response


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


if __name__ == '__main__':
    unittest.main()
