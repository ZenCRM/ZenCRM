"""Pinned, public HTTPS callbacks with bounded responses and no redirects."""
import hashlib
import hmac
import http.client
import ssl
import time
import socket
import threading
from urllib.parse import urlsplit
from ..services.mailbox_transport import public_socket


class PublicHTTPS(http.client.HTTPSConnection):
    def connect(self):
        deadline = getattr(self, 'request_deadline', time.monotonic() + 10)
        sock = public_socket(self.host, self.port, self.timeout, deadline=deadline)
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Plugin callback time budget exceeded')
            sock.settimeout(min(self.timeout, remaining))
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
            if time.monotonic() >= deadline:
                raise TimeoutError('Plugin callback time budget exceeded')
        except Exception:
            sock.close()
            raise


def send_event(url, body, delivery_id, signing_secret):
    parts = urlsplit(url)
    if parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or parts.port not in (None, 443) or parts.fragment or parts.query:
        raise ValueError('Nieprawidłowy adres zdarzeń.')
    timestamp = str(int(time.time()))
    signature = hmac.new(signing_secret.encode(), timestamp.encode() + b'.' + body, hashlib.sha256).hexdigest()
    conn = PublicHTTPS(parts.hostname, 443, timeout=5, context=ssl.create_default_context())
    conn.request_deadline = time.monotonic() + 10
    def interrupt():
        # Interrupt a slow header stream too, not only a completely idle socket.
        try:
            if conn.sock is not None:
                conn.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
    deadline_timer = threading.Timer(10, interrupt)
    deadline_timer.daemon = True
    deadline_timer.start()
    try:
        conn.request('POST', parts.path or '/', body=body,
            headers={'Content-Type': 'application/json', 'X-ZenCRM-Delivery': delivery_id,
                     'X-ZenCRM-Timestamp': timestamp, 'X-ZenCRM-Signature': 'sha256=' + signature})
        response = conn.getresponse()
        # Status alone is sufficient. Do not consume/log potentially infinite callback bodies.
        return response.status
    finally:
        deadline_timer.cancel()
        conn.close()
