import unittest
from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User
from app.models.task import Task
from app.models.task_assignee import TaskAssignee
from flask_jwt_extended import create_access_token

class TaskPermissionsTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context(); self.ctx.push()
        db.create_all()
        db.session.add_all([User(id=i, email=f'{i}@test.local', password_hash='unused-test-hash', first_name='Test', last_name=str(i), role='admin' if i == 3 else 'employee') for i in (1,2,3)])
        db.session.add(Task(id=1,title='Test',status='todo'))
        db.session.flush()
        db.session.add_all([TaskAssignee(id=i,task_id=1,user_id=i,status='pending') for i in (1,2)])
        db.session.commit()
        self.client = self.app.test_client()
    def tearDown(self):
        db.session.remove(); db.drop_all(); self.ctx.pop()
    def call(self, uid, path, data, method='put'):
        return getattr(self.client,method)(path,json=data,headers={'Authorization':'Bearer '+create_access_token(identity=str(uid))})
    def test_own_status(self):
        self.assertEqual(self.call(1,'/api/task-assignees/1',{'status':'done'}).status_code,200)
        self.assertEqual(db.session.get(Task,1).status,'in_progress')
    def test_other_status_and_comment(self):
        self.assertEqual(self.call(1,'/api/task-assignees/2',{'status':'done','comment':'changed'}).status_code,403)
        self.assertEqual(db.session.get(TaskAssignee,2).status,'pending')
    def test_admin(self):
        self.assertEqual(self.call(3,'/api/task-assignees/2',{'status':'done'}).status_code,200)
    def test_invalid_status(self):
        self.assertEqual(self.call(1,'/api/task-assignees/1',{'status':'invalid'}).status_code,400)
    def test_whole_task_bypass(self):
        self.assertEqual(self.call(1,'/api/tasks/1',{'status':'done'}).status_code,403)
    def test_remove_other_bypass(self):
        self.assertEqual(self.call(1,'/api/task-assignees/task/1/set',{'user_ids':[1]},'post').status_code,403)
        self.assertEqual(self.call(1,'/api/task-assignees/2',{},'delete').status_code,403)

if __name__ == '__main__': unittest.main()
