import unittest
from datetime import datetime
from flask_jwt_extended import create_access_token
import test_task_permissions as base
from app.extensions import db
from app.models.activity import Activity
from app.models.client import Client
from app.models.lead import Lead
from app.models.service import Service
from app.models.meeting import Meeting
from app.models.task import Task
from app.models.task_assignee import TaskAssignee


class NotificationsTest(unittest.TestCase):
    setUp = base.TaskPermissionsTest.setUp
    tearDown = base.TaskPermissionsTest.tearDown
    call = base.TaskPermissionsTest.call

    def inbox(self, uid=1):
        return self.client.get('/api/notifications', headers={'Authorization': 'Bearer '+create_access_token(identity=str(uid))})

    def test_requires_authentication(self):
        self.assertEqual(self.client.get('/api/notifications').status_code, 401)

    def test_all_assignment_types_and_isolation(self):
        now = datetime.utcnow()
        db.session.add_all([
            Client(id=1,name='Own client',assignee_id=1),
            Lead(id=1,title='Own lead',assignee_id=1),
            Lead(id=2,title='Other lead',assignee_id=2),
            Lead(id=3,title='Archived lead',assignee_id=1,deleted_at=now),
            Service(id=1,name='Own service',assignee_ids=[1,2]),
            Service(id=2,name='Other service',assignee_ids=[2]),
            Meeting(id=1,title='Own meeting',organizer_id=1,start_time=now,end_time=now),
            Activity(entity_type='lead',entity_id=1,action='updated',user_id=2),
            Activity(entity_type='lead',entity_id=2,action='updated',user_id=2),
        ]);db.session.commit()
        items=self.inbox().get_json()
        self.assertEqual({x['entity_type'] for x in items}, {'client','lead','task','service','meeting'})
        self.assertFalse(any(x['title'] in ['Other lead','Other service','Archived lead'] for x in items))
        self.assertEqual(len([x for x in items if x['id'].startswith('activity:')]),1)
        self.assertEqual(len([x for x in items if x['id']=='assigned:task:1']),1)
        db.session.get(Task,1).assignee_id=1;db.session.commit()
        self.assertEqual(len([x for x in self.inbox().get_json() if x['id']=='assigned:task:1']),1)
        db.session.query(TaskAssignee).filter_by(task_id=1,user_id=1).delete()
        db.session.get(Task,1).assignee_id=None;db.session.commit()
        self.assertFalse(any(x['entity_type']=='task' for x in self.inbox().get_json()))

    def test_updates_appear_in_inbox(self):
        response=self.call(3,'/api/tasks/1',{'title':'Updated task'})
        self.assertEqual(response.status_code,200)
        items=self.inbox().get_json()
        self.assertTrue(any(x['action']=='updated' and x['title']=='Updated task' for x in items))

    def test_layout_composes_and_preserves_template_examples(self):
        for path in ['/', '/index.html']:
            response=self.client.get(path)
            self.assertEqual(response.status_code,200)
            html=response.get_data(as_text=True)
            self.assertIn('<title>ZenCRM</title>',html)
            self.assertIn('{{ client.name }}',html)
            self.assertNotIn('<% include',html)
            self.assertIn('/js/modules/notifications.js',html)
            portal_panel = html.index('class="portal-admin-view"')
            self.assertGreater(html.index('</main>', portal_panel), portal_panel)
            self.assertNotIn('<div class="px-3 py-2 flex gap-4"><a href="/workspace.html#values">', html)
