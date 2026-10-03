import unittest
from unittest.mock import patch
from flask_jwt_extended import create_access_token
import test_task_permissions as task_tests
from app.services.gus_service import GusError, normalize_nip, lookup_company


class ClientCompanyTest(unittest.TestCase):
    setUp = task_tests.TaskPermissionsTest.setUp
    tearDown = task_tests.TaskPermissionsTest.tearDown

    def headers(self):
        return {'Authorization': 'Bearer ' + create_access_token(identity='3')}

    def test_create_update_address_and_identifiers(self):
        response = self.client.post('/api/clients', headers=self.headers(), json={
            'name': 'Firma', 'nip': '526-104-08-28', 'regon': '000331501', 'krs': '0000123456',
            'street': 'Krucza', 'building_number': '208', 'apartment_number': '2',
            'postal_code': '00-925', 'city': 'Warszawa', 'country': 'Polska'})
        self.assertEqual(response.status_code, 201, response.get_json())
        data = response.get_json()
        self.assertEqual(data['nip'], '5261040828')
        self.assertEqual(data['krs'], '0000123456')
        self.assertEqual(data['address'], 'Krucza 208/2, 00-925 Warszawa, Polska')
        updated = self.client.put(f"/api/clients/{data['id']}", headers=self.headers(), json={'city': 'Kraków'})
        self.assertEqual(updated.status_code, 200)
        self.assertIn('Kraków', updated.get_json()['address'])
        cleared = self.client.put(f"/api/clients/{data['id']}", headers=self.headers(), json={key: '' for key in ('street', 'building_number', 'apartment_number', 'postal_code', 'city', 'country')})
        self.assertIsNone(cleared.get_json()['address'])

    def test_optional_identifiers_and_legacy_address(self):
        created = self.client.post('/api/clients', headers=self.headers(), json={'name': 'Osoba', 'address': 'Stary adres'}).get_json()
        updated = self.client.put(f"/api/clients/{created['id']}", headers=self.headers(), json={'name': 'Nowa nazwa', 'street': None, 'city': None})
        self.assertEqual(updated.get_json()['address'], 'Stary adres')
        self.assertIsNone(updated.get_json()['nip'])

    def test_invalid_identifiers(self):
        for field, value in [('nip', '1234567890'), ('regon', '123'), ('krs', '12'), ('city', 3)]:
            response = self.client.post('/api/clients', headers=self.headers(), json={'name': 'Firma', field: value})
            self.assertEqual(response.status_code, 400, field)

    def test_lookup_authenticated_and_results(self):
        self.assertEqual(self.client.get('/api/clients/gus?nip=5261040828').status_code, 401)
        from app.models.setting import Setting
        from app.extensions import db
        self.assertEqual(self.client.get('/api/clients/gus?nip=5261040828', headers=self.headers()).status_code, 403)
        Setting.set_value('gus_enabled', 'true')
        db.session.commit()
        company = {'company': 'GUS', 'nip': '5261040828', 'regon': '000331501', 'city': 'Warszawa'}
        with patch('app.services.gus_service.lookup_company', return_value=company):
            response = self.client.get('/api/clients/gus?nip=5261040828', headers=self.headers())
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_json(), company)
        with patch('app.services.gus_service.lookup_company', return_value=None):
            self.assertEqual(self.client.get('/api/clients/gus?nip=5261040828', headers=self.headers()).status_code, 404)
        with patch('app.services.gus_service.lookup_company', side_effect=GusError('GUS niedostępny')):
            self.assertEqual(self.client.get('/api/clients/gus?nip=5261040828', headers=self.headers()).status_code, 503)

    def test_missing_key_and_nip_checksum(self):
        self.app.config['GUS_API_KEY'] = ''
        self.assertEqual(normalize_nip('526-104-08-28'), '5261040828')
        with self.assertRaises(ValueError):
            normalize_nip('1234567890')
        with self.assertRaises(GusError):
            lookup_company('5261040828')
