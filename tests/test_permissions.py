import unittest

from flask_jwt_extended import create_access_token

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.client import Client
from app.models.team import Team
from app.models.user import User


class PermissionsTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.admin = User(email='admin@local', password_hash='unused', first_name='A', last_name='A', role='admin')
        self.employee = User(email='employee@local', password_hash='unused', first_name='E', last_name='E', role='employee')
        db.session.add_all([self.admin, self.employee])
        db.session.commit()
        self.client = self.app.test_client()
        self.admin_headers = self.headers(self.admin)
        self.employee_headers = self.headers(self.employee)

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def headers(self, user):
        return {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}

    def test_custom_role_grant_and_admin_only_permanent_delete(self):
        created = self.client.post('/api/permissions/roles', json={'name': 'Audytor'}, headers=self.admin_headers)
        self.assertEqual(created.status_code, 201)
        role = created.get_json()['key']
        change = self.client.put(f'/api/users/{self.employee.id}', json={'role': role}, headers=self.admin_headers)
        self.assertEqual(change.status_code, 200)
        self.assertEqual(self.client.post('/api/clients', json={'name': 'Nowy'}, headers=self.employee_headers).status_code, 403)

        grant = self.client.put(f'/api/permissions/roles/{role}/rules',
                                json={'rules': {'clients.create': True, 'clients.delete': True}}, headers=self.admin_headers)
        self.assertEqual(grant.status_code, 200)
        made = self.client.post('/api/clients', json={'name': 'Nowy'}, headers=self.employee_headers)
        self.assertEqual(made.status_code, 201)
        client_id = made.get_json()['id']
        self.assertEqual(self.client.delete(f'/api/clients/{client_id}', headers=self.employee_headers).status_code, 200)
        self.assertEqual(self.client.delete(f'/api/clients/{client_id}/permanent', headers=self.employee_headers).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/archive/clients/{client_id}/permanent', headers=self.employee_headers).status_code, 403)

    def test_team_denial_overrides_role_and_admin_bypasses(self):
        team = Team(name='Sprzedaż', members=[self.employee, self.admin])
        db.session.add(team)
        db.session.commit()
        response = self.client.put(f'/api/permissions/teams/{team.id}/rules',
                                   json={'rules': {'clients.create': False}}, headers=self.admin_headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.post('/api/clients', json={'name': 'Zabroniony'}, headers=self.employee_headers).status_code, 403)
        self.assertEqual(self.client.post('/api/clients', json={'name': 'Dozwolony'}, headers=self.admin_headers).status_code, 201)
        self.assertEqual(self.client.get('/api/permissions/me', headers=self.employee_headers).get_json()['clients.create'], False)

    def test_only_admin_can_manage_rules_and_team_membership(self):
        self.assertEqual(self.client.get('/api/permissions', headers=self.employee_headers).status_code, 403)
        self.assertEqual(self.client.post('/api/permissions/roles', json={'name': 'Nowa'}, headers=self.employee_headers).status_code, 403)
        self.assertEqual(self.client.post('/api/teams', json={'name': 'Moja'}, headers=self.employee_headers).status_code, 403)
        self.assertEqual(self.client.put(f'/api/users/{self.employee.id}', json={'team_ids': []}, headers=self.employee_headers).status_code, 403)
        self.assertEqual(self.client.delete(f'/api/users/{self.admin.id}', headers=self.admin_headers).status_code, 409)


if __name__ == '__main__':
    unittest.main()
