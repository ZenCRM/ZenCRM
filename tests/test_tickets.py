import unittest
from datetime import datetime
from flask_jwt_extended import create_access_token

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.user import User
from app.models.team import Team
from app.models.client import Client
from app.models.contact import Contact
from app.models.ticket import Ticket, TicketMessage
from app.models.workspace import PortalSpace, PortalItem, PortalClientSpace, PortalConfiguration
from app.models.document import Document
from app.models.offer import Offer
from app.models.service import Service
from app.models.setting import Setting


class TicketsTest(unittest.TestCase):
    def setUp(self):
        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'test-secret-key-with-at-least-32-bytes'

        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        admin = User(email='admin@tickets.local', password_hash='unused', first_name='Adam', last_name='Admin', role='admin')
        agent = User(email='agent@tickets.local', password_hash='unused', first_name='Jan', last_name='Kowalski', role='employee')
        db.session.add_all([admin, agent])
        db.session.commit()

        team = Team(name='Dział Wsparcia', color='#018bfc')
        db.session.add(team)
        db.session.commit()

        client = Client(name='ACME Corp', email='kontakt@acme.com', phone='123456789', assignee_id=agent.id)
        db.session.add(client)
        db.session.commit()

        self.admin = admin
        self.agent = agent
        self.team = team
        self.crm_client = client
        self.client = self.app.test_client()
        self.admin_headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(admin.id))}
        self.agent_headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(agent.id))}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_crm_ticket_crud_and_messages(self):
        # 1. Create ticket manually in CRM
        res = self.client.post('/api/tickets', json={
            'title': 'Awaria serwera',
            'description': 'Serwer nie odpowiada od 10 minut',
            'client_id': self.crm_client.id,
            'category': 'technical',
            'priority': 'urgent',
            'assignee_id': self.agent.id,
            'team_id': self.team.id
        }, headers=self.admin_headers)
        self.assertEqual(res.status_code, 201)
        tck_data = res.get_json()
        ticket_id = tck_data['id']
        self.assertEqual(tck_data['title'], 'Awaria serwera')
        self.assertEqual(tck_data['status'], 'new')
        self.assertEqual(tck_data['priority'], 'urgent')
        self.assertEqual(tck_data['client_id'], self.crm_client.id)
        self.assertEqual(tck_data['assignee_id'], self.agent.id)
        self.assertEqual(tck_data['team_id'], self.team.id)
        self.assertTrue(tck_data['ticket_number'].startswith('TIC-'))
        self.assertTrue(bool(tck_data['token']))

        # 2. List tickets
        res = self.client.get('/api/tickets', headers=self.agent_headers)
        self.assertEqual(res.status_code, 200)
        items = res.get_json()
        self.assertEqual(len(items), 1)

        # 3. Filter tickets
        res = self.client.get('/api/tickets?status=new&priority=urgent', headers=self.agent_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()), 1)

        res = self.client.get('/api/tickets?status=resolved', headers=self.agent_headers)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.get_json()), 0)

        # 4. Update ticket status & priority
        res = self.client.put(f'/api/tickets/{ticket_id}', json={
            'status': 'open',
            'priority': 'high'
        }, headers=self.agent_headers)
        self.assertEqual(res.status_code, 200)
        updated = res.get_json()
        self.assertEqual(updated['status'], 'open')
        self.assertEqual(updated['priority'], 'high')

        # 5. Add internal note
        res = self.client.post(f'/api/tickets/{ticket_id}/messages', json={
            'content': 'Sprawdziłem logi, restartuję usługę nginx.',
            'is_internal': True
        }, headers=self.agent_headers)
        self.assertEqual(res.status_code, 201)
        msg_data = res.get_json()
        self.assertTrue(msg_data['is_internal'])
        self.assertEqual(msg_data['sender_name'], 'Jan Kowalski')

        # 6. Add reply to customer (should update status to pending_client)
        res = self.client.post(f'/api/tickets/{ticket_id}/messages', json={
            'content': 'Szanowny Kliencie, usługa została zrestartowana i działa poprawnie.',
            'is_internal': False
        }, headers=self.agent_headers)
        self.assertEqual(res.status_code, 201)

        # Check full ticket details
        res = self.client.get(f'/api/tickets/{ticket_id}', headers=self.agent_headers)
        self.assertEqual(res.status_code, 200)
        full_ticket = res.get_json()
        self.assertEqual(full_ticket['status'], 'pending_client')
        self.assertEqual(len(full_ticket['messages']), 3)  # Initial description message + note + reply

    def test_ticket_number_stays_unique_after_deletion(self):
        def create():
            res = self.client.post('/api/tickets', json={'title': 'Outage', 'description': 'Server is down'},
                                   headers=self.admin_headers)
            self.assertEqual(res.status_code, 201)
            return res.get_json()
        first, second, third = create(), create(), create()
        self.assertEqual(self.client.delete(f"/api/tickets/{second['id']}", headers=self.admin_headers).status_code, 200)
        fourth = create()
        self.assertNotIn(fourth['ticket_number'], {first['ticket_number'], third['ticket_number']})
        self.assertTrue(fourth['ticket_number'].endswith('-0004'))

    def test_ticket_number_sequence_passes_9999(self):
        year = datetime.utcnow().strftime('%Y')
        db.session.add(Ticket(ticket_number=f'TIC-{year}-9999', title='Last', description='Last', contact_email='a@b.c', token=Ticket.generate_token()))
        db.session.add(Ticket(ticket_number=f'TIC-{year}-10000', title='Next', description='Next', contact_email='a@b.c', token=Ticket.generate_token()))
        db.session.commit()
        self.assertEqual(Ticket.generate_number(), f'TIC-{year}-10001')

    def test_public_helpdesk_submit_and_tracking(self):
        # 1. Check public config
        res = self.client.get('/api/tickets/public/config')
        self.assertEqual(res.status_code, 200)
        conf = res.get_json()
        self.assertTrue(conf['enabled'])
        self.assertEqual(conf['path'], '/pomoc')
        self.assertTrue(len(conf['categories']) > 0)

        # 2. Public submit ticket (matching ACME Corp email)
        res = self.client.post('/api/tickets/public/submit', json={
            'name': 'Jan Nowak',
            'email': 'kontakt@acme.com',
            'phone': '987654321',
            'category': 'billing',
            'title': 'Pytanie o fakturę VAT',
            'description': 'Proszę o przesłanie duplikatu faktury za wrzesień.'
        })
        self.assertEqual(res.status_code, 201)
        sub_data = res.get_json()
        self.assertTrue(sub_data['ok'])
        token = sub_data['token']
        self.assertTrue(bool(token))

        # Check in DB that client was automatically linked and ticket was assigned to client's assignee
        ticket = Ticket.query.filter_by(token=token).first()
        self.assertIsNotNone(ticket)
        self.assertEqual(ticket.client_id, self.crm_client.id)
        self.assertEqual(ticket.assignee_id, self.agent.id)  # Auto-assigned because client has assignee_id

        # 3. Track ticket publicly via token (no auth required)
        res = self.client.get(f'/api/tickets/public/track/{token}')
        self.assertEqual(res.status_code, 200)
        track_data = res.get_json()
        self.assertEqual(track_data['title'], 'Pytanie o fakturę VAT')
        self.assertEqual(len(track_data['messages']), 1)

        # 4. Client replies to ticket via tracking link
        res = self.client.post(f'/api/tickets/public/track/{token}/reply', json={
            'content': 'Dodatkowo proszę o informację o terminie płatności.'
        })
        self.assertEqual(res.status_code, 201)

        # Check that message was appended and ticket status changed back to open
        res = self.client.get(f'/api/tickets/public/track/{token}')
        track_data = res.get_json()
        self.assertEqual(track_data['status'], 'open')
        self.assertEqual(len(track_data['messages']), 2)

    def test_webhook_ticket_ingestion(self):
        # 1. Get webhook settings to obtain token
        res = self.client.get('/api/tickets/settings', headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        settings = res.get_json()
        webhook_token = settings['helpdesk_webhook_token']
        self.assertTrue(bool(webhook_token))

        # 2. Call webhook without token -> 401
        res = self.client.post('/api/tickets/webhook', json={
            'title': 'Test webhook',
            'email': 'user@example.com',
            'description': 'Opis'
        })
        self.assertEqual(res.status_code, 401)

        # 3. Call webhook with valid token
        res = self.client.post('/api/tickets/webhook', json={
            'title': 'Zgłoszenie z formularza WWW',
            'email': 'klient@nowy.pl',
            'name': 'Marek Klient',
            'category': 'technical',
            'priority': 'medium',
            'description': 'Formularz kontaktowy z landing page'
        }, headers={'X-Webhook-Token': webhook_token})
        self.assertEqual(res.status_code, 201)
        wh_data = res.get_json()
        self.assertTrue(wh_data['ok'])
        ticket_id = wh_data['id']

        tck = db.session.get(Ticket, ticket_id)
        self.assertEqual(tck.source, 'webhook')
        self.assertEqual(tck.contact_email, 'klient@nowy.pl')

    def test_portal_space_client_documents_and_tickets(self):
        # 1. Create client documents, offers and services
        doc = Document(client_id=self.crm_client.id, title='Umowa Ramowa 2026', type='contract', status='final', content='Tresc umowy')
        offer = Offer(client_id=self.crm_client.id, title='Oferta IT', number='OF/2026/001', status='accepted', total_amount=15000.0)
        service = Service(client_id=self.crm_client.id, name='Opieka IT 24/7', status='active', price=2500.0, billing_cycle='monthly')
        db.session.add_all([doc, offer, service])
        db.session.commit()

        # 2. Create PortalSpace and link to client via PortalClientSpace
        space = PortalSpace(name='Strefa ACME Corp', description='Strefa klienta')
        db.session.add(space)
        db.session.commit()

        mapping = PortalClientSpace(client_id=self.crm_client.id, space_id=space.id)
        db.session.add(mapping)
        db.session.commit()

        # 3. Admin views space detail -> client documents, offers, and services are automatically included!
        res = self.client.get(f'/api/portal/spaces/{space.id}', headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        kinds = [it['kind'] for it in data['items']]
        self.assertIn('document', kinds)
        self.assertIn('offer', kinds)
        self.assertIn('service', kinds)

        # 4. Create ticket in portal space -> auto-creates CRM Ticket
        res = self.client.post(f'/api/portal/spaces/{space.id}/items', json={
            'kind': 'ticket',
            'title': 'Problem ze sprzętem',
            'content': 'Drukarka biurowa zgłasza błąd tonera'
        }, headers=self.admin_headers)
        self.assertEqual(res.status_code, 201)

        # Check CRM tickets for ACME Corp
        res = self.client.get(f'/api/tickets?client_id={self.crm_client.id}', headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        client_tickets = res.get_json()
        self.assertEqual(len(client_tickets), 1)
        self.assertEqual(client_tickets[0]['title'], 'Problem ze sprzętem')
        self.assertEqual(client_tickets[0]['source'], 'portal')

    def test_portal_hides_draft_documents_and_offers(self):
        draft_doc = Document(client_id=self.crm_client.id, title='Internal draft', type='contract', status='draft', content='Internal notes')
        final_doc = Document(client_id=self.crm_client.id, title='Signed contract', type='contract', status='final', content='Contract body')
        draft_offer = Offer(client_id=self.crm_client.id, title='Draft offer', number='OF/DRAFT', status=' Draft ', content='Margin notes')
        unset_doc = Document(client_id=self.crm_client.id, title='No status', type='contract', content='Internal')
        sent_offer = Offer(client_id=self.crm_client.id, title='Sent offer', number='OF/SENT', status='sent', total_amount=100.0)
        space = PortalSpace(name='ACME space')
        db.session.add_all([draft_doc, final_doc, draft_offer, sent_offer, unset_doc, space])
        db.session.flush()
        unset_doc.status = None
        db.session.commit()
        db.session.add(PortalClientSpace(client_id=self.crm_client.id, space_id=space.id))
        db.session.commit()

        res = self.client.get(f'/api/portal/spaces/{space.id}', headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        item_ids = {item['id'] for item in res.get_json()['items']}
        self.assertIn(f'doc_{final_doc.id}', item_ids)
        self.assertIn(f'offer_{sent_offer.id}', item_ids)
        self.assertNotIn(f'doc_{draft_doc.id}', item_ids)
        self.assertNotIn(f'offer_{draft_offer.id}', item_ids)
        self.assertNotIn(f'doc_{unset_doc.id}', item_ids)

        for item_id in (f'doc_{draft_doc.id}', f'offer_{draft_offer.id}', f'doc_{unset_doc.id}'):
            res = self.client.get(f'/api/portal/spaces/{space.id}/items/{item_id}/file', headers=self.admin_headers)
            self.assertEqual(res.status_code, 404)

    def test_helpdesk_settings_are_validated(self):
        manager = User(email='manager@tickets.local', password_hash='unused', first_name='Mia', last_name='Manager', role='manager')
        db.session.add(manager)
        db.session.commit()
        manager_headers = {'Authorization': 'Bearer ' + create_access_token(identity=str(manager.id))}
        current = self.client.get('/api/tickets/settings', headers=self.admin_headers).get_json()

        def save(payload, headers=None):
            return self.client.put('/api/tickets/settings', json=payload, headers=headers or self.admin_headers).status_code

        self.assertEqual(save({'helpdesk_webhook_token': current['helpdesk_webhook_token'], 'helpdesk_title': 'Help'}, manager_headers), 200)
        self.assertEqual(save({'helpdesk_webhook_token': 'a' * 40}, manager_headers), 403)
        self.assertEqual(save({'helpdesk_webhook_token': 'short'}), 400)
        db.session.add(PortalConfiguration(id=1, data={'address': '/client-zone'}))
        db.session.commit()
        for path in ('/api/help', '/client-zone', 'https://evil.example/help', '/help?x=1', '/../help'):
            self.assertEqual(save({'helpdesk_path': path}), 400, path)
        self.assertEqual(save({'helpdesk_enabled': 'yes'}), 400)
        self.assertEqual(save({'helpdesk_default_user_id': 'admin'}), 400)
        self.assertEqual(save({'helpdesk_categories': 'technical'}), 400)
        self.assertEqual(save({'helpdesk_accent_color': 'red;background:url(x)'}), 400)
        self.assertEqual(save({'helpdesk_logo': 'javascript:alert(1)'}), 400)
        self.assertEqual(save({'helpdesk_logo': '/\\evil.example/x.png'}), 400)
        # Values stored before validation existed can be saved back unchanged.
        Setting.set_value('helpdesk_path', '/help.html')
        db.session.commit()
        legacy = self.client.get('/api/tickets/settings', headers=self.admin_headers).get_json()
        self.assertEqual(save(legacy), 200)
        self.assertEqual(save({'helpdesk_path': '/support', 'helpdesk_enabled': False, 'helpdesk_default_user_id': None,
                               'helpdesk_categories': [{'id': 'general', 'name': 'General'}]}), 200)
        self.assertEqual(self.client.get('/api/tickets/settings', headers=self.admin_headers).get_json()['helpdesk_path'], '/support')

    def test_helpdesk_custom_content_and_logo_settings(self):
        # 1. Update settings with custom content and custom logo
        res = self.client.put('/api/tickets/settings', json={
            'helpdesk_title': 'Biuro Obsługi Klienta',
            'helpdesk_header_subtitle': 'Dział Wsparcia 24/7',
            'helpdesk_badge': 'Formularz zgłoszeniowy',
            'helpdesk_heading': 'Jak możemy pomóc?',
            'helpdesk_description': 'Opisz problem poniżej, odpowiemy w 15 minut.',
            'helpdesk_success_heading': 'Dziękujemy za zgłoszenie!',
            'helpdesk_success_description': 'Nasz zespół przystępuje do działania.',
            'helpdesk_footer_text': 'Wsparcie techniczne ZenCRM Inc.',
            'helpdesk_logo': '/uploads/custom_logo.png'
        }, headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        updated = res.get_json()
        self.assertEqual(updated['helpdesk_title'], 'Biuro Obsługi Klienta')
        self.assertEqual(updated['helpdesk_header_subtitle'], 'Dział Wsparcia 24/7')
        self.assertEqual(updated['helpdesk_badge'], 'Formularz zgłoszeniowy')
        self.assertEqual(updated['helpdesk_heading'], 'Jak możemy pomóc?')
        self.assertEqual(updated['helpdesk_logo'], '/uploads/custom_logo.png')

        # 2. Check public config returns custom content and logo
        res = self.client.get('/api/tickets/public/config')
        self.assertEqual(res.status_code, 200)
        pub_conf = res.get_json()
        self.assertEqual(pub_conf['title'], 'Biuro Obsługi Klienta')
        self.assertEqual(pub_conf['header_subtitle'], 'Dział Wsparcia 24/7')
        self.assertEqual(pub_conf['badge'], 'Formularz zgłoszeniowy')
        self.assertEqual(pub_conf['heading'], 'Jak możemy pomóc?')
        self.assertEqual(pub_conf['description'], 'Opisz problem poniżej, odpowiemy w 15 minut.')
        self.assertEqual(pub_conf['success_heading'], 'Dziękujemy za zgłoszenie!')
        self.assertEqual(pub_conf['success_description'], 'Nasz zespół przystępuje do działania.')
        self.assertEqual(pub_conf['footer_text'], 'Wsparcie techniczne ZenCRM Inc.')
        self.assertEqual(pub_conf['logo'], '/uploads/custom_logo.png')


if __name__ == '__main__':
    unittest.main()
