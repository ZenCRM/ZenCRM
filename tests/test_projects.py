import unittest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.client import Client
from app.models.project import Project, ProjectMember
from app.models.task import Task
from app.models.user import User


class ProjectsTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        admin = User(email='admin@proj.local', password_hash='unused', first_name='Adam', last_name='Admin', role='admin')
        user2 = User(email='dev@proj.local', password_hash='unused', first_name='Piotr', last_name='Dev', role='employee')
        client = Client(name='Firma ABC')
        db.session.add_all([admin, user2, client])
        db.session.commit()

        self.admin = admin
        self.user2 = user2
        self.client_record = client
        self.client = self.app.test_client()
        self.headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_project_crud_and_stages(self):
        # 1. Create project
        res = self.client.post('/api/projects', json={
            'name': 'Wdrożenie CRM 2026',
            'client_id': self.client_record.id,
            'manager_id': self.admin.id,
            'status': 'in_progress',
            'budget': 50000,
            'member_ids': [self.user2.id]
        }, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        proj_data = res.get_json()
        proj_id = proj_data['id']
        self.assertEqual(proj_data['name'], 'Wdrożenie CRM 2026')
        self.assertEqual(len(proj_data['members']), 1)

        # 2. Get project detail
        res = self.client.get(f'/api/projects/{proj_id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        detail = res.get_json()
        self.assertEqual(detail['manager']['id'], self.admin.id)
        self.assertEqual(detail['client']['name'], 'Firma ABC')

        # 3. Update stages (Kanban statusy)
        new_stages = [
            {'id': 'todo', 'label': 'Do zrobienia', 'accent': '#64748b'},
            {'id': 'review', 'label': 'Weryfikacja', 'accent': '#3b82f6'},
            {'id': 'done', 'label': 'Zrobione', 'accent': '#10b981'}
        ]
        res = self.client.put(f'/api/projects/{proj_id}/stages', json={'stages': new_stages}, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()['task_stages']), 3)

        # 4. Create task in project
        res = self.client.post('/api/tasks', json={
            'title': 'Przygotowanie makiety',
            'project_id': proj_id,
            'status': 'review',
            'priority': 'high'
        }, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        task_id = res.get_json()['id']

        # 5. List tasks with project_id filter
        res = self.client.get(f'/api/tasks?project_id={proj_id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        tasks = res.get_json()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0]['project_id'], proj_id)
        self.assertEqual(tasks[0]['status'], 'review')

        # 6. Add and remove member
        res = self.client.delete(f'/api/projects/{proj_id}/members/{self.user2.id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()['members']), 0)

        res = self.client.post(f'/api/projects/{proj_id}/members', json={
            'user_id': self.user2.id,
            'role': 'Senior Developer'
        }, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        members = res.get_json()['members']
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0]['role'], 'Senior Developer')

    def test_custom_fields_required_and_batch_values(self):
        # 1. Create required custom field for projects
        res = self.client.post('/api/custom-fields', json={
            'entity': 'projects',
            'label': 'Kod SAP',
            'kind': 'text',
            'required': True
        }, headers=self.headers)
        self.assertEqual(res.status_code, 201)
        cf_data = res.get_json()
        cf_id = cf_data['id']
        self.assertTrue(cf_data['required'])

        # 2. Edit custom field definition
        res = self.client.put(f'/api/custom-fields/{cf_id}', json={
            'label': 'Identyfikator SAP',
            'required': False
        }, headers=self.headers)
        self.assertEqual(res.status_code, 200)
        updated_cf = res.get_json()
        self.assertEqual(updated_cf['label'], 'Identyfikator SAP')
        self.assertFalse(updated_cf['required'])

        # 3. Create project and assign custom value
        proj = Project(name='Projekt Testowy')
        db.session.add(proj)
        db.session.commit()

        self.client.put(f'/api/custom-fields/projects/{proj.id}', json={
            str(cf_id): 'SAP-9988'
        }, headers=self.headers)

        # 4. Batch values endpoint for table view
        res = self.client.get(f'/api/custom-fields/projects/values?ids={proj.id}', headers=self.headers)
        self.assertEqual(res.status_code, 200)
        values = res.get_json()
        self.assertEqual(values[str(proj.id)][str(cf_id)], 'SAP-9988')
