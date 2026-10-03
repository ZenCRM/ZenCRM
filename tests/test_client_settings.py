import json
import unittest
from unittest.mock import patch, Mock
from flask_jwt_extended import create_access_token
import test_task_permissions as task_tests
from app.extensions import db
from app.models.setting import Setting
from app.models.client import Client
from app.services.company_lookup import lookup_mf, address_fields
from app.services.gus_service import GusError


class ClientSettingsTest(unittest.TestCase):
    setUp = task_tests.TaskPermissionsTest.setUp
    tearDown = task_tests.TaskPermissionsTest.tearDown

    def headers(self):
        return {'Authorization': 'Bearer ' + create_access_token(identity='3')}

    def test_custom_statuses_and_used_status_protection(self):
        statuses = [{'id': 'vip', 'label': 'Klient VIP', 'accent': '#123456'}]
        response = self.client.put('/api/settings', headers=self.headers(), json={'client_statuses': json.dumps(statuses)})
        self.assertEqual(response.status_code, 200, response.json)
        response = self.client.post('/api/clients', headers=self.headers(), json={'name': 'VIP'})
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['status'], 'vip')
        self.assertEqual(self.client.post('/api/clients', headers=self.headers(), json={'name': 'Invalid', 'status': 'active'}).status_code, 400)
        client = db.session.get(Client, response.json['id'])
        from datetime import datetime
        client.deleted_at = datetime.utcnow()
        db.session.commit()
        other = [{'id': 'other', 'label': 'Inny', 'accent': '#654321'}]
        response = self.client.put('/api/settings', headers=self.headers(), json={'client_statuses': json.dumps(other)})
        self.assertEqual(response.status_code, 400)
        statuses[0]['label'] = 'Nowa nazwa'
        self.assertEqual(self.client.put('/api/settings', headers=self.headers(), json={'client_statuses': json.dumps(statuses)}).status_code, 200)
        self.assertEqual(self.client.post('/api/settings/reset', headers=self.headers()).status_code, 400)

    def test_mf_no_key_mapping_and_provider_routing(self):
        response = self.client.put('/api/settings', headers=self.headers(), json={'client_company_provider': 'mf'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['gus_enabled'], 'false')
        http = Mock(status_code=200)
        http.json.return_value = {'result': {'subject': {'name': 'Firma', 'nip': '5261040828', 'regon': '000331501', 'krs': '0000123456', 'workingAddress': 'Krucza 208 lok. 2, 00-925 Warszawa'}}}
        with patch('app.services.company_lookup.requests.get', return_value=http) as network:
            result = self.client.get('/api/clients/company-lookup?nip=5261040828', headers=self.headers())
            self.assertEqual(result.status_code, 200, result.json)
            self.assertEqual(result.json['building_number'], '208')
            self.assertEqual(result.json['apartment_number'], '2')
            self.assertEqual(result.json['krs'], '0000123456')
            self.assertIn('date', network.call_args.kwargs['params'])
            self.assertNotIn('Authorization', network.call_args.kwargs['headers'])
        self.assertEqual(self.client.put('/api/settings', headers=self.headers(), json={'client_company_provider': 'invalid'}).status_code, 400)

    def test_mf_not_found_limit_bad_response(self):
        http = Mock(status_code=200)
        http.json.return_value = {'result': {'subject': None}}
        with patch('app.services.company_lookup.requests.get', return_value=http):
            self.assertIsNone(lookup_mf('5261040828'))
            http.status_code = 429
            with self.assertRaises(GusError): lookup_mf('5261040828')
            http.status_code = 200
            http.json.return_value = []
            with self.assertRaises(GusError): lookup_mf('5261040828')
        self.assertEqual(address_fields('Niestandardowy adres')['address'], 'Niestandardowy adres')
        self.assertEqual(address_fields('Chmielna 85/87 00-805 Warszawa')['building_number'], '85/87')

    def test_metrics_limit_colors_and_employee_visibility(self):
        metrics = [{'id': 'all', 'color': '#abcdef'}, {'id': 'status:active', 'color': '#123456'}]
        saved = self.client.put('/api/settings', headers=self.headers(), json={'client_metrics': json.dumps(metrics)})
        self.assertEqual(saved.status_code, 200, saved.json)
        ui = self.client.get('/api/settings/ui', headers={'Authorization': 'Bearer ' + create_access_token(identity='1')})
        self.assertEqual(json.loads(ui.json['client_metrics']), metrics)
        for value in [metrics * 4, [{'id': 'all', 'color': 'red'}], metrics * 2, [{'id': 'unknown', 'color': '#abcdef'}]]:
            response = self.client.put('/api/settings', headers=self.headers(), json={'client_metrics': json.dumps(value)})
            self.assertEqual(response.status_code, 400)
        hidden = self.client.put('/api/settings', headers=self.headers(), json={'client_metrics': '[]'})
        self.assertEqual(hidden.status_code, 200)
