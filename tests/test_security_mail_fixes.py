"""Regression checks for the five findings in SECURITY_AUDIT_20261004.md."""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch
import test_mailboxes as fixtures
from app.extensions import db
from app.models.mailbox import MailMessage
from app.models.permission import PermissionRule
from app.models.setting import Setting
from app.services.mailbox_service import sync_inbox
from app.services.email_service import get_smtp_config
from app.services.render_service import render_template_string
from app.utils.permissions import ensure_builtin_roles
from app.utils.secret_storage import migrate_smtp_password, unseal, PREFIX


class SecurityMailFixesTest(unittest.TestCase):
    def setUp(self):
        self.case = fixtures.MailboxesTest()
        self.case.setUp()

    def tearDown(self):
        self.case.tearDown()

    def remote(self, conn, poison='oversize', fail_after=False):
        conn.select.return_value = ('OK', [b'3'])
        conn.response.return_value = ('UIDVALIDITY', [b'99'])

        def fetch(operation, *args):
            if operation == 'search':
                return 'OK', [b'1 2 3']
            uid, query = args
            if uid == '3' and fail_after:
                raise OSError('temporary provider outage')
            if query == '(FLAGS)':
                return 'OK', [b'FLAGS ()']
            if 'BODYSTRUCTURE' in query:
                if uid == '2' and poison == 'malformed':
                    return 'OK', [b'BODYSTRUCTURE (NIL)']
                size = 2097153 if uid == '2' and poison == 'oversize' else 4
                return 'OK', [f'{uid} (BODYSTRUCTURE ("TEXT" "PLAIN" ("CHARSET" "UTF-8") NIL NIL "7BIT" {size} 1) FLAGS ())'.encode()]
            raw = b'From: sender@example.com\r\nSubject: Good mail\r\n\r\n' if '[HEADER]' in query else b'Body'
            if uid == '2' and poison == 'literal' and '[1]' in query:
                raise ValueError('literal rejected before allocation')
            return 'OK', [(b'BODY[1]', raw), b')']
        conn.uid.side_effect = fetch

    def test_oversized_message_is_quarantined_and_not_retried(self):
        with patch('app.services.mailbox_service.imap_connection') as connection:
            conn = connection.return_value.__enter__.return_value
            self.remote(conn)
            result = sync_inbox(self.case.box)
            self.assertEqual((result['imported'], result['skipped']), (2, 1))
            self.assertEqual(MailMessage.query.count(), 3)
            skipped = MailMessage.query.filter_by(remote_uid='99:2').one()
            self.assertEqual(skipped.content_version, -1)
            conn.uid.reset_mock()
            result = sync_inbox(self.case.box)
            self.assertEqual((result['imported'], result['skipped']), (0, 1))
            self.assertFalse(any(call.args[0] == 'fetch' and call.args[1] == '2' for call in conn.uid.call_args_list))

    def test_rejected_literal_and_bad_mime_do_not_block_later_mail(self):
        for poison in ('literal', 'malformed'):
            with self.subTest(poison=poison):
                MailMessage.query.delete()
                db.session.commit()
                with patch('app.services.mailbox_service.imap_connection') as connection:
                    conn = connection.return_value.__enter__.return_value
                    self.remote(conn, poison)
                    result = sync_inbox(self.case.box)
                    self.assertEqual(result['imported'], 2)
                    self.assertEqual(result['skipped'], 1)
                    self.assertGreaterEqual(connection.call_count, 2)
                    conn.shutdown.assert_called()
                    self.assertEqual(MailMessage.query.filter_by(remote_uid='99:3').one().body, 'Body')

    def test_provider_outage_keeps_preceding_messages_and_releases_lease(self):
        with patch('app.services.mailbox_service.imap_connection') as connection:
            self.remote(connection.return_value.__enter__.return_value, poison=None, fail_after=True)
            with self.assertRaises(OSError):
                sync_inbox(self.case.box)
        self.assertEqual(MailMessage.query.count(), 2)
        db.session.refresh(self.case.box)
        self.assertIsNone(self.case.box.sync_claim_token)
        self.assertIsNone(self.case.box.sync_claim_until)

    def test_manual_sync_respects_background_lease(self):
        self.case.box.sync_claim_token = 'background'
        self.case.box.sync_claim_until = datetime.utcnow() + timedelta(minutes=1)
        db.session.commit()
        with patch('app.services.mailbox_service.imap_connection') as connection:
            response = self.case.client.post(f'/api/mailboxes/{self.case.box.id}/sync', json={}, headers=self.case.headers())
            self.assertEqual(response.status_code, 409)
            connection.assert_not_called()
        db.session.refresh(self.case.box)
        self.assertEqual(self.case.box.sync_claim_token, 'background')

    def test_mail_transport_limit_is_shared_across_addresses(self):
        with patch('app.api.mailboxes.send_message', side_effect=ValueError('invalid payload')) as send:
            for index in range(12):
                response = self.case.client.post(f'/api/mailboxes/{self.case.box.id}/send', json={}, headers=self.case.headers(), environ_overrides={'REMOTE_ADDR': f'10.0.0.{index}'})
                self.assertEqual(response.status_code, 400)
            response = self.case.client.post(f'/api/mailboxes/{self.case.box.id}/sync', json={}, headers=self.case.headers(), environ_overrides={'REMOTE_ADDR': '192.0.2.1'})
            self.assertEqual(response.status_code, 429)
            self.assertEqual(send.call_count, 12)

    def test_mail_http_capacity_rejects_excess_work_and_recovers(self):
        from app.utils.mail_limits import _slots
        self.assertTrue(_slots.acquire(blocking=False))
        self.assertTrue(_slots.acquire(blocking=False))
        try:
            with patch('app.api.mailboxes.send_message') as send:
                response = self.case.client.post(f'/api/mailboxes/{self.case.box.id}/send', json={}, headers=self.case.headers())
                self.assertEqual(response.status_code, 429)
                send.assert_not_called()
        finally:
            _slots.release()
            _slots.release()
        with patch('app.api.mailboxes.send_message', side_effect=ValueError('invalid payload')):
            response = self.case.client.post(f'/api/mailboxes/{self.case.box.id}/send', json={}, headers=self.case.headers())
            self.assertEqual(response.status_code, 400)

    def test_preview_requires_template_permission(self):
        ensure_builtin_roles()
        for action in ('create', 'edit'):
            db.session.add(PermissionRule(role_key='employee', permission='templates.' + action, allowed=False))
        db.session.commit()
        with patch('app.api.templates.render_preview') as render:
            response = self.case.client.post('/api/templates/preview', json={'content': 'Hello'}, headers=self.case.headers())
            self.assertEqual(response.status_code, 403)
            render.assert_not_called()

    def test_renderer_bounds_output_memory_cpu_and_preserves_valid_templates(self):
        self.assertEqual(render_template_string('{% for item in items %}{{ item }}{% endfor %}', {'items': ['<safe>', 'text']}), '&lt;safe&gt;text')
        for content in ("{{ 'x' * 3000000 }}", "{{ 'x' * 1000000000 }}",
                        '{% for a in range(100000) %}{% for b in range(100000) %}{% set n = a + b %}{% endfor %}{% endfor %}'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                render_template_string(content, {})
        self.assertEqual(render_template_string('Recovered {{ value }}', {'value': 'ok'}), 'Recovered ok')

    def test_smtp_password_is_encrypted_via_both_write_apis_and_masked(self):
        for path, payload in (('/api/emails/smtp-config', {'password': 'notification-dummy'}),
                              ('/api/settings', {'smtp_password': 'general-settings-dummy'})):
            with self.subTest(path=path):
                response = self.case.client.put(path, json=payload, headers=self.case.headers(3))
                self.assertEqual(response.status_code, 200)
                stored = Setting.get_value('smtp_password')
                expected = next(iter(payload.values()))
                self.assertTrue(stored.startswith(PREFIX))
                self.assertNotIn(expected, stored)
                self.assertEqual(get_smtp_config()['password'], expected)
                self.assertNotIn(stored, response.get_data(as_text=True))
                self.assertNotIn(expected, response.get_data(as_text=True))

    def test_legacy_smtp_migration_is_idempotent_and_does_not_change_password(self):
        raw = ' legacy-dummy with spaces '
        db.session.add(Setting(key='smtp_password', value=raw, category='smtp'))
        db.session.commit()
        migrate_smtp_password()
        stored = Setting.get_value('smtp_password')
        self.assertEqual(unseal(stored), raw)
        migrate_smtp_password()
        self.assertEqual(Setting.get_value('smtp_password'), stored)

    def test_startup_preparation_migrates_legacy_smtp_password(self):
        from app.database import prepare_database, MIGRATIONS_DIR
        from flask_migrate import stamp
        # The fixture uses create_all, so its current schema must be stamped
        # before exercising a restart of an already upgraded installation.
        stamp(directory=MIGRATIONS_DIR, revision='head')
        db.session.add(Setting(key='smtp_password', value='legacy-startup-dummy', category='smtp'))
        db.session.commit()
        prepare_database()
        self.assertTrue(Setting.get_value('smtp_password').startswith(PREFIX))
        self.assertEqual(get_smtp_config()['password'], 'legacy-startup-dummy')

    def test_corrupt_smtp_ciphertext_fails_closed(self):
        db.session.add(Setting(key='smtp_password', value=PREFIX + 'broken', category='smtp'))
        db.session.commit()
        from cryptography.fernet import InvalidToken
        with self.assertRaises(InvalidToken):
            get_smtp_config()


if __name__ == '__main__':
    unittest.main()
