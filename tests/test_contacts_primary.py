import unittest
from flask_jwt_extended import create_access_token
import test_task_permissions as task_tests
from app.models.client import Client
from app.models.contact import Contact
from app.extensions import db


class ContactsPrimaryTest(unittest.TestCase):
    setUp = task_tests.TaskPermissionsTest.setUp
    tearDown = task_tests.TaskPermissionsTest.tearDown

    def headers(self, user_id=3):
        return {'Authorization': 'Bearer ' + create_access_token(identity=str(user_id))}

    def test_contact_primary_flag_and_exclusivity(self):
        # Utwórz klienta
        client = Client(name='Firma Testowa ABC')
        db.session.add(client)
        db.session.commit()

        # Dodaj kontakt 1 z is_primary=True
        r1 = self.client.post('/api/contacts', json={
            'first_name': 'Jan',
            'last_name': 'Kowalski',
            'client_id': client.id,
            'is_primary': True
        }, headers=self.headers())
        self.assertEqual(r1.status_code, 201)
        c1 = r1.get_json()
        self.assertTrue(c1['is_primary'])

        # Dodaj kontakt 2 z is_primary=True dla tego samego klienta
        r2 = self.client.post('/api/contacts', json={
            'first_name': 'Anna',
            'last_name': 'Nowak',
            'client_id': client.id,
            'is_primary': True
        }, headers=self.headers())
        self.assertEqual(r2.status_code, 201)
        c2 = r2.get_json()
        self.assertTrue(c2['is_primary'])

        # Sprawdź, czy c1 został automatycznie zdemotowany (is_primary=False)
        r1_check = self.client.get(f'/api/contacts/{c1["id"]}', headers=self.headers())
        self.assertEqual(r1_check.status_code, 200)
        self.assertFalse(r1_check.get_json()['is_primary'])

        # Lista kontaktów powinna zwracać kontakt główny na pierwszym miejscu
        list_res = self.client.get(f'/api/contacts?client_id={client.id}', headers=self.headers())
        self.assertEqual(list_res.status_code, 200)
        contacts = list_res.get_json()
        self.assertEqual(len(contacts), 2)
        self.assertEqual(contacts[0]['id'], c2['id'])
        self.assertTrue(contacts[0]['is_primary'])

        # Aktualizacja c1 do is_primary=True powinna zdemotować c2
        up_res = self.client.put(f'/api/contacts/{c1["id"]}', json={
            'is_primary': True
        }, headers=self.headers())
        self.assertEqual(up_res.status_code, 200)
        self.assertTrue(up_res.get_json()['is_primary'])

        r2_check = self.client.get(f'/api/contacts/{c2["id"]}', headers=self.headers())
        self.assertFalse(r2_check.get_json()['is_primary'])

    def test_forgot_password_endpoint(self):
        # Puste zapytanie
        r_empty = self.client.post('/api/auth/forgot-password', json={})
        self.assertEqual(r_empty.status_code, 400)

        # Poprawny adres e-mail
        r_ok = self.client.post('/api/auth/forgot-password', json={'email': 'admin@test.local'})
        self.assertEqual(r_ok.status_code, 200)
        data = r_ok.get_json()
        self.assertTrue(data.get('ok'))
        self.assertIn('message', data)
