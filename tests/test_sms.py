import unittest
import json
from unittest.mock import patch
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User
from app.models.client import Client
from app.models.sms import SmsDevice, SmsQueue, PhoneCall, SmsMessage
from flask_jwt_extended import create_access_token


class SmsApiTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Seed admin and client
        self.admin = User(id=1, email='admin@test.local', password_hash='hash', first_name='Admin', last_name='Zen', role='admin')
        self.client_rec = Client(id=1, name='Firma Testowa', phone='+48 500 600 700')
        db.session.add_all([self.admin, self.client_rec])

        # Seed device
        self.device = SmsDevice(
            id=1,
            name='Telefon Firmowy',
            phone_number='+48 500 111 222',
            token='TEST_SECRET_TOKEN',
            user_id=1,
            is_active=True
        )
        db.session.add(self.device)
        db.session.commit()

        self.client = self.app.test_client()
        self.jwt_header = {'Authorization': 'Bearer ' + create_access_token(identity='1')}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_next_task_skips_task_claimed_by_another_poller(self):
        other = SmsDevice(id=2, name='Second phone', phone_number='+48 500 333 444',
                          token='OTHER_SECRET_TOKEN', user_id=1, is_active=True)
        taken = SmsQueue(phone_number='+48 600 000 001', message='first', action='send_sms', status='pending')
        free = SmsQueue(phone_number='+48 600 000 002', message='second', action='send_sms', status='pending')
        db.session.add_all([other, taken, free])
        db.session.commit()
        taken_id, free_id = taken.id, free.id
        stale_candidates = [taken_id, free_id]
        # Another poller claims the oldest task after this request has read the candidates.
        SmsQueue.query.filter_by(id=taken_id).update({'status': 'processing', 'device_id': other.id})
        db.session.commit()

        with patch('app.api.sms.pending_task_ids', return_value=stale_candidates):
            res = self.client.get('/api/sms/next', headers={'X-Device-Token': 'TEST_SECRET_TOKEN'})

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json['id'], free_id)
        self.assertEqual(db.session.get(SmsQueue, taken_id).device_id, other.id)
        claimed = db.session.get(SmsQueue, free_id)
        self.assertEqual((claimed.status, claimed.device_id), ('processing', self.device.id))

    def test_call_note_is_saved_and_returned_with_history(self):
        call = PhoneCall(device_id=self.device.id, number=self.client_rec.phone,
                         type='incoming', timestamp=1760000000000)
        db.session.add(call)
        db.session.commit()

        response = self.client.put(f'/api/sms/calls/{call.id}/note',
                                   json={'note': '  Ustalenia z rozmowy  '}, headers=self.jwt_header)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json['note'], 'Ustalenia z rozmowy')
        history = self.client.get('/api/sms/calls', headers=self.jwt_header)
        self.assertEqual(history.json['calls'][0]['note'], 'Ustalenia z rozmowy')
        self.assertEqual(self.client.put(f'/api/sms/calls/{call.id}/note',
                         json={'note': 123}, headers=self.jwt_header).status_code, 400)
        self.assertEqual(self.client.put('/api/sms/calls/999/note',
                         json={'note': 'x'}, headers=self.jwt_header).status_code, 404)

    def test_device_crud(self):
        # List devices
        res = self.client.get('/api/sms/devices', headers=self.jwt_header)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.json), 1)

        # Create device
        res = self.client.post('/api/sms/devices', json={
            'name': 'Nowy Telefon',
            'phone_number': '+48 600 700 800'
        }, headers=self.jwt_header)
        self.assertEqual(res.status_code, 201)
        new_id = res.json['id']
        self.assertTrue(res.json['token'].startswith('zen_sms_'))

        # Update device
        res = self.client.put(f'/api/sms/devices/{new_id}', json={
            'name': 'Zmieniona Nazwa'
        }, headers=self.jwt_header)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json['name'], 'Zmieniona Nazwa')

        # Delete device
        res = self.client.delete(f'/api/sms/devices/{new_id}', headers=self.jwt_header)
        self.assertEqual(res.status_code, 200)

    def test_next_task_polling_and_sms_send(self):
        # 1. Invalid token
        res = self.client.get('/api/sms/next.php?token=WRONG_TOKEN')
        self.assertEqual(res.status_code, 403)

        # 2. Empty queue
        res = self.client.get('/api/sms/next.php?token=TEST_SECRET_TOKEN')
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.json)

        # 3. Queue an SMS send via CRM
        res = self.client.post('/api/sms/send', json={
            'device_id': 1,
            'phone_number': '+48500600700',
            'message': 'Cześć! Twoje zamówienie jest gotowe.'
        }, headers=self.jwt_header)
        self.assertEqual(res.status_code, 201)
        task_id = res.json['id']
        self.assertEqual(res.json['client_id'], 1)  # Auto-matched to client

        # 4. Phone polls next task
        res = self.client.get('/api/sms/next.php?token=TEST_SECRET_TOKEN')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json['id'], task_id)
        self.assertEqual(res.json['to'], '+48500600700')
        self.assertEqual(res.json['text'], 'Cześć! Twoje zamówienie jest gotowe.')

        # 5. Phone reports sent status
        res = self.client.post('/api/sms/report.php', json={
            'token': 'TEST_SECRET_TOKEN',
            'id': task_id,
            'status': 'sent'
        })
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.json['success'])

        # Verify task is marked sent
        task = db.session.get(SmsQueue, task_id)
        self.assertEqual(task.status, 'sent')

        # Verify message is logged in SmsMessage history
        msgs = self.client.get('/api/sms/messages', headers=self.jwt_header).json
        self.assertEqual(len(msgs['messages']), 1)
        self.assertEqual(msgs['messages'][0]['type'], 'sent')
        self.assertEqual(msgs['messages'][0]['address'], '+48500600700')

    def test_device_actions_and_reporting(self):
        # 1. Trigger get_stats action
        res = self.client.post('/api/sms/actions/trigger', json={
            'device_id': 1,
            'action': 'get_stats'
        }, headers=self.jwt_header)
        self.assertEqual(res.status_code, 201)
        task_id = res.json['id']

        # 2. Phone polls next
        res = self.client.get('/api/sms/next?token=TEST_SECRET_TOKEN')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json['action'], 'get_stats')
        self.assertEqual(res.json['id'], task_id)

        # 3. Phone posts stats
        res = self.client.post('/api/sms/stats.php', json={
            'token': 'TEST_SECRET_TOKEN',
            'request_id': task_id,
            'today': {
                'calls_total': 10,
                'calls_incoming': 6,
                'calls_outgoing': 4,
                'calls_missed': 1,
                'duration_total_sec': 500,
                'sms_sent': 5,
                'sms_received': 8
            },
            'week': {
                'calls_total': 50,
                'duration_total_sec': 3000,
                'sms_total': 60
            }
        })
        self.assertEqual(res.status_code, 200)

        # Verify device stats saved
        dev = db.session.get(SmsDevice, 1)
        self.assertIsNotNone(dev.today_stats)
        self.assertTrue(dev.is_online)

        # 4. Phone posts call history
        res = self.client.post('/api/sms/history.php', json={
            'token': 'TEST_SECRET_TOKEN',
            'history': [
                {
                    'number': '+48 500 600 700',
                    'name': 'Firma Testowa',
                    'type': 'incoming',
                    'timestamp': 1759010000000,
                    'date_formatted': '2026-09-27 22:10:00',
                    'duration_sec': 120,
                    'duration_formatted': '2m 00s'
                },
                {
                    'number': '+48 999 888 777',
                    'name': 'Nieznany',
                    'type': 'missed',
                    'timestamp': 1759005000000,
                    'date_formatted': '2026-09-27 20:00:00',
                    'duration_sec': 0,
                    'duration_formatted': '0s'
                }
            ]
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json['inserted'], 2)

        # Verify calls API
        calls_res = self.client.get('/api/sms/calls', headers=self.jwt_header)
        self.assertEqual(calls_res.status_code, 200)
        self.assertEqual(len(calls_res.json['calls']), 2)
        # Verify client link on matching phone
        self.assertIsNotNone(calls_res.json['calls'][0]['client'] or calls_res.json['calls'][1]['client'])

        # 5. Phone posts SMS history
        res = self.client.post('/api/sms/sms_history.php', json={
            'token': 'TEST_SECRET_TOKEN',
            'sms_history': [
                {
                    'address': '+48 500 600 700',
                    'body': 'Dzień dobry, czy oferta aktualna?',
                    'timestamp': 1759008000000,
                    'date_formatted': '2026-09-27 21:30:00',
                    'type': 'received'
                }
            ]
        })
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json['inserted'], 1)

        # Verify threads
        threads = self.client.get('/api/sms/threads', headers=self.jwt_header).json
        self.assertEqual(len(threads), 1)

        # Verify stats summary (calculated directly from calls and sms in database)
        summary = self.client.get('/api/sms/stats-summary', headers=self.jwt_header).json
        self.assertEqual(summary['total_devices'], 1)
        self.assertEqual(summary['online_devices'], 1)
        self.assertEqual(summary['all_time']['calls_total'], 2)
        self.assertEqual(summary['all_time']['sms_total'], 1)

        # 6. Test sync endpoint
        sync_res = self.client.post('/api/sms/sync', headers=self.jwt_header)
        self.assertEqual(sync_res.status_code, 200)
        self.assertTrue(sync_res.json['success'])
        self.assertEqual(sync_res.json['queued_tasks'], 2)

        # 7. Test entity-history endpoint for client
        entity_res = self.client.get(f'/api/sms/entity-history?type=client&id={self.client_rec.id}', headers=self.jwt_header)
        self.assertEqual(entity_res.status_code, 200)
        self.assertEqual(len(entity_res.json['calls']), 1)
        self.assertEqual(len(entity_res.json['messages']), 1)

    def test_device_user_assignment_and_isolation(self):
        # 1. Create a second user (employee)
        employee = User(id=2, email='emp@test.local', password_hash='hash', first_name='Jan', last_name='Kowalski', role='employee')
        db.session.add(employee)
        db.session.commit()
        emp_jwt_header = {'Authorization': 'Bearer ' + create_access_token(identity='2')}

        # 2. Employee adds their own phone (automatically bound to employee.id)
        emp_dev_res = self.client.post('/api/sms/devices', json={
            'name': 'Telefon Pracownika',
            'phone_number': '+48 500 222 333'
        }, headers=emp_jwt_header)
        self.assertEqual(emp_dev_res.status_code, 201)
        emp_dev_id = emp_dev_res.json['id']
        emp_dev = db.session.get(SmsDevice, emp_dev_id)
        self.assertEqual(emp_dev.user_id, employee.id)

        # 3. Create another phone assigned to admin
        admin_dev_res = self.client.post('/api/sms/devices', json={
            'name': 'Telefon Admina 2',
            'phone_number': '+48 500 999 888'
        }, headers=self.jwt_header)
        self.assertEqual(admin_dev_res.status_code, 201)
        admin_dev_id = admin_dev_res.json['id']
        admin_dev = db.session.get(SmsDevice, admin_dev_id)
        self.assertEqual(admin_dev.user_id, self.admin.id)

        # 4. Admin sees ONLY admin's devices in GET /devices (self.device and admin_dev_id)
        admin_list = self.client.get('/api/sms/devices', headers=self.jwt_header).json
        self.assertEqual(len(admin_list), 2)
        admin_dev_ids = [d['id'] for d in admin_list]
        self.assertIn(self.device.id, admin_dev_ids)
        self.assertIn(admin_dev_id, admin_dev_ids)
        self.assertNotIn(emp_dev_id, admin_dev_ids)

        # 5. Employee sees ONLY their own device in GET /devices
        emp_list = self.client.get('/api/sms/devices', headers=emp_jwt_header).json
        self.assertEqual(len(emp_list), 1)
        self.assertEqual(emp_list[0]['id'], emp_dev_id)
        self.assertEqual(emp_list[0]['user_id'], employee.id)
        self.assertIn('token', emp_list[0])

        # 6. Employee cannot edit Admin's device, Admin cannot edit Employee's device
        forbidden_edit_1 = self.client.put(f'/api/sms/devices/{admin_dev_id}', json={'name': 'Hacked'}, headers=emp_jwt_header)
        self.assertEqual(forbidden_edit_1.status_code, 403)
        forbidden_edit_2 = self.client.put(f'/api/sms/devices/{emp_dev_id}', json={'name': 'Hacked by admin'}, headers=self.jwt_header)
        self.assertEqual(forbidden_edit_2.status_code, 403)

        # 7. Add calls: one on employee phone, one on admin phone
        call_emp = PhoneCall(device_id=emp_dev_id, number='+48 500 600 700', type='incoming', timestamp=1760000001000)
        call_admin = PhoneCall(device_id=admin_dev_id, number='+48 500 600 700', type='outgoing', timestamp=1760000002000)
        db.session.add_all([call_emp, call_admin])
        db.session.commit()

        # In Telefonia & SMS calls tab:
        # Employee sees only their phone's call
        emp_calls = self.client.get('/api/sms/calls', headers=emp_jwt_header).json
        self.assertEqual(len(emp_calls['calls']), 1)
        self.assertEqual(emp_calls['calls'][0]['device_id'], emp_dev_id)

        # Admin sees only their own phone's call in Telefonia & SMS
        admin_calls = self.client.get('/api/sms/calls', headers=self.jwt_header).json
        self.assertEqual(len(admin_calls['calls']), 1)
        self.assertEqual(admin_calls['calls'][0]['device_id'], admin_dev_id)

        # 8. Entity history respects device ownership too.
        emp_entity_res = self.client.get(f'/api/sms/entity-history?type=client&id={self.client_rec.id}', headers=emp_jwt_header)
        self.assertEqual(emp_entity_res.status_code, 200)
        self.assertEqual(len(emp_entity_res.json['calls']), 1)

        admin_entity_res = self.client.get(f'/api/sms/entity-history?type=client&id={self.client_rec.id}', headers=self.jwt_header)
        self.assertEqual(admin_entity_res.status_code, 200)
        self.assertEqual(len(admin_entity_res.json['calls']), 1)


if __name__ == '__main__':
    unittest.main()
