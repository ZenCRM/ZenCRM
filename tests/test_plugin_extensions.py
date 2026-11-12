from datetime import date, datetime
from decimal import Decimal
import unittest
from app.extensions import db
from app.models.lead import Lead
from app.models.project import Project, ProjectMember
from app.models.ticket import Ticket
from app.models.document import Document
from app.models.offer import Offer
from app.models.service import Service
from app.models.meeting import Meeting
from app.plugins.reports import SOURCES
from tests import test_plugins as fixtures


class ExtendedReportsTest(unittest.TestCase):
    setUp = fixtures.PluginTest.setUp
    tearDown = fixtures.PluginTest.tearDown
    post = fixtures.PluginTest.post
    access = fixtures.PluginTest.access
    call = fixtures.PluginTest.call
    report_access = fixtures.PluginTest.report_access


class ExtendedReportTests(ExtendedReportsTest):
    def populate(self):
        first, other = self.users['employee'].id, self.users['other'].id
        now = datetime(2020, 2, 15)
        for uid, client in [(first, self.own), (other, self.other)]:
            db.session.add_all([
                Lead(title='Private lead', assignee_id=uid, stage='new', source='web', value=Decimal('123.45'), created_at=now),
                Project(name='Private project', manager_id=uid, budget=Decimal('200.15'), created_at=now),
                Ticket(ticket_number=f'T-{uid}', title='Private ticket', description='Secret body', contact_email=f'secret-{uid}@test.com', token=f'token-{uid}', assignee_id=uid, created_at=now),
                Document(title='Private doc', created_by=uid, type='contract', created_at=now),
                Offer(number=f'O-{uid}', title='Private offer', client_id=client.id, created_by=uid, total_amount=Decimal('456.78'), valid_until=date(2020, 2, 15), created_at=now),
                Service(name='Private service', client_id=client.id, price=Decimal('33.30'), billing_cycle='monthly', created_at=now),
                Meeting(title='Private meeting', organizer_id=uid, start_time=now, end_time=datetime(2020, 2, 15, 17), created_at=now),
            ])
        db.session.commit()

    def test_all_sources_respect_ownership_and_return_only_aggregates(self):
        token = self.report_access(); self.populate()
        for entity in SOURCES.keys() - {'tasks', 'clients'}:
            with self.subTest(entity=entity):
                result = self.call(token, 'reports.aggregate', {'entity': entity})
                self.assertEqual(result.status_code, 200, result.json)
                self.assertEqual(result.json['total'], 1)
                self.assertNotIn('secret', str(result.json).lower())
                self.assertNotIn('Private', str(result.json))
        admin = self.report_access('admin')
        for entity in SOURCES.keys() - {'tasks', 'clients'}:
            self.assertEqual(self.call(admin, 'reports.aggregate', {'entity': entity}).json['total'], 2)

    def test_membership_and_deleted_records(self):
        token = self.report_access(); self.populate()
        project = Project.query.filter_by(manager_id=self.users['other'].id).one()
        db.session.add(ProjectMember(project_id=project.id, user_id=self.users['employee'].id))
        db.session.commit()
        self.assertEqual(self.call(token, 'reports.aggregate', {'entity':'projects'}).json['total'], 2)
        project.deleted_at = datetime.utcnow()
        own_lead = Lead.query.filter_by(assignee_id=self.users['employee'].id).one(); own_lead.deleted_at=datetime.utcnow()
        self.own.deleted_at=datetime.utcnow(); db.session.commit()
        for entity, expected in [('projects',1),('leads',0),('services',0)]:
            self.assertEqual(self.call(token, 'reports.aggregate', {'entity':entity}).json['total'], expected)

    def test_money_filters_month_groups_and_previous_period(self):
        token = self.report_access(); self.populate()
        db.session.add(Lead(title='Prior', assignee_id=self.users['employee'].id, value=Decimal('100.15'), created_at=datetime(2020,1,25), source='web'))
        db.session.add(Lead(title='Current', assignee_id=self.users['employee'].id, value=Decimal('33.25'), created_at=datetime(2020,2,20), source='web'))
        db.session.commit()
        result = self.call(token, 'reports.aggregate', {'entity':'leads','group_by':'month','date_from':'2020-02-01','date_to':'2020-02-29','compare_previous':True}).json
        self.assertEqual(result['total'],2); self.assertEqual(result['metrics']['amount'],'156.70')
        self.assertEqual(result['rows'][0]['label'],'2020-02')
        self.assertEqual(result['comparison']['total'],1); self.assertEqual(result['comparison']['change'],1)
        self.assertEqual(result['comparison']['change_percent'],100); self.assertEqual(result['comparison']['amount'],'100.15')
        filtered = self.call(token,'reports.aggregate',{'entity':'leads','amount_min':'100','amount_max':'124'}).json
        self.assertEqual(filtered['total'],2); self.assertEqual(filtered['metrics']['amount'],'223.60')

    def test_date_columns_include_whole_date_and_deny_arbitrary_fields(self):
        token = self.report_access(); self.populate()
        self.assertEqual(self.call(token,'reports.aggregate',{'entity':'offers','date_field':'valid_until','date_from':'2020-02-15','date_to':'2020-02-15'}).json['total'],1)
        self.assertEqual(self.call(token,'reports.aggregate',{'entity':'meetings','date_field':'start_time','date_from':'2020-02-15','date_to':'2020-02-15'}).json['total'],1)
        for params in [{'entity':'leads','date_field':'notes'}, {'entity':'clients','group_by':'email'}, {'entity':'leads','amount_min':'NaN'},
                       {'entity':'leads','amount_max':True},{'entity':'tasks','amount_min':'1'}, {'entity':'leads','amount_min':10,'amount_max':1},
                       {'compare_previous':True}, {'date_from':'1900-01-01','date_to':'1900-01-10','compare_previous':True}]:
            self.assertEqual(self.call(token,'reports.aggregate',params).status_code,400)

    def test_capabilities_require_consent_and_have_no_business_data(self):
        self.assertEqual(self.client.get('/api/plugins/reports/capabilities',headers=self.headers['employee']).status_code,403)
        token=self.report_access()
        response=self.call(token,'reports.capabilities')
        self.assertEqual(set(response.json),set(SOURCES))
        self.assertIn('source',response.json['leads']['groups']);self.assertIn('month',response.json['leads']['groups'])
        self.assertNotIn('rows',str(response.json))
