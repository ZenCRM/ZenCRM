"""GUS BIR1 lookup. Credentials stay on the server."""
import re
from email import policy
from email.parser import BytesParser
from xml.sax.saxutils import escape

import requests
from flask import current_app
from lxml import etree

PRODUCTION_URL = 'https://wyszukiwarkaregon.stat.gov.pl/wsBIR/UslugaBIRzewnPubl.svc'
TEST_URL = 'https://wyszukiwarkaregontest.stat.gov.pl/wsBIR/UslugaBIRzewnPubl.svc'
NS = 'http://CIS/BIR/PUBL/2014/07'
DATA_NS = 'http://CIS/BIR/PUBL/2014/07/DataContract'


class GusError(Exception):
    pass


def normalize_nip(value):
    if not isinstance(value, str):
        raise ValueError('Podaj poprawny NIP (10 cyfr).')
    nip = re.sub(r'[\s-]', '', value)
    if not re.fullmatch(r'[0-9]{10}', nip) or sum(int(n) * w for n, w in zip(nip[:9], (6, 5, 7, 2, 3, 4, 5, 6, 7))) % 11 != int(nip[-1]):
        raise ValueError('Podaj poprawny NIP (10 cyfr i poprawna suma kontrolna).')
    return nip


def _xml(content):
    return etree.fromstring(content, parser=etree.XMLParser(resolve_entities=False, no_network=True))


def _call(session, url, method, body, sid=None):
    action = f'{NS}/IUslugaBIRzewnPubl/{method}'
    envelope = f'''<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope" xmlns:a="http://www.w3.org/2005/08/addressing"><s:Header><a:Action s:mustUnderstand="1">{action}</a:Action><a:To s:mustUnderstand="1">{url}</a:To></s:Header><s:Body><{method} xmlns="{NS}">{body}</{method}></s:Body></s:Envelope>'''
    headers = {'Content-Type': f'application/soap+xml; charset=utf-8; action="{action}"'}
    if sid:
        headers['sid'] = sid
    response = session.post(url, data=envelope.encode('utf-8'), headers=headers, timeout=(5, 15))
    response.raise_for_status()
    content = response.content
    content_type = response.headers.get('Content-Type', '')
    if content_type.lower().startswith('multipart/'):
        mime = BytesParser(policy=policy.default).parsebytes(b'Content-Type: ' + content_type.encode() + b'\r\nMIME-Version: 1.0\r\n\r\n' + content)
        parts = [p for p in mime.walk() if p.get_content_type() in ('application/xop+xml', 'application/soap+xml', 'text/xml')]
        if not parts:
            raise GusError('GUS zwrócił niepoprawną odpowiedź.')
        content = parts[0].get_payload(decode=True)
    root = _xml(content)
    if root.xpath('//*[local-name()="Fault"]'):
        raise GusError('GUS nie może teraz obsłużyć wyszukiwania. Spróbuj ponownie później.')
    nodes = root.xpath(f'//*[local-name()="{method}Result"]')
    if not nodes:
        raise GusError('GUS zwrócił niepoprawną odpowiedź.')
    return nodes[0].text or ''


def gus_enabled():
    from .company_lookup import provider
    return provider() == 'gus'


def lookup_company(nip):
    from ..models.setting import Setting
    if not gus_enabled():
        raise GusError('Wyszukiwarka GUS jest wyłączona w ustawieniach CRM.')
    nip = normalize_nip(nip)
    key = Setting.get_value('gus_api_key', '') or current_app.config.get('GUS_API_KEY', '')
    if not key:
        raise GusError('Integracja GUS nie jest skonfigurowana. Administrator musi dodać klucz API w ustawieniach CRM → GUS.')
    url = TEST_URL if current_app.config.get('GUS_TEST_MODE') else PRODUCTION_URL
    sid = None
    with requests.Session() as session:
        try:
            sid = _call(session, url, 'Zaloguj', f'<pKluczUzytkownika>{escape(key)}</pKluczUzytkownika>')
            if not sid:
                raise GusError('Nie udało się zalogować do GUS. Sprawdź klucz API.')
            result = _call(session, url, 'DaneSzukajPodmioty', f'<pParametryWyszukiwania xmlns:d="{DATA_NS}"><d:Nip>{nip}</d:Nip></pParametryWyszukiwania>', sid)
            if not result.strip():
                return None
            root = _xml(result.encode('utf-8'))
            rows = root.xpath('//*[local-name()="dane"]')
            if not rows:
                return None
            records = [{etree.QName(c).localname: c.text or '' for c in row} for row in rows]
            # Prefer a headquarters entry over a local unit.
            record = next((r for r in records if len(r.get('Regon', '')) == 9), records[0])
            return {
                'company': record.get('Nazwa', ''), 'nip': record.get('Nip') or nip,
                'regon': record.get('Regon', ''), 'street': record.get('Ulica', ''),
                'building_number': record.get('NrNieruchomosci', ''),
                'apartment_number': record.get('NrLokalu', ''),
                'postal_code': record.get('KodPocztowy', ''),
                'city': record.get('Miejscowosc', ''), 'country': 'Polska',
            }
        except (requests.RequestException, etree.XMLSyntaxError) as exc:
            raise GusError('Nie udało się połączyć z GUS. Spróbuj ponownie później.') from exc
        finally:
            if sid:
                try:
                    _call(session, url, 'Wyloguj', f'<pIdentyfikatorSesji>{escape(sid)}</pIdentyfikatorSesji>', sid)
                except (requests.RequestException, etree.XMLSyntaxError, GusError):
                    pass
