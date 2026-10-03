import unittest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.lead import Lead
from app.models.meeting import Meeting
from app.models.user import User


class MeetingContextTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        user = User(email='admin@meeting.local', password_hash='unused', first_name='A', last_name='A', role='admin')
        lead = Lead(title='Nowy lead', stage='new')
        db.session.add_all([user, lead])
        db.session.commit()
        self.lead_id = lead.id
        self.headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_meeting_stays_with_lead_then_moves_to_client_on_conversion(self):
        created = self.client.post('/api/meetings', json={
            'title': 'Rozmowa', 'start_time': '2026-09-30T10:00:00',
            'end_time': '2026-09-30T10:30:00', 'lead_id': self.lead_id,
        }, headers=self.headers)
        self.assertEqual(created.status_code, 201)
        meeting_id = created.get_json()['id']
        self.assertEqual(created.get_json()['lead_id'], self.lead_id)
        listed = self.client.get(f'/api/meetings?lead_id={self.lead_id}', headers=self.headers)
        self.assertEqual([item['id'] for item in listed.get_json()], [meeting_id])

        converted = self.client.post(f'/api/leads/{self.lead_id}/convert', headers=self.headers)
        self.assertEqual(converted.status_code, 200)
        meeting = db.session.get(Meeting, meeting_id)
        self.assertEqual(meeting.client_id, converted.get_json()['client_id'])
        self.assertIsNone(meeting.lead_id)


if __name__ == '__main__':
    unittest.main()
