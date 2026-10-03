import unittest
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User
from app.models.client import Client
from app.models.contact import Contact
from app.models.task import Task
from app.models.project import Project
from app.models.meeting import Meeting
from app.models.setting import Setting
from app.services.email_service import render_template
from datetime import datetime


class ArchiveAndFieldsTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        user = User(id=1, email='admin@test.com', first_name='Adam', last_name='Kowalski', role='admin')
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()

        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def auth_headers(self, uid=1):
        return {'Authorization': 'Bearer ' + create_access_token(identity=str(uid))}

    def test_contact_creation_without_last_name(self):
        """Sprawdza czy kontakt można dodać bez nazwiska (gdy pole nie jest wymagane)."""
        res = self.client.post('/api/contacts', json={
            'first_name': 'Michał',
            'email': 'michal@test.pl'
        }, headers=self.auth_headers(1))
        self.assertEqual(res.status_code, 201)
        data = res.get_json()
        self.assertEqual(data['first_name'], 'Michał')
        self.assertEqual(data['last_name'], '')

    def test_archive_listing_and_deleted_by_info(self):
        """Sprawdza czy usunięcie elementu trafia do archiwum z informacją o usuwającym użytkowniku."""
        # Utwórz klienta
        client = Client(name='Firma ABC', email='kontakt@abc.pl')
        db.session.add(client)
        # Utwórz zadanie
        task = Task(title='Wdrożenie CRM')
        db.session.add(task)
        # Utwórz projekt
        project = Project(name='Projekt Sklep', status='in_progress')
        db.session.add(project)
        db.session.commit()

        # Usuń zadanie przez API
        res = self.client.delete(f'/api/tasks/{task.id}', headers=self.auth_headers(1))
        self.assertEqual(res.status_code, 200)

        # Usuń klienta przez API
        res = self.client.delete(f'/api/clients/{client.id}', headers=self.auth_headers(1))
        self.assertEqual(res.status_code, 200)

        # Usuń projekt przez API
        res = self.client.delete(f'/api/projects/{project.id}', headers=self.auth_headers(1))
        self.assertEqual(res.status_code, 200)

        # Pobierz archiwum
        res = self.client.get('/api/archive', headers=self.auth_headers(1))
        self.assertEqual(res.status_code, 200)
        arch = res.get_json()
        self.assertGreaterEqual(arch['total'], 3)

        items_by_type = {it['_type']: it for it in arch['items']}
        self.assertIn('tasks', items_by_type)
        self.assertIn('clients', items_by_type)
        self.assertIn('projects', items_by_type)

        # Sprawdź deleted_by
        task_item = items_by_type['tasks']
        self.assertIsNotNone(task_item.get('deleted_at'))
        self.assertIsNotNone(task_item.get('deleted_by'))
        self.assertEqual(task_item['deleted_by']['name'], 'Adam Kowalski')

        # Sprawdź podgląd
        res = self.client.get(f'/api/archive/tasks/{task.id}', headers=self.auth_headers(1))
        self.assertEqual(res.status_code, 200)
        prev = res.get_json()
        self.assertEqual(prev['title'], 'Wdrożenie CRM')

        # Przywróć klienta
        res = self.client.post(f'/api/archive/clients/{client.id}/restore', headers=self.auth_headers(1))
        self.assertEqual(res.status_code, 200)

        # Klient nie powinien być już w archiwum
        res = self.client.get('/api/archive', headers=self.auth_headers(1))
        arch2 = res.get_json()
        remaining_ids = [it['id'] for it in arch2['items'] if it['_type'] == 'clients']
        self.assertNotIn(client.id, remaining_ids)

    def test_email_template_logo_injection(self):
        """Sprawdza czy render_template dodaje logo do treści maila."""
        Setting.set_value('brand_logo_light', '/uploads/branding/logo.png', 'branding')
        Setting.set_value('company_name', 'SuperCRM', 'company')
        db.session.commit()

        subject, html = render_template('client_ticket_created', {
            'client_name': 'Jan',
            'ticket_number': 'TK-1',
            'ticket_title': 'Awaria',
            'ticket_category': 'Ogólne',
            'ticket_url': 'https://crm.local/portal'
        })

        self.assertIn('TK-1', subject)
        self.assertIn('Jan', html)
        self.assertIn('logo.png', html)
        self.assertIn('<img', html)


if __name__ == '__main__':
    unittest.main()
