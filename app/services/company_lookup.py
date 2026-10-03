"""Company lookup provider selection and free Ministry of Finance API."""
import re
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
from ..models.setting import Setting
from .gus_service import GusError, normalize_nip


def provider():
    value = Setting.get_value('client_company_provider', '')
    return value if value in ('off', 'gus', 'mf') else ('gus' if Setting.get_value('gus_enabled', 'false') == 'true' else 'off')


def address_fields(address):
    fields = dict(address=address, street='', building_number='', apartment_number='', postal_code='', city='', country='')
    if not address:
        return fields
    match = re.fullmatch(r'\s*(.*?)\s*,?\s*(\d{2}-\d{3})\s+(.+?)\s*', address)
    if not match:
        return fields
    line, fields['postal_code'], fields['city'] = match.groups()
    line = line.strip(' ,')
    number = re.fullmatch(r'(.*?)\s+(\d+[A-Za-z]?(?:[/-]\d+[A-Za-z]?)?)(?:\s+(?:lok\.?|m\.?)\s*(\S+))?', line)
    if number:
        fields['street'], fields['building_number'], apartment = number.groups()
        fields['apartment_number'] = apartment or ''
    else:
        fields['street'] = line
    fields['country'] = 'Polska'
    return fields


def lookup_mf(nip):
    nip = normalize_nip(nip)
    date = datetime.now(ZoneInfo('Europe/Warsaw')).date().isoformat()
    try:
        response = requests.get(f'https://wl-api.mf.gov.pl/api/search/nip/{nip}', params={'date': date}, headers={'Accept': 'application/json'}, timeout=(5, 15))
        if response.status_code == 429:
            raise GusError('Przekroczono limit zapytań API Ministerstwa Finansów. Spróbuj ponownie później.')
        response.raise_for_status()
        payload = response.json()
        result = payload.get('result')
        if not isinstance(result, dict):
            raise GusError('Ministerstwo Finansów zwróciło niepoprawną odpowiedź.')
        subject = result.get('subject')
        if subject is None:
            return None
        if not isinstance(subject, dict) or not isinstance(subject.get('name'), str):
            raise GusError('Ministerstwo Finansów zwróciło niepoprawną odpowiedź.')
        address = subject.get('workingAddress') or subject.get('residenceAddress') or ''
        if not isinstance(address, str):
            raise GusError('Ministerstwo Finansów zwróciło niepoprawną odpowiedź.')
        return {'company': subject['name'], 'nip': subject.get('nip') or nip,
                'regon': subject.get('regon') or '', 'krs': subject.get('krs') or '',
                **address_fields(address)}
    except (requests.RequestException, ValueError, AttributeError) as exc:
        raise GusError('Nie udało się pobrać danych z Ministerstwa Finansów. Spróbuj ponownie później.') from exc
