"""Permanent deletes under enforced foreign keys: by-products go, linked business records block."""
import unittest
from datetime import datetime

from flask_jwt_extended import create_access_token

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.client import Client
from app.models.contact import Contact
from app.models.document import Document
from app.models.lead import Lead
from app.models.offer import Offer
from app.models.push import PushSubscription
from app.models.reminder import Reminder
from app.models.service import Service
from app.models.sms import PhoneCall, SmsDevice, SmsMessage
from app.models.task import Task
from app.models.task_assignee import TaskAssignee
from app.models.template import Template
from app.models.user import User
from app.models.workspace import PortalClientSpace, PortalSpace
from app.models.project import Project
from app.models.team import Team
from app.models.ticket import Ticket


class HardDeleteTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'hard-delete-test-key-with-at-least-32-bytes'
            PUSH_ENABLED = False
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.client = self.app.test_client()
        self.admin = User(email='admin@example.com', first_name='Ada', last_name='Admin', role='admin', is_active=True)
        self.admin.set_password('admin-password-1')
        db.session.add(self.admin)
        db.session.commit()
        self.headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(self.admin.id))}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def add(self, *records):
        db.session.add_all(records)
        db.session.commit()
        return records[0] if len(records) == 1 else records

    def delete(self, url):
        response = self.client.delete(url, headers=self.headers)
        db.session.expire_all()
        return response

    def test_client_with_business_records_is_refused(self):
        client = self.add(Client(name='Acme'))
        self.add(Lead(title='Upsell', client_id=client.id))
        response = self.delete(f'/api/archive/clients/{client.id}/permanent')
        self.assertEqual(response.status_code, 409)
        self.assertTrue(response.get_json()['error'])
        self.assertIsNotNone(db.session.get(Client, client.id))

    def test_client_by_products_are_released(self):
        client = self.add(Client(name='Acme'))
        space = self.add(PortalSpace(name='Acme space'))
        device = self.add(SmsDevice(name='Phone', token='DELETE_TEST_TOKEN', user_id=self.admin.id))
        call, message = self.add(PhoneCall(device_id=device.id, number='+48500', type='incoming', client_id=client.id),
                                 SmsMessage(device_id=device.id, address='+48500', body='Hi', type='received', client_id=client.id))
        self.add(PortalClientSpace(client_id=client.id, space_id=space.id))
        self.assertEqual(self.delete(f'/api/clients/{client.id}/permanent').status_code, 200)
        self.assertIsNone(db.session.get(Client, client.id))
        self.assertEqual(PortalClientSpace.query.count(), 0)
        self.assertIsNone(db.session.get(PhoneCall, call.id).client_id)
        self.assertIsNone(db.session.get(SmsMessage, message.id).client_id)

    def test_task_reminders_and_assignees_go_with_the_task(self):
        task = self.add(Task(title='Call back'))
        self.add(TaskAssignee(task_id=task.id, user_id=self.admin.id),
                 Reminder(user_id=self.admin.id, title='Call', remind_at=datetime.utcnow(), task_id=task.id))
        self.assertEqual(self.delete(f'/api/archive/tasks/{task.id}/permanent').status_code, 200)
        self.assertEqual((TaskAssignee.query.count(), Reminder.query.count()), (0, 0))

    def test_template_and_service_links_are_cleared(self):
        client = self.add(Client(name='Acme'))
        template = self.add(Template(name='Offer', type='offer', content='<p>Offer</p>'))
        service = self.add(Service(name='Support', client_id=client.id))
        offer, document, task = self.add(Offer(number='OF/1', title='Offer', client_id=client.id, template_id=template.id),
                                         Document(title='Annex', type='contract', service_id=service.id),
                                         Task(title='Onboard', service_id=service.id))
        self.assertEqual(self.delete(f'/api/templates/{template.id}').status_code, 200)
        self.assertEqual(self.delete(f'/api/services/{service.id}/permanent').status_code, 200)
        self.assertIsNone(db.session.get(Offer, offer.id).template_id)
        self.assertIsNone(db.session.get(Document, document.id).service_id)
        self.assertIsNone(db.session.get(Task, task.id).service_id)

    def test_user_with_only_personal_records_can_be_deleted(self):
        user = self.add(User(email='temp@example.com', first_name='Tim', last_name='Temp', role='employee', is_active=True, password_hash='unused'))
        self.add(Reminder(user_id=user.id, title='Personal', remind_at=datetime.utcnow()),
                 PushSubscription(user_id=user.id, endpoint_hash='a' * 64, subscription={'endpoint': 'https://push.example'}))
        self.assertEqual(self.delete(f'/api/users/{user.id}').status_code, 200)
        self.assertIsNone(db.session.get(User, user.id))

    def test_user_with_crm_history_or_phone_must_be_deactivated_instead(self):
        assignee = self.add(User(email='rep@example.com', first_name='Rita', last_name='Rep', role='employee', is_active=True, password_hash='unused'))
        self.add(Client(name='Acme', assignee_id=assignee.id))
        owner = self.add(User(email='phone@example.com', first_name='Pat', last_name='Phone', role='employee', is_active=True, password_hash='unused'))
        self.add(SmsDevice(name='Phone', token='OWNER_TEST_TOKEN', user_id=owner.id))
        handler = self.add(User(email='agent@example.com', first_name='Hal', last_name='Agent', role='employee', is_active=True, password_hash='unused'))
        self.add(Ticket(ticket_number='TIC-2026-0001', title='Help', description='Help', contact_email='c@example.com',
                        token=Ticket.generate_token(), assignee_id=handler.id))
        leader = self.add(User(email='lead@example.com', first_name='Lea', last_name='Lead', role='employee', is_active=True, password_hash='unused'))
        self.add(Team(name='Support', leader_id=leader.id))
        worker = self.add(User(email='work@example.com', first_name='Wes', last_name='Worker', role='employee', is_active=True, password_hash='unused'))
        task = self.add(Task(title='Ongoing'))
        self.add(TaskAssignee(task_id=task.id, user_id=worker.id))
        for user in (assignee, owner, handler, leader, worker):
            response = self.delete(f'/api/users/{user.id}')
            self.assertEqual(response.status_code, 409)
            self.assertIsNotNone(db.session.get(User, user.id))

    def test_client_with_project_is_refused(self):
        client = self.add(Client(name='Acme'))
        project = self.add(Project(name='Rollout', client_id=client.id))
        self.assertEqual(self.delete(f'/api/clients/{client.id}/permanent').status_code, 409)
        self.assertEqual(db.session.get(Project, project.id).client_id, client.id)

    def test_empty_archive_removes_archived_parents_after_their_archived_children(self):
        now = datetime.utcnow()
        client = self.add(Client(name='Gone', deleted_at=now))
        self.add(Project(name='Old project', client_id=client.id, deleted_at=now),
                 Task(title='Old task', client_id=client.id, deleted_at=now))
        response = self.client.post('/api/archive/empty', headers=self.headers)
        self.assertEqual(response.get_json()['deleted'], 3)
        self.assertEqual(response.get_json()['skipped'], [])

    def test_empty_archive_skips_records_that_are_still_linked(self):
        now = datetime.utcnow()
        client = self.add(Client(name='Linked', deleted_at=now))
        self.add(Lead(title='Live lead', client_id=client.id))
        contact = self.add(Contact(first_name='Old', deleted_at=now))
        response = self.client.post('/api/archive/empty', headers=self.headers)
        db.session.expire_all()
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body['deleted'], 1)
        self.assertEqual([(item['type'], item['id']) for item in body['skipped']], [('clients', client.id)])
        self.assertIsNone(db.session.get(Contact, contact.id))
        self.assertIsNotNone(db.session.get(Client, client.id))


if __name__ == '__main__':
    unittest.main()
