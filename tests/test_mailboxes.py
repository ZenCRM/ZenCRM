import unittest
from datetime import datetime
from unittest.mock import patch
from flask_jwt_extended import create_access_token
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User
from app.models.team import Team
from app.models.client import Client
from app.models.contact import Contact
from app.models.mailbox import Mailbox, MailMessage
from app.services.mailbox_service import encrypt_password, password, message_body, sync_inbox
from app.utils.mail_html import sanitize_mail_html, sanitize_signature_html
from app.services.mailbox_imap import parse_structure, mime_parts
from email import policy
from email.parser import BytesParser


class MailboxesTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            PREPARE_DATABASE = False
            PUSH_ENABLED = False
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            SECRET_KEY = 'mailbox-test-secret-with-at-least-32-bytes'
            JWT_SECRET_KEY = 'mailbox-test-jwt-with-at-least-32-bytes'
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        for uid, role in ((1, 'employee'), (2, 'employee'), (3, 'admin')):
            u = User(id=uid, email=f'user{uid}@test.com', first_name='User', last_name=str(uid), role=role)
            u.set_password('test-password')
            db.session.add(u)
        db.session.flush()
        db.session.add(Team(id=1, name='Team', leader_id=1, members=[db.session.get(User, 1), db.session.get(User, 2)]))
        self.box = Mailbox(name='Private', email='me@test.com', user_id=1, username='me@test.com',
                           password_encrypted=encrypt_password('secret-password'), imap_host='imap.test.com', smtp_host='smtp.test.com')
        db.session.add(self.box)
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def headers(self, uid=1):
        return {'Authorization': 'Bearer ' + create_access_token(identity=str(uid))}

    def test_polling_interval_persists_and_rejects_invalid_values(self):
        self.assertEqual(self.box.sync_interval_minutes,5)
        for interval in (5,10,15,30,60):
            response = self.client.put(f'/api/mailboxes/{self.box.id}',json={'sync_interval_minutes':interval},headers=self.headers())
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json['sync_interval_minutes'],interval)
            self.assertIsNotNone(self.box.next_sync_at)
        for invalid in (0,1,6,True,'10',None):
            self.assertEqual(self.client.put(f'/api/mailboxes/{self.box.id}',json={'sync_interval_minutes':invalid},headers=self.headers()).status_code,400)
        self.assertEqual(self.box.sync_interval_minutes,60)

    def test_periodic_polling_respects_schedule_lease_and_retries_failures(self):
        from app.services.mailbox_worker import sync_due
        from datetime import timedelta
        now = datetime.utcnow()
        box_id = self.box.id
        self.box.next_sync_at = now + timedelta(minutes=30)
        db.session.commit()
        with patch('app.services.mailbox_worker.sync_inbox') as sync:
            sync_due(now)
            sync.assert_not_called()
            self.box.next_sync_at = now - timedelta(minutes=1)
            self.box.sync_claim_until = now + timedelta(minutes=10)
            db.session.commit()
            sync_due(now)
            sync.assert_not_called()
            self.box.sync_claim_until = None
            db.session.commit()
            sync.side_effect = ValueError('private provider error')
            sync_due(now)
            sync.assert_called_once()
        box = db.session.get(Mailbox,box_id)
        self.assertIsNone(box.sync_claim_token)
        self.assertIsNone(box.sync_claim_until)
        self.assertGreater(box.next_sync_at,now)

    def test_received_signature_background_css_preserved_without_remote_css(self):
        raw = '<html><head><style>@import "https://bad.test/track.css";.signature{background:#14213d;border-radius:18px;overflow:hidden}.bad{background-image:url(https://bad.test)}</style></head><body style="background:#fafafa"><table class="signature" style="background:linear-gradient(90deg,#14213d,#304060);letter-spacing:-0.2px"><tr><td>Signature</td></tr></table><script>evil()</script></body></html>'
        cleaned = sanitize_mail_html(raw)
        for value in ('background:#14213d','class="signature"','overflow:hidden','linear-gradient','background:#fafafa'):
            self.assertIn(value,cleaned)
        for value in ('@import','bad.test','script','evil()'):
            self.assertNotIn(value,cleaned)

    def test_unread_count_is_private_and_excludes_sent_and_read(self):
        shared = Mailbox(name='Shared', email='team@test.com', team_id=1, username='team',
                         password_encrypted=encrypt_password('secret'), imap_host='imap.test.com', smtp_host='smtp.test.com')
        db.session.add(shared)
        db.session.flush()
        for box, folder, read in ((self.box,'inbox',False),(self.box,'inbox',True),
                                  (self.box,'sent',False),(shared,'inbox',False)):
            db.session.add(MailMessage(mailbox_id=box.id, folder=folder, sender='sender@test.com', is_read=read))
        db.session.commit()
        self.assertEqual(self.client.get('/api/mailboxes/unread',headers=self.headers()).json, {'total':2})
        self.assertEqual(self.client.get('/api/mailboxes/unread',headers=self.headers(2)).json, {'total':1})
        self.assertEqual(self.client.get('/api/mailboxes/unread',headers=self.headers(3)).json, {'total':0})
        self.assertEqual(self.client.get('/api/mailboxes/unread').status_code,401)

    def test_host_change_requires_password_before_network_or_mutation(self):
        with patch('app.api.mailboxes.test_connection') as connection:
            response = self.client.put(f'/api/mailboxes/{self.box.id}',json={'smtp_host':'attacker.example'},headers=self.headers())
            self.assertEqual(response.status_code,400)
            connection.assert_not_called()
        self.assertEqual(db.session.get(Mailbox,self.box.id).smtp_host,'smtp.test.com')
        with patch('app.api.mailboxes.test_connection'):
            response = self.client.put(f'/api/mailboxes/{self.box.id}',json={'smtp_host':'new.example','password':'new-secret'},headers=self.headers())
            self.assertEqual(response.status_code,200)
            self.assertEqual(password(self.box),'new-secret')

    def test_profile_email_method_defaults_persists_and_validates(self):
        self.assertEqual(self.client.get('/api/users/1',headers=self.headers()).json['default_email_method'],'mailto')
        saved = self.client.put('/api/users/1',json={'default_email_method':'crm'},headers=self.headers())
        self.assertEqual(saved.status_code,200)
        self.assertEqual(self.client.get('/api/users/1',headers=self.headers()).json['default_email_method'],'crm')
        invalid = self.client.put('/api/users/1',json={'default_email_method':'invalid'},headers=self.headers())
        self.assertEqual(invalid.status_code,400)
        self.assertEqual(self.client.get('/api/users/1',headers=self.headers()).json['default_email_method'],'crm')
        self.assertEqual(self.client.put('/api/users/2',json={'default_email_method':'crm'},headers=self.headers()).status_code,403)

    def test_personal_is_private_even_from_admin(self):
        for uid in (2, 3):
            self.assertEqual(self.client.get('/api/mailboxes', headers=self.headers(uid)).json, [])
            self.assertEqual(self.client.get(f'/api/mailboxes/{self.box.id}/messages', headers=self.headers(uid)).status_code, 404)
            self.assertEqual(self.client.post(f'/api/mailboxes/{self.box.id}/send', json={}, headers=self.headers(uid)).status_code, 404)
        data = self.client.get('/api/mailboxes', headers=self.headers()).json[0]
        self.assertNotIn('password_encrypted', data)
        self.assertNotIn('password', data)
        self.assertNotIn('secret-password', self.box.password_encrypted)
        self.assertEqual(password(self.box), 'secret-password')

    def test_client_history_matches_email_and_contacts_and_respects_mailbox_access(self):
        client = Client(name='Company', email=' CLIENT@Test.com ')
        db.session.add(client); db.session.flush()
        db.session.add(Contact(first_name='Person',email='contact@test.com',client_id=client.id))
        db.session.add(Contact(first_name='Archived',email='archived@test.com',client_id=client.id,deleted_at=datetime.utcnow()))
        team_box = Mailbox(name='Team',email='team@test.com',team_id=1,username='team',password_encrypted=encrypt_password('test'),imap_host='imap.test.com',smtp_host='smtp.test.com')
        db.session.add(team_box); db.session.flush()
        messages = [
            MailMessage(mailbox_id=self.box.id,sender='client@test.com',subject='Private incoming'),
            MailMessage(mailbox_id=team_box.id,sender='CONTACT@test.com',subject='Contact incoming'),
            MailMessage(mailbox_id=team_box.id,folder='sent',sender='team@test.com',recipients=['other@test.com'],cc=['CLIENT@test.com'],subject='CC outgoing'),
            MailMessage(mailbox_id=team_box.id,folder='sent',sender='team@test.com',bcc=['contact@test.com'],subject='BCC outgoing'),
            MailMessage(mailbox_id=team_box.id,sender='archived@test.com',subject='Archived contact'),
            MailMessage(mailbox_id=team_box.id,folder='sent',sender='team@test.com',recipients=['notclient@test.com'],subject='Substring'),
        ]
        db.session.add_all(messages); db.session.commit()
        url = f'/api/mailboxes/clients/{client.id}/messages'
        own = self.client.get(url,headers=self.headers()).json
        self.assertEqual(own['total'],4)
        self.assertEqual(set(own['emails']),{'client@test.com','contact@test.com'})
        self.assertEqual({m['subject'] for m in own['items']},{'Private incoming','Contact incoming','CC outgoing','BCC outgoing'})
        self.assertEqual(self.client.get(url,headers=self.headers(2)).json['total'],3)
        self.assertEqual(self.client.get(url,headers=self.headers(3)).json['total'],0)
        self.assertEqual(self.client.get(url).status_code,401)

    def test_empty_client_email_does_not_match_empty_senders(self):
        client = Client(name='No address')
        db.session.add(client); db.session.add(MailMessage(mailbox_id=self.box.id,sender='',subject='Empty'))
        db.session.commit()
        result = self.client.get(f'/api/mailboxes/clients/{client.id}/messages',headers=self.headers()).json
        self.assertEqual(result['total'],0)
        self.assertEqual(result['emails'],[])

    def test_full_html_signature_preserves_css_and_layout_after_save_and_send(self):
        signature = '<!doctype html><html><head><style>.signature{background:#14213d;overflow:hidden}@media(max-width:500px){.signature td{display:block}}</style></head><body><table class="signature" style="background:#14213d;border-radius:18px;overflow:hidden;letter-spacing:-0.2px"><tr><td><img src="https://example.test/logo.png" style="display:block;outline:none"><a href="mailto:person@example.test">Person</a></td></tr></table></body></html>'
        response = self.client.put(f'/api/mailboxes/{self.box.id}',json={'signature':signature,'signature_format':'html'},headers=self.headers())
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json['signature'],signature)
        with patch('app.services.mailbox_service.smtp_connection') as smtp:
            smtp.return_value.__enter__.return_value.send_message.return_value = {}
            sent = self.client.post(f'/api/mailboxes/{self.box.id}/send',json={'to':'client@test.com','subject':'Hello','body':'Message'},headers=self.headers())
            self.assertEqual(sent.status_code,201)
            html = smtp.return_value.__enter__.return_value.send_message.call_args.args[0].get_body(preferencelist=('html',)).get_content()
        for expected in ('<style>', '@media', 'background:#14213d', 'overflow:hidden', 'letter-spacing:-0.2px', 'https://example.test/logo.png'):
            self.assertIn(expected,html)
        self.assertNotIn('<html>',html)

    def test_signature_blocks_active_html_without_rewriting_formatting(self):
        raw = '<style>.signature{display:flex;background:linear-gradient(red,blue)}</style><div class="signature" style="overflow:hidden"><script>bad()</script><iframe src="https://bad.test"></iframe><img src="https://good.test/logo.png" onerror="bad()"><a href="javascript:bad()">Link</a></div>'
        cleaned = sanitize_signature_html(raw)
        for expected in ('<style>', 'display:flex', 'linear-gradient(red,blue)', 'class="signature"', 'overflow:hidden', 'https://good.test/logo.png'):
            self.assertIn(expected,cleaned)
        for forbidden in ('<script', '<iframe', 'onerror', 'javascript:', 'bad()'):
            self.assertNotIn(forbidden,cleaned)

    def test_large_signature_html_limit_is_supported(self):
        signature = '<table><tr><td>' + 'Example ' * 2000 + '</td></tr></table>'
        result = self.client.put(f'/api/mailboxes/{self.box.id}',json={'signature':signature,'signature_format':'html'},headers=self.headers())
        self.assertEqual(result.status_code,200)
        self.assertEqual(result.json['signature'],signature)

    def test_shared_access_and_management(self):
        self.box.user_id = None
        self.box.team_id = 1
        db.session.commit()
        self.assertEqual(len(self.client.get('/api/mailboxes', headers=self.headers(2)).json), 1)
        self.assertEqual(self.client.put(f'/api/mailboxes/{self.box.id}', json={'signature': 'Team'}, headers=self.headers(2)).status_code, 403)
        self.assertEqual(self.client.put(f'/api/mailboxes/{self.box.id}', json={'signature': 'Team'}, headers=self.headers()).status_code, 200)
        team = db.session.get(Team, 1)
        team.members.remove(db.session.get(User, 2))
        db.session.commit()
        self.assertEqual(self.client.get(f'/api/mailboxes/{self.box.id}/messages', headers=self.headers(2)).status_code, 404)

    def test_case_insensitive_matches_and_excludes_archived(self):
        c = Client(name='Company', email=' Person@Test.com ')
        db.session.add(c)
        db.session.flush()
        db.session.add(Contact(first_name='Person', last_name='Example', email='PERSON@test.com', client_id=c.id))
        db.session.add(Client(name='Archived', email='person@test.com', deleted_at=datetime.utcnow()))
        db.session.add(Contact(first_name='Archived', email='person@test.com', deleted_at=datetime.utcnow()))
        msg = MailMessage(mailbox_id=self.box.id, sender='person@test.com', recipients=['me@test.com'], body='<script>never executed</script>', subject='Hello')
        db.session.add(msg)
        db.session.commit()
        result = self.client.get(f'/api/mailboxes/{self.box.id}/messages/{msg.id}', headers=self.headers()).json
        self.assertEqual(result['links']['clients'], [{'id': c.id, 'name': 'Company'}])
        self.assertEqual(len(result['links']['contacts']), 1)
        self.assertFalse(result['is_read'])
        marked = self.client.put(f'/api/mailboxes/{self.box.id}/messages/{msg.id}/read', json={'is_read': True}, headers=self.headers())
        self.assertTrue(marked.json['is_read'])

    @patch('app.api.mailboxes.test_connection')
    def test_connect_validates_both_servers_without_sending(self, connect):
        data = dict(name='Shared', email='office@test.com', username='office@test.com', password='app-password',
                    team_id=1, imap_host='imap.test.com', smtp_host='smtp.test.com')
        res = self.client.post('/api/mailboxes', json=data, headers=self.headers())
        self.assertEqual(res.status_code, 201)
        connect.assert_called_once()
        self.assertEqual(res.json['team_id'], 1)
        self.assertIsNone(res.json['user_id'])
        self.assertEqual(self.client.post('/api/mailboxes', json=data, headers=self.headers(2)).status_code, 403)
        data['imap_port'] = 'oops'
        self.assertEqual(self.client.post('/api/mailboxes', json=data, headers=self.headers()).status_code, 400)

    @patch('app.services.mailbox_service.smtp_connection')
    def test_send_signature_and_sent_history(self, connection):
        smtp = connection.return_value.__enter__.return_value
        smtp.send_message.return_value = {}
        self.box.signature = 'Jane\nCompany'
        db.session.commit()
        res = self.client.post(f'/api/mailboxes/{self.box.id}/send', json={'to': 'client@test.com', 'subject': 'Hello', 'body': 'Message'}, headers=self.headers())
        self.assertEqual(res.status_code, 201)
        self.assertIn('Jane\nCompany', res.json['message']['body'])
        self.assertEqual(res.json['message']['folder'], 'sent')
        smtp.send_message.assert_called_once()
        res = self.client.post(f'/api/mailboxes/{self.box.id}/send', json={'to': 'bad\r\nBcc: secret@test.com', 'subject': 'Hello', 'body': 'Message'}, headers=self.headers())
        self.assertEqual(res.status_code, 400)
        self.assertEqual(smtp.send_message.call_count, 1)

    @patch('app.services.mailbox_service.imap_connection')
    def test_sync_is_idempotent_and_uidvalidity_aware(self, connection):
        conn = connection.return_value.__enter__.return_value
        conn.select.return_value = ('OK', [b'1'])
        conn.response.return_value = ('UIDVALIDITY', [b'99'])
        header = b'From: client@test.com\r\nTo: me@test.com\r\nSubject: Hello\r\n\r\n'
        def fetch(op, *args):
            if op == 'search':
                return 'OK', [b'1']
            query = args[1]
            if query == '(FLAGS)':
                return 'OK', [b'1 (UID 1 FLAGS (\\Seen))']
            if 'BODYSTRUCTURE' in query:
                return 'OK', [b'1 (UID 1 BODYSTRUCTURE ("TEXT" "PLAIN" ("CHARSET" "UTF-8") NIL NIL "7BIT" 4 1) FLAGS (\\Seen))']
            literal = header if '[HEADER]' in query else b'Body'
            return 'OK', [(b'1 (UID 1 BODY[1] {4}', literal), b')']
        conn.uid.side_effect = fetch
        self.assertEqual(sync_inbox(self.box)['imported'], 1)
        self.assertEqual(sync_inbox(self.box)['imported'], 0)
        conn.response.return_value = ('UIDVALIDITY', [b'100'])
        self.assertEqual(sync_inbox(self.box)['imported'], 1)
        self.assertEqual(MailMessage.query.count(), 2)

    def test_html_mail_is_plain_text(self):
        msg = BytesParser(policy=policy.default).parsebytes(b'Content-Type: text/html; charset=utf-8\r\n\r\n<p>Hello</p><script>alert(1)</script><img src="https://tracking.test/pixel">')
        self.assertIn('Hello', message_body(msg))
        self.assertNotIn('alert', message_body(msg))
        self.assertNotIn('tracking', message_body(msg))

    def test_invalid_template_cannot_be_saved(self):
        res = self.client.post('/api/templates', json={'name': 'Broken', 'type': 'document', 'content': '{% if %}'}, headers=self.headers())
        self.assertEqual(res.status_code, 400)

    @patch('app.services.mailbox_service.smtp_connection')
    def test_reply_keeps_thread_headers(self, connection):
        smtp = connection.return_value.__enter__.return_value
        smtp.send_message.return_value = {}
        original = MailMessage(mailbox_id=self.box.id, sender='client@test.com', recipients=['me@test.com'], message_id='<original@test.com>')
        db.session.add(original)
        db.session.commit()
        res = self.client.post(f'/api/mailboxes/{self.box.id}/send', json={'to': 'client@test.com', 'subject': 'Re: Hello', 'body': 'Reply', 'reply_to_id': original.id}, headers=self.headers())
        self.assertEqual(res.status_code, 201)
        sent = smtp.send_message.call_args.args[0]
        self.assertEqual(sent['In-Reply-To'], '<original@test.com>')
        self.assertEqual(sent['References'], '<original@test.com>')

    @patch('app.services.mailbox_service.imap_connection')
    def test_sync_never_fetches_attachment_contents(self, connection):
        conn = connection.return_value.__enter__.return_value
        conn.select.return_value = ('OK', [b'1'])
        conn.response.return_value = ('UIDVALIDITY', [b'99'])
        header = b'From: client@test.com\r\nTo: me@test.com\r\nCc: copy@test.com\r\nSubject: HTML mail\r\n\r\n'
        structure = b'1 (UID 1 BODYSTRUCTURE (("TEXT" "HTML" ("CHARSET" "UTF-8") NIL NIL "7BIT" 45 1 NIL NIL)("APPLICATION" "PDF" ("NAME" "offer.pdf") NIL NIL "BASE64" 8 NIL ("ATTACHMENT" ("FILENAME" "offer.pdf"))) "MIXED") FLAGS ())'
        def fetch(op, *args):
            if op == 'search':
                return 'OK', [b'1']
            query = args[1]
            if 'BODYSTRUCTURE' in query:
                return 'OK', [structure]
            self.assertNotIn('BODY.PEEK[]', query)
            self.assertNotIn('[2]', query)
            raw = header if '[HEADER]' in query else b'<p style="color:red">Hello</p><script>bad()</script>'
            return 'OK', [(b'1 (UID 1 BODY[1] {45}', raw), b')']
        conn.uid.side_effect = fetch
        self.assertEqual(sync_inbox(self.box)['imported'], 1)
        msg = MailMessage.query.first()
        self.assertIn('color:red', msg.body_html)
        self.assertNotIn('script', msg.body_html)
        self.assertEqual(msg.cc, ['copy@test.com'])
        self.assertEqual(msg.attachments[0]['filename'], 'offer.pdf')
        self.assertNotIn('data', msg.attachments[0])

    @patch('app.services.mailbox_service.imap_connection')
    def test_attachment_is_fetched_only_on_explicit_download(self, connection):
        conn = connection.return_value.__enter__.return_value
        conn.select.return_value = ('OK', [b'1'])
        conn.response.return_value = ('UIDVALIDITY', [b'99'])
        conn.uid.return_value = ('OK', [(b'1 BODY[2] {8}', b'UERG'), b')'])
        msg = MailMessage(mailbox_id=self.box.id, sender='client@test.com', remote_uid='99:1', attachments=[{'part':'2','filename':'offer.pdf','encoding':'base64','size':4}])
        db.session.add(msg)
        db.session.commit()
        url = f'/api/mailboxes/{self.box.id}/messages/{msg.id}/attachments/2'
        self.assertEqual(self.client.get(url, headers=self.headers(2)).status_code, 404)
        conn.uid.assert_not_called()
        self.client.get(f'/api/mailboxes/{self.box.id}/messages/{msg.id}', headers=self.headers())
        conn.uid.assert_not_called()
        result = self.client.get(url, headers=self.headers())
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data, b'PDF')
        self.assertIn('attachment', result.headers['Content-Disposition'])
        conn.uid.assert_called_once_with('fetch', '1', '(BODY.PEEK[2])')

    @patch('app.services.mailbox_service.smtp_connection')
    def test_english_forward_headers_preserve_original_message_and_signature(self, connection):
        smtp = connection.return_value.__enter__.return_value
        smtp.send_message.return_value = {}
        self.box.signature_format = 'text'
        self.box.signature = 'Moja własna stopka'
        original = MailMessage(mailbox_id=self.box.id, sender='client@test.com', recipients=['me@test.com'],
                               subject='Moja umowa', body='Oryginalna treść klienta')
        db.session.add(original)
        db.session.commit()
        headers = {**self.headers(), 'Accept-Language': 'en'}
        response = self.client.post(f'/api/mailboxes/{self.box.id}/send', headers=headers, json={
            'to': 'other@test.com', 'subject': 'Fwd: Moja umowa', 'body': 'Moja wiadomość',
            'forward_message_id': original.id,
        })
        self.assertEqual(response.status_code, 201)
        sent = smtp.send_message.call_args.args[0].get_body(preferencelist=('plain',)).get_content()
        self.assertIn('Forwarded message', sent)
        self.assertIn('From: client@test.com\nTo: me@test.com\nSubject: Moja umowa', sent)
        self.assertIn('Oryginalna treść klienta', sent)
        self.assertIn('Moja własna stopka', sent)
        self.assertIn('Moja wiadomość', sent)

    @patch('app.services.mailbox_service.smtp_connection')
    def test_cc_bcc_html_signature_and_forward(self, connection):
        smtp = connection.return_value.__enter__.return_value
        smtp.send_message.return_value = {}
        self.box.signature_format = 'html'
        self.box.signature = '<strong>Jane</strong><a href="https://example.com">Company</a>'
        original = MailMessage(mailbox_id=self.box.id, sender='original@test.com', recipients=['me@test.com'], subject='Original', body='Original text', body_html='<p><b>Original HTML</b></p>')
        db.session.add(original)
        db.session.commit()
        result = self.client.post(f'/api/mailboxes/{self.box.id}/send', json={'to':'to@test.com','cc':'cc@test.com','bcc':'hidden@test.com','subject':'Fwd: Original','body':'See below','forward_message_id':original.id}, headers=self.headers())
        self.assertEqual(result.status_code, 201)
        sent = smtp.send_message.call_args.args[0]
        self.assertEqual(sent['Cc'], 'cc@test.com')
        self.assertIsNone(sent['Bcc'])
        self.assertIn('hidden@test.com', smtp.send_message.call_args.kwargs['to_addrs'])
        self.assertNotIn('hidden@test.com', sent.as_string())
        html = sent.get_body(preferencelist=('html',)).get_content()
        self.assertIn('<strong>Jane</strong>', html)
        self.assertIn('Original HTML', html)
        self.assertEqual(result.json['message']['bcc'], ['hidden@test.com'])

    @patch('app.services.mailbox_service.imap_connection')
    def test_read_status_updates_imap_and_filters(self, connection):
        conn = connection.return_value.__enter__.return_value
        conn.select.return_value = ('OK', [b'1'])
        conn.response.return_value = ('UIDVALIDITY', [b'99'])
        conn.uid.return_value = ('OK', [])
        msg = MailMessage(mailbox_id=self.box.id, remote_uid='99:1', sender='client@test.com')
        db.session.add(msg)
        db.session.commit()
        self.assertEqual(self.client.get(f'/api/mailboxes/{self.box.id}/messages?status=unread', headers=self.headers()).json['total'], 1)
        result = self.client.put(f'/api/mailboxes/{self.box.id}/messages/{msg.id}/read', json={'is_read':True}, headers=self.headers())
        self.assertEqual(result.status_code, 200)
        conn.uid.assert_called_with('store', '1', '+FLAGS.SILENT', r'(\Seen)')
        self.assertEqual(self.client.get(f'/api/mailboxes/{self.box.id}/messages?status=unread', headers=self.headers()).json['total'], 0)
        self.client.put(f'/api/mailboxes/{self.box.id}/messages/{msg.id}/read', json={'is_read':False}, headers=self.headers())
        conn.uid.assert_called_with('store', '1', '-FLAGS.SILENT', r'(\Seen)')

    def test_sanitizer_removes_active_content_but_preserves_formatting(self):
        html = sanitize_mail_html('<table><tr><td style="color:red;background-image:url(https://bad.test)"><b>Hello</b></td></tr></table><script>alert(1)</script><img src="cid:attachment" onerror="bad()"><a href="javascript:bad()">link</a>')
        self.assertIn('<table>', html)
        self.assertIn('<b>Hello</b>', html)
        self.assertIn('color:red', html)
        for bad in ('script', 'alert', 'onerror', 'javascript', 'cid:', 'background-image'):
            self.assertNotIn(bad, html)

    @patch('app.services.mailbox_service.imap_connection')
    def test_full_sync_paginates_beyond_latest_100_without_duplicates(self, connection):
        conn = connection.return_value.__enter__.return_value
        conn.select.return_value = ('OK', [b'150'])
        conn.response.return_value = ('UIDVALIDITY', [b'99'])
        db.session.add_all([MailMessage(mailbox_id=self.box.id, remote_uid=f'99:{uid}', sender='client@test.com', content_version=2) for uid in range(1,151)])
        db.session.commit()
        conn.uid.side_effect = lambda op, *args: ('OK', [b' '.join(str(v).encode() for v in range(1,151))]) if op == 'search' else ('OK', [b'1 (FLAGS ())'])
        first = sync_inbox(self.box, all_messages=True)
        second = sync_inbox(self.box, all_messages=True, before_uid=first['next_before_uid'])
        third = sync_inbox(self.box, all_messages=True, before_uid=second['next_before_uid'])
        self.assertEqual(first['processed'] + second['processed'] + third['processed'], 150)
        self.assertIsNone(third['next_before_uid'])
        self.assertEqual(MailMessage.query.count(), 150)
        self.assertTrue(all(call.args[0] == 'search' or call.args[2] == '(FLAGS)' for call in conn.uid.call_args_list))
