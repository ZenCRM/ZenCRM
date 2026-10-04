import socket
import unittest
import time
from unittest.mock import patch, Mock
from app.services.mailbox_transport import public_socket, PublicIMAP, PublicSMTPSSL
from app.services.mailbox_imap import fetch_literal


class MailboxTransportTest(unittest.TestCase):
    def addresses(self, *ips):
        return [(socket.AF_INET6 if ':' in ip else socket.AF_INET, socket.SOCK_STREAM, 6, '', (ip,993)) for ip in ips]

    def test_nonpublic_and_mixed_dns_never_connect(self):
        for ip in ('127.0.0.1','10.0.0.1','169.254.169.254','192.168.1.1','::1','fc00::1','::ffff:127.0.0.1','224.0.0.1','64:ff9b::7f00:1','2002:7f00:1::'):
            with self.subTest(ip=ip), patch('socket.getaddrinfo',return_value=self.addresses('8.8.8.8',ip)), patch('socket.socket') as sock:
                with self.assertRaises(ValueError): public_socket('mail.example',993,20)
                sock.assert_not_called()

    def test_public_address_is_pinned_without_second_dns_lookup(self):
        with patch('socket.getaddrinfo',return_value=self.addresses('8.8.8.8')) as dns, patch('socket.socket') as sock:
            public_socket('mail.example',993,20)
            dns.assert_called_once()
            sock.return_value.connect.assert_called_once_with(('8.8.8.8',993))

    def test_tls_checks_original_hostname_and_closes_failed_socket(self):
        smtp = object.__new__(PublicSMTPSSL)
        smtp.context = Mock()
        smtp.context.wrap_socket.side_effect = ValueError('certificate mismatch')
        with patch('app.services.mailbox_transport.public_socket') as connect:
            with self.assertRaises(ValueError): smtp._get_socket('mail.example',465,20)
            smtp.context.wrap_socket.assert_called_once_with(connect.return_value,server_hostname='mail.example')
            connect.return_value.close.assert_called_once()

    def test_oversized_imap_literal_rejected_before_read(self):
        conn = object.__new__(PublicIMAP)
        with patch('imaplib.IMAP4.read') as read:
            with self.assertRaises(ValueError): conn.read(conn.max_literal + 1)
            read.assert_not_called()

    def test_literal_limit_restored_and_actual_payload_checked(self):
        conn = Mock(max_literal=123)
        conn.uid.return_value = ('OK',[(b'BODY[1]',b'oversize')])
        with self.assertRaises(ValueError): fetch_literal(conn,'1','1',max_bytes=4)
        self.assertEqual(conn.max_literal,123)
        conn.uid.side_effect = OSError('disconnected')
        with self.assertRaises(OSError): fetch_literal(conn,'1','1',max_bytes=4)
        self.assertEqual(conn.max_literal,123)

    def test_transport_deadline_and_byte_budget_stop_before_read(self):
        conn = object.__new__(PublicIMAP)
        conn.sock = Mock()
        conn.deadline = time.monotonic() - 1
        with patch('imaplib.IMAP4.read') as read:
            with self.assertRaises(TimeoutError):
                conn.read(1)
            read.assert_not_called()

        conn.deadline = None
        conn.remaining_bytes = 1
        with patch('imaplib.IMAP4.read') as read:
            with self.assertRaises(RuntimeError):
                conn.read(2)
            read.assert_not_called()

    def test_oversized_protocol_line_is_a_recoverable_content_error(self):
        conn = object.__new__(PublicIMAP)
        import imaplib
        with patch('imaplib.IMAP4.readline', side_effect=imaplib.IMAP4.error('got more than 1000000 bytes')):
            with self.assertRaises(ValueError):
                conn.readline()
        with patch('imaplib.IMAP4.readline', side_effect=imaplib.IMAP4.abort('disconnected')):
            with self.assertRaises(imaplib.IMAP4.abort):
                conn.readline()
