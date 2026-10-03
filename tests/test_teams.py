import unittest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User
from app.models.team import Team


class TeamsTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        admin = User(email='admin@teams.local', password_hash='unused', first_name='Adam', last_name='Admin', role='admin')
        user2 = User(email='dev@teams.local', password_hash='unused', first_name='Piotr', last_name='Dev', role='employee')
        db.session.add_all([admin, user2])
        db.session.commit()

        self.admin = admin
        self.user2 = user2
        self.client = self.app.test_client()
        self.headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_team_crud_and_members(self):
        # 1. Create team
        res = self.client.post('/api/teams', json={
            'name': 'Dział Sprzedaży',
            'description': 'Zespół odpowiedzialny za pozyskiwanie klientów',
            'color': '#10b981',
            'leader_id': self.admin.id,
            'member_ids': [self.user2.id]
        }, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        team_data = res.get_json()
        team_id = team_data['id']
        self.assertEqual(team_data['name'], 'Dział Sprzedaży')
        self.assertEqual(team_data['leader_id'], self.admin.id)
        self.assertEqual(len(team_data['members']), 1)
        self.assertEqual(team_data['members'][0]['id'], self.user2.id)

        # 2. List teams
        res = self.client.get('/api/teams', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        teams = res.get_json()
        self.assertEqual(len(teams), 1)

        # 3. Get team detail
        res = self.client.get(f'/api/teams/{team_id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['name'], 'Dział Sprzedaży')

        # 4. Check user has teams in to_dict
        res = self.client.get(f'/api/users/{self.user2.id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        u_data = res.get_json()
        self.assertTrue(any(t['id'] == team_id for t in u_data.get('teams', [])))

        # 5. Add admin to team via members endpoint
        res = self.client.post(f'/api/teams/{team_id}/members', json={'user_id': self.admin.id}, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()['members']), 2)

        # 6. Remove member from team
        res = self.client.delete(f'/api/teams/{team_id}/members/{self.user2.id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()['members']), 1)

        # 7. Update team
        res = self.client.put(f'/api/teams/{team_id}', json={
            'name': 'Dział Wdrożeń',
            'color': '#8b5cf6'
        }, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['name'], 'Dział Wdrożeń')
        self.assertEqual(res.get_json()['color'], '#8b5cf6')

        # 8. Delete team
        res = self.client.delete(f'/api/teams/{team_id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        res = self.client.get(f'/api/teams/{team_id}', headers=self.headers)
        self.assertEqual(res.status_code, 404)
