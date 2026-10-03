import unittest
from datetime import datetime, timedelta, timezone
from flask_jwt_extended import create_access_token
import test_task_permissions as base
from app.extensions import db
from app.models.reminder import Reminder
from app.models.task import Task

class RemindersTest(unittest.TestCase):
    setUp = base.TaskPermissionsTest.setUp
    tearDown = base.TaskPermissionsTest.tearDown
    call = base.TaskPermissionsTest.call

    def future(self):
        return (datetime.now(timezone.utc)+timedelta(days=2)).isoformat()

    def listing(self, uid=1):
        return self.client.get('/api/reminders', headers={'Authorization':'Bearer '+create_access_token(identity=str(uid))})

    def test_auth_and_ownership(self):
        self.assertEqual(self.client.get('/api/reminders').status_code,401)
        result=self.call(1,'/api/reminders',dict(title='Call',remind_at=self.future(),user_id=2),'post')
        self.assertEqual(result.status_code,201)
        rid=result.json['id']
        self.assertEqual(len(self.listing().json),1)
        self.assertEqual(self.listing(2).json,[])
        self.assertEqual(self.call(2,f'/api/reminders/{rid}',{'action':'dismiss'}).status_code,404)

    def test_snooze_dismiss_and_validation(self):
        for at in ['bad','2000-01-01T00:00:00Z','2099-01-01T00:00:00']:
            self.assertEqual(self.call(1,'/api/reminders',dict(title='Call',remind_at=at),'post').status_code,400)
        rid=self.call(1,'/api/reminders',dict(title='Call',remind_at=self.future()),'post').json['id']
        self.assertEqual(self.call(1,f'/api/reminders/{rid}',dict(action='snooze',minutes=-1)).status_code,400)
        result=self.call(1,f'/api/reminders/{rid}',dict(action='snooze',minutes=10))
        self.assertEqual(result.status_code,200)
        at=datetime.fromisoformat(result.json['remind_at'].replace('Z','+00:00'))
        self.assertTrue(590 < (at-datetime.now(timezone.utc)).total_seconds() <= 600)
        self.assertEqual(self.call(1,f'/api/reminders/{rid}',dict(action='dismiss')).status_code,200)
        self.assertEqual(self.listing().json,[])

    def test_task_transaction_and_upsert(self):
        payload=dict(title='Task reminder',reminder_at=self.future())
        result=self.call(1,'/api/tasks',payload,'post')
        self.assertEqual(result.status_code,201)
        tid=result.json['id']
        self.assertEqual(Reminder.query.filter_by(task_id=tid,user_id=1).count(),1)
        self.call(1,f'/api/tasks/{tid}',payload)
        self.assertEqual(Reminder.query.filter_by(task_id=tid,user_id=1).count(),1)
        self.assertEqual(self.call(1,f'/api/tasks/{tid}',dict(title='Must rollback',reminder_at='bad')).status_code,400)
        self.assertEqual(db.session.get(Task,tid).title,'Task reminder')
        self.call(1,f'/api/tasks/{tid}',dict(status='done'))
        self.assertEqual(self.listing().json,[])
        self.call(1,f'/api/tasks/{tid}',dict(reminder_at=None))
        self.assertEqual(Reminder.query.filter_by(task_id=tid).count(),0)

    def test_timezone_and_overdue(self):
        result=self.call(1,'/api/reminders',dict(title='TZ',remind_at='2099-01-01T12:00:00+02:00'),'post')
        self.assertEqual(result.json['remind_at'],'2099-01-01T10:00:00Z')
        row=db.session.get(Reminder,result.json['id']);row.remind_at=datetime.utcnow()-timedelta(days=1);db.session.commit()
        self.assertEqual(len(self.listing().json),1)

    def test_link_and_archive_endpoints(self):
        created = self.call(1, '/api/reminders', dict(title='With Link', remind_at=self.future(), link='https://example.com/test'), 'post')
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json.get('link'), 'https://example.com/test')
        rid = created.json['id']

        # Listing should contain link
        items = self.listing().json
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].get('link'), 'https://example.com/test')

        # Dismiss / archive
        self.assertEqual(self.call(1, f'/api/reminders/{rid}', dict(action='dismiss')).status_code, 200)
        self.assertEqual(len(self.listing().json), 0)

        # Include archived
        res_all = self.client.get('/api/reminders?include_archived=true', headers={'Authorization':'Bearer '+create_access_token(identity='1')})
        self.assertEqual(res_all.status_code, 200)
        self.assertEqual(len(res_all.json), 1)
        self.assertTrue(res_all.json[0]['dismissed'])
        self.assertEqual(res_all.json[0]['link'], 'https://example.com/test')

        # Restore
        res_restore = self.call(1, f'/api/reminders/{rid}', dict(action='restore'))
        self.assertEqual(res_restore.status_code, 200)
        self.assertFalse(res_restore.json['dismissed'])
        self.assertEqual(len(self.listing().json), 1)

        # Delete
        del_res = self.client.delete(f'/api/reminders/{rid}', headers={'Authorization':'Bearer '+create_access_token(identity='1')})
        self.assertEqual(del_res.status_code, 200)
        self.assertEqual(len(self.listing().json), 0)
