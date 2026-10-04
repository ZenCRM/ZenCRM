"""Selective IMAP fetching: headers and text parts, never attachment bodies."""
import re
from email.message import EmailMessage
from email.header import decode_header, make_header
from urllib.parse import unquote


def response_bytes(payload):
    return b' '.join(v[0] if isinstance(v, tuple) else v for v in payload if isinstance(v, (bytes, tuple)))


def parse_structure(payload):
    # Preserve literals inside BODYSTRUCTURE while omitting the header/body literal.
    pieces = []
    for entry in payload:
        if isinstance(entry, tuple):
            prefix, literal = entry
            if re.search(rb'BODY\[HEADER\]', prefix, re.I):
                pieces.append(re.sub(rb'\{\d+\}\s*$', b'', prefix))
            else:
                pieces.extend((prefix + b'\r\n', literal))
        elif isinstance(entry, bytes):
            pieces.append(entry)
    raw = b' '.join(pieces)
    start = re.search(rb'BODYSTRUCTURE\s*\(', raw, re.I)
    if not start:
        raise ValueError('Serwer nie zwrócił struktury MIME wiadomości')
    raw = raw[start.end() - 1:]
    index = 0

    def item(depth=0):
        nonlocal index
        if depth > 30:
            raise ValueError('Zbyt złożona struktura wiadomości')
        while index < len(raw) and raw[index:index + 1].isspace():
            index += 1
        if index >= len(raw):
            raise ValueError('Niepełna struktura MIME')
        char = raw[index:index + 1]
        if char == b'(':
            index += 1
            result = []
            while True:
                while index < len(raw) and raw[index:index + 1].isspace():
                    index += 1
                if raw[index:index + 1] == b')':
                    index += 1
                    return result
                result.append(item(depth + 1))
        if char == b'"':
            index += 1
            result = bytearray()
            while index < len(raw):
                c = raw[index]
                index += 1
                if c == 34:
                    return result.decode('utf-8', 'replace')
                if c == 92 and index < len(raw):
                    c = raw[index]
                    index += 1
                result.append(c)
            raise ValueError('Niepełny tekst MIME')
        if char == b'{':
            end = raw.index(b'}', index)
            length = int(raw[index + 1:end].rstrip(b'+'))
            index = end + 1
            while raw[index:index + 1] in (b' ', b'\r', b'\n'):
                index += 1
            result = raw[index:index + length]
            index += length
            return result.decode('utf-8', 'replace')
        end = index
        while end < len(raw) and raw[end:end + 1] not in (b' ', b')', b'(', b'\r', b'\n'):
            end += 1
        atom = raw[index:end].decode('utf-8', 'replace')
        index = end
        return None if atom.upper() == 'NIL' else atom

    return item()


def parameters(value):
    if not isinstance(value, list):
        return {}
    return {str(value[i]).lower(): value[i + 1] for i in range(0, len(value) - 1, 2)}


def filename(params):
    value = params.get('filename') or params.get('name')
    for key in ('filename', 'name'):
        if params.get(key + '*'):
            value = unquote(str(params[key + '*']).split("'", 2)[-1])
        chunks = sorted((int(re.search(r'\*(\d+)', k).group(1)), v) for k, v in params.items() if re.fullmatch(key + r'\*\d+\*?', k))
        if chunks:
            value = unquote(''.join(str(v) for _, v in chunks).split("'", 2)[-1])
    try:
        return str(make_header(decode_header(str(value))))[:255] if value else ''
    except (ValueError, LookupError):
        return str(value or '')[:255]


def mime_parts(node, prefix=''):
    if not isinstance(node, list) or not node:
        raise ValueError('Nieprawidłowa struktura MIME')
    if isinstance(node[0], list):
        count = next((i for i, child in enumerate(node) if not isinstance(child, list)), len(node))
        subtype = str(node[count]).lower() if count < len(node) else 'mixed'
        params = parameters(node[count + 1]) if len(node) > count + 1 else {}
        disposition = node[count + 2] if len(node) > count + 2 else None
        disp = str(disposition[0]).lower() if isinstance(disposition, list) and disposition else ''
        name = filename({**params, **(parameters(disposition[1]) if isinstance(disposition, list) and len(disposition) > 1 else {})})
        if prefix and (name or disp == 'attachment'):
            return [{'part': prefix, 'content_type': 'multipart/' + subtype, 'encoding': '7bit',
                     'charset': 'utf-8', 'size': sum(p['size'] for child in node[:count] for p in mime_parts(child)),
                     'filename': name or 'załącznik-' + prefix, 'attachment': True}]
        parts = []
        number = 1
        for child in node:
            if not isinstance(child, list):
                break
            parts.extend(mime_parts(child, (prefix + '.' if prefix else '') + str(number)))
            number += 1
        return parts
    if len(node) < 7:
        raise ValueError('Niepełny opis części MIME')
    main, sub = str(node[0]).lower(), str(node[1]).lower()
    params = parameters(node[2])
    disposition_index = 9 if main == 'text' else 11 if main == 'message' and sub == 'rfc822' else 8
    disposition = node[disposition_index] if len(node) > disposition_index else None
    disp = str(disposition[0]).lower() if isinstance(disposition, list) and disposition else ''
    disp_params = parameters(disposition[1]) if isinstance(disposition, list) and len(disposition) > 1 else {}
    name = filename({**params, **disp_params})
    is_attachment = bool(name or disp == 'attachment' or main != 'text' or sub not in ('plain', 'html'))
    return [{'part': prefix or '1', 'content_type': main + '/' + sub,
             'encoding': str(node[5] or '7bit'), 'charset': params.get('charset') or 'utf-8',
             'size': int(node[6] or 0), 'filename': name or ('załącznik-' + (prefix or '1')),
             'attachment': is_attachment}]


def fetch_literal(conn, uid, section, max_bytes=512 * 1024):
    if not re.fullmatch(r'(?:HEADER|\d+(?:\.\d+)*)', section):
        raise ValueError('Nieprawidłowa część wiadomości')
    previous_limit = getattr(conn, 'max_literal', 512 * 1024)
    conn.max_literal = max_bytes
    try:
        status, payload = conn.uid('fetch', uid, f'(BODY.PEEK[{section}])')
    finally:
        conn.max_literal = previous_limit
    if status != 'OK':
        raise ValueError('Nie udało się pobrać treści wiadomości')
    entry = next((v for v in payload if isinstance(v, tuple)), None)
    if not entry:
        raise ValueError('Serwer nie zwrócił treści wiadomości')
    if len(entry[1]) > max_bytes:
        raise ValueError('Dane z serwera poczty przekraczają limit pobierania')
    return entry[1]


def decode_part(raw, part):
    msg = EmailMessage()
    msg['Content-Transfer-Encoding'] = part['encoding']
    msg.set_payload(raw.decode('ascii', 'surrogateescape'))
    return msg.get_payload(decode=True)


def text_part(conn, uid, part):
    raw = decode_part(fetch_literal(conn, uid, part['part'], max_bytes=2 * 1024 * 1024), part)
    try:
        return raw.decode(part['charset'], 'replace')[:1000000]
    except LookupError:
        return raw.decode('utf-8', 'replace')[:1000000]
