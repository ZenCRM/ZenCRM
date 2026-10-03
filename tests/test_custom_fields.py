import unittest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.client import Client
from app.models.user import User


class CustomFieldsTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        admin = User(email='admin@test.local', password_hash='unused', first_name='Admin', last_name='Test', role='admin')
        client = Client(name='Klient z polami')
        db.session.add_all([admin, client])
        db.session.commit()
        self.admin_id = admin.id
        self.client_id = client.id
        self.client = self.app.test_client()
        self.headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(self.admin_id))}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_custom_fields_crud_and_values(self):
        # 1. Initially empty
        res = self.client.get('/api/custom-fields', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), [])

        # Values for record with 0 fields
        res = self.client.get(f'/api/custom-fields/clients/{self.client_id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), {})

        # 2. Create boolean, number, text fields
        bool_field = self.client.post('/api/custom-fields', json={
            'entity': 'clients', 'label': 'Zgoda marketingowa', 'kind': 'boolean'
        }, headers=self.headers).get_json()
        num_field = self.client.post('/api/custom-fields', json={
            'entity': 'clients', 'label': 'Rabat procentowy', 'kind': 'number'
        }, headers=self.headers).get_json()
        text_field = self.client.post('/api/custom-fields', json={
            'entity': 'clients', 'label': 'Numer umowy', 'kind': 'text'
        }, headers=self.headers).get_json()

        # 3. Save values with boolean true/false and comma-separated float
        res = self.client.put(f'/api/custom-fields/clients/{self.client_id}', json={
            str(bool_field['id']): True,
            str(num_field['id']): '15,5',
            str(text_field['id']): 'UM/2026/01',
        }, headers=self.headers)
        self.assertEqual(res.status_code, 200)

        # 4. Read values back
        values = self.client.get(f'/api/custom-fields/clients/{self.client_id}', headers=self.headers).get_json()
        self.assertEqual(values[str(bool_field['id'])], 'true')
        self.assertEqual(values[str(num_field['id'])], '15.5')
        self.assertEqual(values[str(text_field['id'])], 'UM/2026/01')

        # 5. Delete field
        del_res = self.client.delete(f'/api/custom-fields/{bool_field["id"]}', headers=self.headers)
        self.assertEqual(del_res.status_code, 200)
        values_after = self.client.get(f'/api/custom-fields/clients/{self.client_id}', headers=self.headers).get_json()
        self.assertNotIn(str(bool_field['id']), values_after)


if __name__ == '__main__':
    unittest.main()
