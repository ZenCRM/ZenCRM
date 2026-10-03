import copy
from datetime import datetime, timedelta
import io
import tempfile
from unittest.mock import patch
import unittest
import test_task_permissions as task_tests
from app.utils.lead_stages import DEFAULT_STAGES
from app.models.lead import Lead
from app.models.task import Task
from app.extensions import db

class BoardAndAvatarTest(unittest.TestCase):
    setUp = task_tests.TaskPermissionsTest.setUp
    tearDown = task_tests.TaskPermissionsTest.tearDown
    call = task_tests.TaskPermissionsTest.call
    def test_custom_stages_persist_and_stats(self):
        stages = copy.deepcopy(DEFAULT_STAGES)
        stages.append({'id':'review','label':'Weryfikacja','accent':'#007fce'})
        response = self.call(3,'/api/leads/board-settings',{'stages':stages})
        self.assertEqual(response.status_code,200)
        db.session.add(Lead(title='Test lead',stage='review',value=100));db.session.commit()
        result=self.client.get('/api/leads/board-settings',headers=self.headers()).get_json()
        self.assertEqual(result['stages'][-1]['label'],'Weryfikacja')
        stats=self.client.get('/api/stats',headers=self.headers()).get_json()
        self.assertEqual(stats['funnel']['review'],1)
        self.assertEqual(stats['cards']['pipeline'],100)
    def headers(self):
        from flask_jwt_extended import create_access_token
        return {'Authorization':'Bearer '+create_access_token(identity='3')}
    def test_dashboard_task_status_counts_exclude_deleted(self):
        before = self.client.get('/api/stats', headers=self.headers()).get_json()['task_status']
        db.session.add_all([
            Task(title='Plan', status='todo'),
            Task(title='Praca', status='in_progress'),
            Task(title='Gotowe', status='done'),
            Task(title='Usunięte', status='done', deleted_at=datetime.utcnow()),
        ])
        db.session.commit()
        stats = self.client.get('/api/stats', headers=self.headers()).get_json()
        self.assertEqual(stats['task_status'], {status: before.get(status, 0) + 1 for status in ('todo', 'in_progress', 'done')})
    def test_dashboard_tasks_partitioning(self):
        now = datetime.utcnow()
        db.session.add_all([
            Task(title='Zadanie zaległe', status='todo', due_date=now - timedelta(days=2)),
            Task(title='Zadanie na dziś', status='todo', due_date=now + timedelta(minutes=30)),
            Task(title='Zadanie na jutro', status='todo', due_date=now + timedelta(days=2)),
            Task(title='Zadanie zrobione', status='done', due_date=now - timedelta(days=2)),
        ])
        db.session.commit()
        stats = self.client.get('/api/stats', headers=self.headers()).get_json()
        self.assertIn('overdue_tasks', stats)
        self.assertIn('today_tasks', stats)
        self.assertIn('upcoming_tasks', stats)
        overdue_titles = [t['title'] for t in stats['overdue_tasks']]
        today_titles = [t['title'] for t in stats['today_tasks']]
        upcoming_titles = [t['title'] for t in stats['upcoming_tasks']]
        self.assertIn('Zadanie zaległe', overdue_titles)
        self.assertNotIn('Zadanie zrobione', overdue_titles)
        self.assertIn('Zadanie na dziś', today_titles)
        self.assertIn('Zadanie na jutro', upcoming_titles)
    def test_task_status_settings_save_and_permissions(self):
        stages = [
            {'id': 'todo', 'label': 'Plan', 'accent': '#865528'},
            {'id': 'in_progress', 'label': 'Realizacja', 'accent': '#008c9f'},
            {'id': 'done', 'label': 'Gotowe', 'accent': '#16886e'},
        ]
        self.assertEqual(self.call(1, '/api/tasks/board-settings', {'stages': stages}).status_code, 403)
        self.assertEqual(self.call(3, '/api/tasks/board-settings', {'stages': stages}).status_code, 200)
        saved = self.client.get('/api/tasks/board-settings', headers=self.headers()).get_json()['stages']
        self.assertEqual(saved, stages)
        self.assertEqual(self.call(3, '/api/tasks/board-settings', {'stages': stages[:2]}).status_code, 400)
    def test_task_status_can_be_added_reordered_and_removed_when_unused(self):
        stages = self.client.get('/api/tasks/board-settings', headers=self.headers()).get_json()['stages']
        custom = {'id': 'stage_review', 'label': 'Do kontroli', 'accent': '#7255aa'}
        another = {'id': 'stage_ready', 'label': 'Gotowe do kontroli', 'accent': '#4579aa'}
        configured = [stages[0], another, custom, stages[1], stages[2]]
        self.assertEqual(self.call(3, '/api/tasks/board-settings', {'stages': configured}).status_code, 200)
        created = self.call(3, '/api/tasks', {'title': 'Kontrola', 'status': custom['id']}, 'post')
        self.assertEqual(created.status_code, 201)
        task_id = created.get_json()['id']
        self.assertEqual(self.client.get('/api/stats', headers=self.headers()).get_json()['task_status'][custom['id']], 1)
        without_custom = [stage for stage in configured if stage['id'] != custom['id']]
        self.assertEqual(self.call(3, '/api/tasks/board-settings', {'stages': without_custom}).status_code, 400)
        self.assertEqual(self.call(3, f'/api/tasks/{task_id}', {'status': 'todo'}).status_code, 200)
        self.assertEqual(self.call(3, '/api/tasks/board-settings', {'stages': without_custom}).status_code, 200)
        self.assertEqual(self.call(3, '/api/tasks', {'title': 'Błędny status', 'status': custom['id']}, 'post').status_code, 400)
        self.assertEqual(self.client.get('/api/tasks/board-settings', headers=self.headers()).get_json()['stages'], without_custom)
    def test_task_status_anchors_cannot_be_deleted(self):
        stages = self.client.get('/api/tasks/board-settings', headers=self.headers()).get_json()['stages']
        self.assertEqual(self.call(3, '/api/tasks/board-settings', {'stages': stages[1:]}).status_code, 400)
        self.assertEqual(self.call(3, '/api/tasks/board-settings', {'stages': stages[:-1]}).status_code, 400)
    def test_assignee_progress_uses_remaining_configured_status(self):
        stages = self.client.get('/api/tasks/board-settings', headers=self.headers()).get_json()['stages']
        custom = {'id': 'stage_review', 'label': 'Kontrola', 'accent': '#7255aa'}
        self.assertEqual(self.call(3, '/api/tasks/board-settings', {'stages': [stages[0], custom, stages[-1]]}).status_code, 200)
        self.assertEqual(self.call(1, '/api/task-assignees/1', {'status': 'in_progress'}).status_code, 200)
        self.assertEqual(db.session.get(Task, 1).status, custom['id'])
    def test_invalid_stage_config(self):
        stages=copy.deepcopy(DEFAULT_STAGES);stages[0]['accent']='red'
        self.assertEqual(self.call(3,'/api/leads/board-settings',{'stages':stages}).status_code,400)
        self.assertEqual(self.call(1,'/api/leads/board-settings',{'stages':DEFAULT_STAGES}).status_code,403)
    def test_used_stage_cannot_be_removed(self):
        db.session.add(Lead(title='Used',stage='contacted'));db.session.commit()
        stages=[s for s in DEFAULT_STAGES if s['id']!='contacted']
        self.assertEqual(self.call(3,'/api/leads/board-settings',{'stages':stages}).status_code,400)
    def test_avatar_upload_and_profile_save(self):
        from PIL import Image
        data=io.BytesIO();Image.new('RGB',(2,2),'blue').save(data,format='PNG');data.seek(0)
        with tempfile.TemporaryDirectory() as folder, patch('app.api.users.AVATAR_DIR',folder):
            result=self.client.post('/api/users/3/avatar',data={'file':(data,'avatar.png')},headers=self.headers())
            self.assertEqual(result.status_code,200)
            avatar=result.get_json()['avatar_url']
            self.assertTrue(avatar.startswith('/api/avatars/'))
            self.assertEqual(self.call(3,'/api/users/3',{'avatar_url':avatar,'first_name':'Test','last_name':'Admin','email':'3@test.local'}).status_code,200)
