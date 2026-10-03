import unittest
from io import BytesIO
from pathlib import Path

from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.client import Client
from app.models.document import Document
from app.models.user import User
from app.models.workspace import PortalClientSpace, PortalItem, PortalMember, PortalReply, PortalSpace


class PortalLoginTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        admin = User(email='admin@test.local', password_hash='unused', first_name='Admin', last_name='Test', role='admin')
        client = Client(name='Firma testowa')
        space = PortalSpace(name='Portal firmy')
        db.session.add_all([admin, client, space])
        db.session.flush()
        db.session.add(PortalClientSpace(client_id=client.id, space_id=space.id))
        db.session.add(PortalMember(
            space_id=space.id,
            email='portal@test.local',
            password_hash=generate_password_hash('bezpieczne-haslo'),
        ))
        db.session.commit()
        self.admin_id = admin.id
        self.uploaded_files = []
        self.space_id = space.id
        self.client = self.app.test_client()

    def tearDown(self):
        for path in self.uploaded_files:
            path.unlink(missing_ok=True)
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_login_resolves_space_from_email(self):
        response = self.client.post('/api/portal/login', json={
            'email': ' PORTAL@test.local ',
            'password': 'bezpieczne-haslo',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['space_id'], self.space_id)
        self.assertTrue(response.get_json()['token'])

    def test_login_does_not_require_or_trust_space_id(self):
        response = self.client.post('/api/portal/login', json={
            'space_id': 999999,
            'email': 'portal@test.local',
            'password': 'bezpieczne-haslo',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['space_id'], self.space_id)

    def test_wrong_password_is_rejected(self):
        response = self.client.post('/api/portal/login', json={
            'email': 'portal@test.local',
            'password': 'zle-haslo',
        })
        self.assertEqual(response.status_code, 401)

    def test_portal_logo_upload_save_and_public_read(self):
        headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(self.admin_id))}
        uploaded = self.client.post(
            '/api/portal/branding',
            data={'file': (BytesIO(b'\x89PNG\r\n\x1a\nportal-logo'), 'logo.png')},
            headers=headers,
            content_type='multipart/form-data',
        )
        self.assertEqual(uploaded.status_code, 200)
        logo_url = uploaded.get_json()['url']
        self.uploaded_files.append(Path(self.app.instance_path) / 'portal_branding' / logo_url.rsplit('/', 1)[-1])
        saved = self.client.put('/api/portal/configuration', json={
            'address': '/portal.html',
            'enabled': True,
            'logo': logo_url,
            'login_background': '',
            'modules': ['document', 'offer', 'ticket', 'service', 'info'],
        }, headers=headers)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(self.client.get('/api/portal/configuration').get_json()['logo'], logo_url)
        public_logo = self.client.get(logo_url)
        self.assertEqual(public_logo.status_code, 200)
        public_logo.close()

    def test_admin_ticket_list_contains_client_context(self):
        ticket = PortalItem(space_id=self.space_id, kind='ticket', title='Problem z dokumentem', content='Proszę o pomoc')
        db.session.add(ticket)
        db.session.flush()
        db.session.add(PortalReply(item_id=ticket.id, author='portal@test.local', content='Dodatkowa informacja'))
        db.session.commit()
        headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(self.admin_id))}
        response = self.client.get('/api/portal/tickets', headers=headers)
        self.assertEqual(response.status_code, 200)
        row = response.get_json()[0]
        self.assertEqual(row['title'], 'Problem z dokumentem')
        self.assertEqual(row['client_name'], 'Firma testowa')
        self.assertEqual(row['space_id'], self.space_id)
        self.assertEqual(row['reply_count'], 1)

    def test_admin_creates_portal_for_specific_client(self):
        second_client = Client(name='Druga firma')
        db.session.add(second_client)
        db.session.commit()
        headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(self.admin_id))}
        response = self.client.post('/api/portal/spaces', json={
            'client_id': second_client.id,
            'name': 'Portal drugiej firmy',
            'description': 'Materiały klienta',
        }, headers=headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()['client_id'], second_client.id)
        self.assertIsNotNone(db.session.get(PortalClientSpace, second_client.id))
        self.assertEqual(response.get_json()['name'], second_client.name)

    def test_portal_content_is_limited_to_tickets_and_information(self):
        headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(self.admin_id))}
        path = f'/api/portal/spaces/{self.space_id}'
        for kind in ('document', 'offer', 'service'):
            response = self.client.post(path + '/items', json={'kind': kind, 'title': 'Ręczny materiał'}, headers=headers)
            self.assertEqual(response.status_code, 403)
        response = self.client.post(path + '/items', json={'kind': 'info', 'title': 'Godziny pracy', 'content': '8–16'}, headers=headers)
        self.assertEqual(response.status_code, 201)
        item_id = response.get_json()['id']
        changed = self.client.put(path + f'/items/{item_id}', json={'title': 'Kontakt', 'content': '9–17'}, headers=headers)
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(db.session.get(PortalItem, item_id).content, '9–17')
        original_client = db.session.get(Client, PortalClientSpace.query.filter_by(space_id=self.space_id).first().client_id)
        updated = self.client.put(path, json={'name': 'Ręczna nazwa', 'description': 'Opis powitalny'}, headers=headers)
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()['name'], original_client.name)
        original_client.name = 'Nowa nazwa klienta'
        db.session.commit()
        self.assertEqual(self.client.get(path, headers=headers).get_json()['name'], 'Nowa nazwa klienta')

    def test_other_clients_document_cannot_be_downloaded_from_space(self):
        other_client = Client(name='Inny klient')
        db.session.add(other_client)
        db.session.flush()
        document = Document(client_id=other_client.id, title='Prywatny dokument', type='other', content='Poufne')
        db.session.add(document)
        db.session.commit()
        headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(self.admin_id))}
        response = self.client.get(f'/api/portal/spaces/{self.space_id}/items/doc_{document.id}/file', headers=headers)
        self.assertEqual(response.status_code, 404)

    def test_admin_deletes_portal_space(self):
        headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(self.admin_id))}
        ticket = PortalItem(space_id=self.space_id, kind='ticket', title='Do usunięcia', content='Opis')
        db.session.add(ticket)
        db.session.commit()
        response = self.client.delete(f'/api/portal/spaces/{self.space_id}', headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(db.session.get(PortalSpace, self.space_id))
        self.assertIsNone(db.session.get(PortalItem, ticket.id))


if __name__ == '__main__':
    unittest.main()
