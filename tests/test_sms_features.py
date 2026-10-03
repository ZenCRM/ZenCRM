import unittest
from datetime import datetime
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.sms import SmsDevice, PhoneCall, SmsMessage
from app.models.client import Client
from app.models.contact import Contact
from app.models.activity import Activity
from app.api.sms import phones_match, find_entities_by_phone, create_telephony_activity


class TestSmsFeatures(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_phone_normalization_and_match(self):
        self.assertTrue(phones_match('+48500600700', '500600700'))
        self.assertTrue(phones_match('48 500 600 700', '+48 500-600-700'))
        self.assertTrue(phones_match('0048500600700', '500600700'))
        self.assertFalse(phones_match('500600700', '500600701'))

    def test_device_sync_from_and_activities(self):
        cl = Client(name='Firma Testowa', phone='+48 500 600 700')
        db.session.add(cl)
        db.session.commit()

        ct = Contact(client_id=cl.id, first_name='Jan', last_name='Kowalski', phone='500 600 700')
        db.session.add(ct)
        db.session.commit()

        # Find entities by phone matches client and contact
        ents = find_entities_by_phone('500600700')
        self.assertEqual(len(ents['clients']), 1)
        self.assertEqual(len(ents['contacts']), 1)
        self.assertEqual(ents['contacts'][0]['name'], 'Jan Kowalski')

        # Test activity creation with custom timestamp
        custom_time = datetime(2026, 1, 15, 10, 30, 0)
        act = create_telephony_activity(
            item_type='call',
            entity_type='client',
            entity_id=cl.id,
            phone='500600700',
            direction='incoming',
            title_or_contact='Jan Kowalski',
            duration_sec=45,
            item_time=custom_time
        )
        db.session.commit()

        saved_act = Activity.query.filter_by(entity_type='client', entity_id=cl.id).first()
        self.assertIsNotNone(saved_act)
        self.assertEqual(saved_act.created_at, custom_time)
        self.assertIn('Jan Kowalski', saved_act.description)


if __name__ == '__main__':
    unittest.main()
