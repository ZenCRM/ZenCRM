"""TLS mail transports pinned to verified public DNS addresses."""
import ipaddress
import socket
import imaplib
import smtplib
import time

TRANSITION_NETWORKS = tuple(ipaddress.ip_network(network) for network in
                            ('64:ff9b::/96', '64:ff9b:1::/48', '2002::/16', '2001::/32'))


def public_socket(host, port, timeout, deadline=None):
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError('Nie znaleziono serwera poczty')
    for _, _, _, _, address in addresses:
        ip = ipaddress.ip_address(address[0].split('%')[0])
        ip = getattr(ip, 'ipv4_mapped', None) or ip
        if not ip.is_global or ip.is_multicast or (ip.version == 6 and any(ip in network for network in TRANSITION_NETWORKS)):
            raise ValueError('Serwer poczty musi mieć publiczny adres IP')
    # Connect to the already validated numeric address, without resolving DNS again.
    last_error = None
    for family, kind, protocol, _, address in addresses[:4]:
        remaining = deadline - time.monotonic() if deadline is not None else timeout
        if remaining <= 0:
            raise TimeoutError('Mailbox synchronization time budget exceeded')
        sock = socket.socket(family, kind, protocol)
        sock.settimeout(min(timeout, remaining))
        try:
            sock.connect(address)
            return sock
        except OSError as error:
            last_error = error
            sock.close()
    raise last_error


class PublicSMTP(smtplib.SMTP):
    def _get_socket(self, host, port, timeout):
        return public_socket(host, port, timeout)


class PublicSMTPSSL(smtplib.SMTP_SSL):
    def _get_socket(self, host, port, timeout):
        sock = public_socket(host, port, timeout)
        try:
            return self.context.wrap_socket(sock, server_hostname=host)
        except Exception:
            sock.close()
            raise


class PublicIMAP(imaplib.IMAP4_SSL):
    max_literal = 512 * 1024
    remaining_bytes = 64 * 1024 * 1024
    deadline = None

    def __init__(self, *args, deadline=None, remaining_bytes=64 * 1024 * 1024, **kwargs):
        self.deadline = deadline
        self.remaining_bytes = remaining_bytes
        super().__init__(*args, **kwargs)

    def _check_deadline(self):
        if self.deadline is not None:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Mailbox synchronization time budget exceeded')
            self.sock.settimeout(min(20, remaining))

    def _account_bytes(self, count):
        self.remaining_bytes -= count
        if self.remaining_bytes < 0:
            raise RuntimeError('Mailbox response byte budget exceeded')

    def _create_socket(self, timeout):
        if self.deadline is not None:
            remaining = self.deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Mailbox synchronization time budget exceeded')
            timeout = min(timeout, remaining)
        sock = public_socket(self.host, self.port, timeout, deadline=self.deadline)
        try:
            return self.ssl_context.wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise

    def read(self, size):
        # Reject a dishonest IMAP literal size before imaplib allocates its buffer.
        if size > self.max_literal:
            raise ValueError('Dane z serwera poczty przekraczają limit pobierania')
        self._check_deadline()
        self._account_bytes(size)
        return super().read(size)

    def readline(self):
        self._check_deadline()
        try:
            line = super().readline()
        except imaplib.IMAP4.error as error:
            if str(error).startswith('got more than'):
                raise ValueError('Dane z serwera poczty przekraczają limit pobierania') from None
            raise
        self._account_bytes(len(line))
        return line

    def send(self, data):
        self._check_deadline()
        return super().send(data)
