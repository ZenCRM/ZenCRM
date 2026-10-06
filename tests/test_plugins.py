import copy
import hashlib
import hmac
import json
import socket
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from flask_jwt_extended import create_access_token
from sqlalchemy import inspect
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.orm import Session

from app import create_app
from app.config import Config
from app.extensions import db
from app.models.client import Client
from app.models.task import Task
from app.models.user import User
from app.models.permission import Role, PermissionRule
from app.models.setting import Setting
from app.plugins.manifest import validate_manifest
from app.plugins.models import PluginApp, PluginGrant, PluginToken, PluginCode, PluginStorage, PluginEvent, PluginDelivery
from app.plugins.tokens import challenge, digest
from app.plugins.events import emit_client_event
from app.plugins.worker import run_once
from app.plugins.transport import send_event, PublicHTTPS
from app.plugins.bundled import BUNDLED, ALL_USERS, seed_bundled, bundled_metadata

ROOT = Path(__file__).resolve().parents[1]


class PluginTest(unittest.TestCase):
    def setUp(self):
        class C(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = 'sqlite://'
            JWT_SECRET_KEY = 'plugin-tests-with-at-least-thirty-two-bytes'
            SECRET_KEY = 'plugin-encryption-tests-only'
            PLUGINS_ENABLED = True
            PLUGINS_LOCKED = False
            PUBLIC_BASE_URL = 'https://crm.example.com'
            PREPARE_DATABASE = False
            PUSH_ENABLED = False
            MAIL_POLLING_ENABLED = False
        self.app = create_app(C)
        self.ctx = self.app.app_context(); self.ctx.push()
        db.create_all()
        self.client = self.app.test_client()
        self.users = {}; self.headers = {}
        for name, role in [('admin', 'admin'), ('employee', 'employee'), ('other', 'employee')]:
            user = User(email=name+'@example.com', first_name=name, last_name='Test', role=role, is_active=True)
            user.set_password('test-password')
            db.session.add(user); db.session.flush()
            self.users[name] = user
            self.headers[name] = {'Authorization': 'Bearer ' + create_access_token(identity=str(user.id))}
        db.session.add(Role(key='employee', name='Employee'))
        self.own = Client(name='Own', assignee_id=self.users['employee'].id, notes='secret notes')
        self.other = Client(name='Other', assignee_id=self.users['other'].id)
        self.archived = Client(name='Archived', assignee_id=self.users['employee'].id, deleted_at=datetime.utcnow())
        db.session.add_all([self.own, self.other, self.archived])
        db.session.add_all([Task(title='In progress', status='in_progress', assignee_id=self.users['employee'].id),
                            Task(title='Private', assignee_id=self.users['other'].id),
                            Task(title='Done', status='done', assignee_id=self.users['employee'].id)])
        db.session.commit()

    def tearDown(self):
        db.session.remove(); db.drop_all(); db.engine.dispose(); self.ctx.pop()

    def post(self, path, payload, user='admin'):
        return self.client.post('/api/plugins'+path, json=payload, headers=self.headers[user])

    def remote(self, app_id='client-tools-demo'):
        manifest = json.loads((ROOT/'plugins/examples/remote/manifest.json').read_text(encoding='utf-8'))
        manifest['id'] = app_id
        return manifest

    def install(self, manifest=None):
        manifest = manifest or self.remote()
        registered = self.post('/apps', manifest)
        self.assertEqual(registered.status_code, 201, registered.json)
        app_id = manifest['id']
        credentials = self.post('/apps/'+app_id+'/credentials', {}) if manifest['type']=='remote' else None
        app = db.session.get(PluginApp, app_id)
        installed = self.post('/apps/'+app_id+'/install', {'revision': app.revision, 'scopes':manifest['scopes'],
                              'allowed_users': [u.id for u in self.users.values()], 'configuration': {}})
        self.assertEqual(installed.status_code, 200, installed.json)
        enabled = self.post('/apps/'+app_id+'/enable', {'revision': installed.json['revision']})
        self.assertEqual(enabled.status_code, 200, enabled.json)
        for user in self.users:
            consent = self.post('/apps/'+app_id+'/consent', {'revision':enabled.json['revision'], 'scopes':manifest['scopes']}, user)
            self.assertEqual(consent.status_code, 200, consent.json)
        return app_id, credentials.json if credentials else None

    def access(self, app_id, user='employee'):
        response = self.post('/apps/'+app_id+'/personal-token', {'days':1}, user)
        self.assertEqual(response.status_code, 201, response.json)
        return response.json['access_token']

    def call(self, token, operation, params=None):
        return self.client.post('/api/plugin-api/v1/call', json={'operation':operation,'params':params or {}},
                                headers={'Authorization':'Bearer '+token})

    def oauth(self, app_id, secret, user='employee'):
        verifier = 'a'*64
        uri = 'https://apps.example.com/oauth/callback'
        auth = self.post('/apps/'+app_id+'/authorize', {'response_type':'code','redirect_uri':uri,
            'code_challenge_method':'S256','code_challenge':challenge(verifier), 'state':'random-state-with-entropy'}, user)
        self.assertEqual(auth.status_code, 200, auth.json)
        payload = {'grant_type':'authorization_code','client_id':app_id,'client_secret':secret,
                   'redirect_uri':uri,'code':auth.json['code'],'code_verifier':verifier}
        return payload

    def test_feature_off_and_private_by_default(self):
        self.app.config['PLUGINS_ENABLED'] = False
        self.assertEqual(self.client.get('/api/plugins/status').status_code, 401)
        self.assertEqual(self.client.get('/api/plugins/status', headers=self.headers['employee']).json['enabled'], False)
        self.assertEqual(self.client.get('/api/plugins/apps', headers=self.headers['admin']).status_code, 503)
        self.assertEqual(self.call('fake', 'clients.list').status_code, 503)
        self.assertEqual(self.client.post('/api/plugin-api/v1/unknown').status_code, 404)

    def test_bundled_store_is_preinstalled_without_implicit_consent(self):
        seed_bundled()
        for item in BUNDLED.values():
            self.assertEqual(validate_manifest(item['manifest']), item['manifest'])
        self.assertEqual(self.client.get('/api/plugins/store').status_code, 401)
        response = self.client.get('/api/plugins/store', headers=self.headers['employee'])
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json), 3)
        for app in response.json:
            self.assertTrue(app['bundled'] and app['installed'] and app['available'])
            self.assertEqual(app['consented_scopes'], [])
            self.assertNotIn('allowed_users', app)
            self.assertNotIn('configuration', app)
            denied = self.post('/apps/'+app['id']+'/invoke', {'operation': app['manifest']['placements'][0]['operation']}, 'employee')
            self.assertEqual(denied.status_code, 403)
        self.assertEqual(PluginGrant.query.count(), 0)
        self.assertEqual(PluginToken.query.count(), 0)

    def test_bundled_read_scope_and_record_boundaries(self):
        seed_bundled()
        for app_id, operation, expected in [
            ('zencrm-work-summary', 'reports.summary', None),
            ('zencrm-client-directory', 'clients.list', ['Own']),
            ('zencrm-task-list', 'tasks.list', ['In progress', 'Done']),
        ]:
            app = db.session.get(PluginApp, app_id)
            grant = self.post('/apps/'+app_id+'/consent', {'revision':app.revision, 'scopes':app.approved_scopes}, 'employee')
            self.assertEqual(grant.status_code, 200, grant.json)
            result = self.post('/apps/'+app_id+'/invoke', {'operation':operation}, 'employee')
            self.assertEqual(result.status_code, 200, result.json)
            if expected:
                self.assertEqual([item.get('name', item.get('title')) for item in result.json['items']], expected)
            else:
                self.assertEqual(result.json['clients'], 1)
                self.assertEqual(result.json['open_tasks'], 1)
            self.assertEqual(self.post('/apps/'+app_id+'/invoke', {'operation':'clients.update', 'params':{'id':self.own.id, 'fields':{'name':'Changed'}}}, 'employee').status_code, 403)
            self.assertEqual(self.post('/apps/'+app_id+'/consent', {'revision':app.revision, 'scopes':['clients.write']}, 'employee').status_code, 400)

    def test_bundled_seed_preserves_admin_disable_uninstall_and_audience(self):
        seed_bundled()
        app = db.session.get(PluginApp, 'zencrm-work-summary')
        self.assertEqual(self.post('/apps/'+app.id+'/disable', {'revision':app.revision}, 'employee').status_code, 403)
        response = self.post('/apps/'+app.id+'/disable', {'revision':app.revision})
        self.assertEqual(response.status_code, 200)
        response = self.post('/apps/'+app.id+'/install', {'revision':response.json['revision'], 'scopes':['reports.read'],
                    'allowed_users':[self.users['admin'].id], 'all_users':False})
        self.assertEqual(response.status_code, 200, response.json)
        self.post('/apps/'+app.id+'/enable', {'revision':response.json['revision']})
        other = db.session.get(PluginApp, 'zencrm-task-list')
        self.post('/apps/'+other.id+'/uninstall', {'revision':other.revision})
        before = [(row.id, row.revision, row.installed, row.enabled, row.allowed_users[:]) for row in PluginApp.query.order_by(PluginApp.id)]
        seed_bundled(); seed_bundled()
        self.assertEqual(before, [(row.id, row.revision, row.installed, row.enabled, row.allowed_users) for row in PluginApp.query.order_by(PluginApp.id)])
        store = self.client.get('/api/plugins/store', headers=self.headers['employee']).json
        self.assertFalse(next(row for row in store if row['id']==app.id)['available'])
        self.assertFalse(next(row for row in store if row['id']==other.id)['available'])
        self.assertEqual(self.post('/apps/'+app.id+'/consent', {'revision':app.revision, 'scopes':['reports.read']}, 'employee').status_code, 403)
        self.post('/apps/'+app.id+'/disable', {'revision':app.revision})
        # Explicit all-users approval is restricted to reviewed bundled definitions.
        self.assertEqual(self.post('/apps/'+app.id+'/install', {'revision':app.revision, 'scopes':['reports.read'],
                    'allowed_users':[self.users['admin'].id], 'all_users':True}).status_code, 400)
        response = self.post('/apps/'+app.id+'/install', {'revision':app.revision, 'scopes':['reports.read'],
                    'allowed_users':[], 'all_users':True})
        self.assertEqual(response.status_code, 200, response.json)
        self.assertTrue(response.json['all_users'])
        self.post('/apps/'+app.id+'/enable', {'revision':response.json['revision']})
        self.assertEqual(self.post('/apps/'+app.id+'/consent', {'revision':app.revision, 'scopes':['reports.read']}, 'employee').status_code, 200)

    def test_all_users_audience_requires_canonical_bundled_definition(self):
        seed_bundled()
        user = User(email='new@example.com', first_name='New', last_name='User', role='employee', is_active=True)
        user.set_password('test-password'); db.session.add(user); db.session.commit()
        headers = {'Authorization':'Bearer '+create_access_token(identity=str(user.id))}
        self.assertEqual(len(self.client.get('/api/plugins/apps', headers=headers).json), 3)
        app = db.session.get(PluginApp, 'zencrm-work-summary')
        app.manifest = {**app.manifest, 'name':'Impostor'}; db.session.commit()
        self.assertFalse(bundled_metadata(app)['bundled'])
        self.assertEqual(len(self.client.get('/api/plugins/apps', headers=headers).json), 2)
        user.is_active = False; db.session.commit()
        self.assertEqual(self.client.get('/api/plugins/store', headers=headers).status_code, 403)

    def test_store_hides_external_apps_outside_approved_audience(self):
        seed_bundled()
        app_id, _ = self.install()
        app = db.session.get(PluginApp, app_id)
        self.post('/apps/'+app_id+'/disable', {'revision':app.revision})
        response = self.post('/apps/'+app_id+'/install', {'revision':app.revision, 'scopes':app.manifest['scopes'], 'allowed_users':[self.users['admin'].id]})
        self.post('/apps/'+app_id+'/enable', {'revision':response.json['revision']})
        store = self.client.get('/api/plugins/store', headers=self.headers['employee']).json
        self.assertEqual(len(store), 3)
        self.assertEqual(len(self.client.get('/api/plugins/store', headers=self.headers['admin']).json), 4)
        self.post('/apps/'+app_id+'/disable', {'revision':app.revision})
        self.assertEqual(self.post('/apps/'+app_id+'/install', {'revision':app.revision, 'scopes':app.manifest['scopes'], 'allowed_users':[], 'all_users':True}).status_code, 400)
        # A corrupted/malicious marker on an external definition cannot grant access either.
        app.allowed_users = [ALL_USERS]; app.enabled = True; db.session.commit()
        self.assertEqual(len(self.client.get('/api/plugins/apps', headers=self.headers['employee']).json), 3)

    def test_bundled_manifest_ids_are_reserved_and_platform_gate_applies(self):
        manifest = copy.deepcopy(BUNDLED['zencrm-work-summary']['manifest'])
        self.assertEqual(self.post('/apps', manifest).status_code, 409)
        seed_bundled()
        self.assertEqual(self.client.put('/api/plugins/apps/zencrm-work-summary/manifest', json=manifest, headers=self.headers['admin']).status_code, 409)
        self.app.config['PLUGINS_ENABLED'] = False
        self.assertEqual(self.client.get('/api/plugins/store', headers=self.headers['employee']).status_code, 503)

    def test_named_views_are_authorized_per_user_and_removed_on_revoke(self):
        seed_bundled()
        path = '/api/plugins/views'
        self.assertEqual(self.client.get(path).status_code, 401)
        self.assertEqual(self.client.get(path, headers=self.headers['employee']).json, [])
        app = db.session.get(PluginApp, 'zencrm-work-summary')
        self.post('/apps/'+app.id+'/consent', {'revision':app.revision, 'scopes':['reports.read']}, 'employee')
        views = self.client.get(path, headers=self.headers['employee']).json
        self.assertEqual(len(views), 1)
        self.assertEqual(views[0]['id'], 'plugin/zencrm-work-summary/main')
        self.assertEqual(views[0]['placement_id'], 'main')
        self.assertNotIn('configuration', views[0])
        self.assertNotIn('allowed_users', views[0])
        self.assertEqual(self.client.get(path, headers=self.headers['other']).json, [])
        self.client.delete('/api/plugins/apps/'+app.id+'/consent', headers=self.headers['employee'])
        self.assertEqual(self.client.get(path, headers=self.headers['employee']).json, [])
        self.app.config['PLUGINS_ENABLED'] = False
        self.assertEqual(self.client.get(path, headers=self.headers['employee']).status_code, 503)

    def test_multiple_views_respect_approved_and_consented_scopes(self):
        manifest = json.loads((ROOT/'plugins/examples/reports/manifest.json').read_text(encoding='utf-8'))
        manifest['scopes'] = ['reports.read', 'tasks.read']
        manifest['placements'].append({'id':'tasks', 'slot':'app.page', 'label':'Tasks', 'operation':'tasks.list'})
        manifest['views'].append({'id':'tasks', 'label':'Tasks', 'placement':'tasks'})
        app_id, _ = self.install(manifest)
        app = db.session.get(PluginApp, app_id)
        self.post('/apps/'+app_id+'/consent', {'revision':app.revision, 'scopes':['reports.read']}, 'employee')
        views = self.client.get('/api/plugins/views', headers=self.headers['employee']).json
        self.assertEqual([view['view_id'] for view in views], ['summary'])
        self.assertEqual(self.post('/apps/'+app_id+'/invoke', {'operation':'tasks.list'}, 'employee').status_code, 403)
        self.post('/apps/'+app_id+'/disable', {'revision':app.revision})
        self.assertEqual(self.client.get('/api/plugins/views', headers=self.headers['employee']).json, [])

    def test_named_views_reject_invalid_routes_references_and_executable_content(self):
        manifest = self.remote()
        for invalid in [None, {}, [{'id':'../../settings', 'label':'Bad', 'placement':'application'}],
                        [{'id':'settings', 'label':'Bad', 'placement':'client-panel'}],
                        [{'id':'settings', 'label':'Bad', 'placement':'missing'}],
                        [{'id':'settings', 'label':'Bad', 'placement':'application', 'html':'<script>'}],
                        [{'id':'a', 'label':'One', 'placement':'application'}, {'id':'a', 'label':'Two', 'placement':'application'}],
                        [{'id':'a', 'label':'', 'placement':'application'}]]:
            with self.subTest(invalid=invalid):
                self.assertEqual(self.post('/apps', {**manifest, 'views':invalid}).status_code, 400)
        app_id, _ = self.install(manifest)
        self.assertEqual(self.client.get('/api/plugins/views', headers=self.headers['employee']).json[0]['id'], 'plugin/'+app_id+'/tools')

    def test_admin_can_enable_platform_without_server_restart(self):
        self.app.config['PLUGINS_ENABLED'] = False
        for method in ('get', 'put'):
            call = getattr(self.client, method)
            params = {'json': {'enabled': True}} if method == 'put' else {}
            self.assertEqual(call('/api/plugins/settings', **params).status_code, 401)
            self.assertEqual(call('/api/plugins/settings', headers=self.headers['employee'], **params).status_code, 403)
        result = self.client.put('/api/plugins/settings', json={'enabled': True}, headers=self.headers['admin'])
        self.assertEqual(result.status_code, 200, result.json)
        self.assertTrue(result.json['enabled'])
        self.assertEqual(Setting.get_value('plugins_enabled'), 'true')
        self.assertTrue(self.client.get('/api/plugins/status', headers=self.headers['employee']).json['enabled'])
        # Removing the ORM session simulates the next request/another process reading the setting.
        db.session.remove()
        self.assertTrue(self.client.get('/api/plugins/status', headers=self.headers['admin']).json['enabled'])
        result = self.client.put('/api/plugins/settings', json={'enabled': False}, headers=self.headers['admin'])
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.get('/api/plugins/catalog', headers=self.headers['admin']).status_code, 503)

    def test_server_veto_and_strict_platform_toggle_payload(self):
        self.app.config['PLUGINS_LOCKED'] = True
        Setting.set_value('plugins_enabled', 'true'); db.session.commit()
        self.assertFalse(self.client.get('/api/plugins/status', headers=self.headers['admin']).json['enabled'])
        self.assertTrue(self.client.get('/api/plugins/settings', headers=self.headers['admin']).json['server_locked'])
        self.assertEqual(self.client.put('/api/plugins/settings', json={'enabled':True}, headers=self.headers['admin']).status_code, 409)
        self.assertFalse(self.client.get('/api/plugins/status', headers=self.headers['admin']).json['enabled'])
        for payload in ({'enabled':'true'}, {'enabled':1}, {}, {'enabled':False,'scope':'all'}):
            self.assertEqual(self.client.put('/api/plugins/settings', json=payload, headers=self.headers['admin']).status_code, 400)

    def test_database_switch_stops_api_and_worker_and_can_resume(self):
        app_id, _ = self.install(); token = self.access(app_id); self.subscribe(token)
        emit_client_event('client.updated.v1',self.own.id); db.session.commit()
        result = self.client.put('/api/plugins/settings', json={'enabled':False}, headers=self.headers['admin'])
        self.assertEqual(result.status_code,200)
        self.assertEqual(self.call(token,'clients.list').status_code,503)
        with patch('app.plugins.worker.send_event') as send:
            self.assertEqual(run_once(),0); send.assert_not_called()
        emit_client_event('client.updated.v1',self.own.id); db.session.commit()
        self.assertEqual(PluginEvent.query.count(),1)
        self.client.put('/api/plugins/settings', json={'enabled':True}, headers=self.headers['admin'])
        self.assertEqual(self.call(token,'clients.list').status_code,200)
        with patch('app.plugins.worker.send_event',return_value=204) as send:
            self.assertEqual(run_once(),1); send.assert_called_once()

    def test_unrelated_general_settings_save_preserves_platform_state(self):
        self.client.put('/api/plugins/settings',json={'enabled':True},headers=self.headers['admin'])
        for path in ('/api/settings', '/api/settings/full', '/api/settings/ui', '/api/settings/public'):
            result = self.client.get(path,headers=self.headers['admin'])
            self.assertNotIn('plugins_enabled',str(result.json))
        result = self.client.put('/api/settings',json={'brand_name':'New brand','plugins_enabled':'false'},headers=self.headers['admin'])
        self.assertEqual(result.status_code,200,result.json)
        self.assertEqual(Setting.get_value('plugins_enabled'),'true')

    def test_admin_installation_and_explicit_consent(self):
        manifest = self.remote()
        self.assertEqual(self.post('/apps', manifest, 'employee').status_code, 403)
        app = self.post('/apps', manifest).json
        self.assertEqual(self.post('/apps/'+app['id']+'/enable', {'revision':app['revision']}).status_code, 409)
        installed = self.post('/apps/'+app['id']+'/install', {'revision':app['revision'], 'scopes':['clients.read'],
            'allowed_users':[self.users['employee'].id]}).json
        enabled = self.post('/apps/'+app['id']+'/enable', {'revision':installed['revision']}).json
        self.assertEqual(self.post('/apps/'+app['id']+'/personal-token', {}, 'employee').status_code, 403)
        self.assertEqual(self.post('/apps/'+app['id']+'/consent', {'revision':enabled['revision'],'scopes':['storage']}, 'employee').status_code, 400)
        self.assertEqual(self.post('/apps/'+app['id']+'/consent', {'revision':enabled['revision'],'scopes':['clients.read']}, 'other').status_code, 403)
        self.assertEqual(self.post('/apps/'+app['id']+'/consent', {'revision':enabled['revision'],'scopes':['clients.read']}, 'employee').status_code, 200)

    def test_tokens_do_not_cross_authentication_boundaries(self):
        app_id, _ = self.install(); token = self.access(app_id)
        for path in ('/api/clients', '/api/auth/me', '/api/plugins/catalog'):
            self.assertIn(self.client.get(path, headers={'Authorization':'Bearer '+token}).status_code, (401,422))
        crm_token = self.headers['employee']['Authorization'][7:]
        self.assertEqual(self.call(crm_token, 'clients.list').status_code, 401)
        self.assertEqual(self.call(token, '/users').status_code, 400)
        self.assertEqual(self.call(token, ['clients.list']).status_code, 400)
        self.assertEqual(self.call(token, 'reports.summary').status_code, 403)
        self.assertEqual(self.client.post('/api/plugin-api/v1/call?access_token='+token, json={'operation':'clients.list'}).status_code, 401)
        self.assertEqual(PluginToken.query.first().access_hash, digest(token))
        response = self.call(token, 'clients.list')
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertNotIn(token, str(PluginToken.query.first().__dict__))

    def test_record_visibility_fields_and_live_reassignment(self):
        app_id, _ = self.install(); token = self.access(app_id)
        listed = self.call(token, 'clients.list').json
        self.assertEqual([item['id'] for item in listed['items']], [self.own.id])
        self.assertNotIn('notes', listed['items'][0])
        for row in (self.other, self.archived):
            self.assertEqual(self.call(token, 'clients.get', {'id':row.id}).status_code, 404)
        self.own.assignee_id = self.users['other'].id; db.session.commit()
        self.assertEqual(self.call(token, 'clients.get', {'id':self.own.id}).status_code, 404)
        self.assertEqual(self.call(token, 'clients.list', {'limit':101}).status_code, 400)

    def test_write_needs_scope_domain_permission_and_allowed_fields(self):
        manifest = self.remote(); manifest['scopes'].append('clients.write')
        app_id, _ = self.install(manifest); token = self.access(app_id)
        self.assertEqual(self.call(token, 'clients.update', {'id':self.other.id,'fields':{'name':'Changed'}}).status_code,404)
        self.assertEqual(self.call(token, 'clients.update', {'id':self.own.id,'fields':{'assignee_id':1}}).status_code,400)
        db.session.add(PermissionRule(role_key='employee',permission='clients.edit',allowed=False)); db.session.commit()
        self.assertEqual(self.call(token, 'clients.update', {'id':self.own.id,'fields':{'name':'Changed'}}).status_code,403)
        PermissionRule.query.delete(); db.session.commit()
        self.assertEqual(self.call(token, 'clients.update', {'id':self.own.id,'fields':{'name':'Changed'}}).status_code,200)
        self.assertEqual(db.session.get(Client,self.own.id).name,'Changed')

    def test_storage_isolated_optimistic_and_bounded(self):
        app_id, _ = self.install(); token = self.access(app_id)
        params = {'key':'x', 'revision':0,'value':{'private':'value'}}
        saved = self.call(token, 'storage.put', params)
        self.assertEqual(saved.status_code,200)
        revision = saved.json['revision']
        self.assertEqual(self.call(token, 'storage.put', params).status_code,409)
        other = self.access(app_id,'other')
        self.assertEqual(self.call(other, 'storage.get', {'key':'x'}).json['revision'],0)
        self.assertEqual(self.call(token, 'storage.put', {'key':'huge','revision':0,'value':'x'*9000}).status_code,400)
        grant = PluginGrant.query.filter_by(app_id=app_id,user_id=self.users['employee'].id).one()
        db.session.add_all([PluginStorage(grant_id=grant.id,key=str(i),value=i) for i in range(99)]); db.session.commit()
        self.assertEqual(self.call(token, 'storage.put', {'key':'full','revision':0,'value':1}).status_code,409)
        self.assertEqual(self.call(token, 'storage.delete', {'key':'x','revision':revision}).status_code,200)
        self.assertEqual(self.call(token, 'storage.put', {'key':'x','revision':0,'value':'new'}).status_code,200)
        self.assertEqual(self.call(token, 'storage.put', {'key':'x','revision':revision,'value':'old'}).status_code,409)
        self.assertEqual(self.call(token, 'storage.delete', {'key':'x','revision':10**30}).status_code,400)

    def test_reports_use_user_visibility_and_count_in_progress(self):
        manifest = json.loads((ROOT/'plugins/examples/reports/manifest.json').read_text(encoding='utf-8'))
        app_id, _ = self.install(manifest)
        result = self.call(self.access(app_id), 'reports.summary').json
        self.assertEqual(result['clients'],1); self.assertEqual(result['open_tasks'],1)
        self.assertEqual(self.call(self.access(app_id,'admin'),'reports.summary').json['clients'],2)

    def test_configuration_is_scoped_to_the_application(self):
        app_id, _ = self.install()
        app = db.session.get(PluginApp, app_id); app.configuration = {'label': 'configured'}; db.session.commit()
        self.assertEqual(self.call(self.access(app_id), 'app.config.get').json, {'configuration': {'label': 'configured'}})
        manifest = self.remote('another-demo'); manifest['scopes'].remove('app.config')
        other_id, _ = self.install(manifest)
        self.assertEqual(self.call(self.access(other_id), 'app.config.get').status_code, 403)

    def test_pkce_redirect_and_single_use(self):
        app_id, secrets = self.install(); payload = self.oauth(app_id,secrets['client_secret'])
        for field,value in [('code_verifier','b'*64),('redirect_uri','https://evil.example/callback'),('client_secret','incorrect')]:
            incorrect = {**payload,field:value}
            self.assertIn(self.client.post('/api/plugin-api/v1/oauth/token',json=incorrect).status_code,(400,401))
        response = self.client.post('/api/plugin-api/v1/oauth/token',json=payload)
        self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(self.client.post('/api/plugin-api/v1/oauth/token',json=payload).status_code,400)
        self.assertEqual(self.call(response.json['access_token'],'clients.list').status_code,200)
        code = PluginCode.query.one(); self.assertNotEqual(code.code_hash,payload['code'])

    def test_refresh_rotation_and_reuse_revokes_family(self):
        app_id, secrets = self.install()
        original = self.client.post('/api/plugin-api/v1/oauth/token',json=self.oauth(app_id,secrets['client_secret'])).json
        payload = {'grant_type':'refresh_token','client_id':app_id,'client_secret':secrets['client_secret'],'refresh_token':original['refresh_token']}
        refreshed = self.client.post('/api/plugin-api/v1/oauth/token',json=payload)
        self.assertEqual(refreshed.status_code,200,refreshed.json)
        self.assertEqual(self.call(original['access_token'],'clients.list').status_code,401)
        self.assertEqual(self.client.post('/api/plugin-api/v1/oauth/token',json=payload).status_code,400)
        self.assertEqual(self.call(refreshed.json['access_token'],'clients.list').status_code,401)
        self.assertTrue(all(row.revoked for row in PluginToken.query.all()))

    def test_password_deactivation_expiry_and_revoke(self):
        app_id, _ = self.install(); token = self.access(app_id)
        self.users['employee'].set_password('new-password'); db.session.commit()
        self.assertEqual(self.call(token,'clients.list').status_code,401)
        self.headers['employee'] = {'Authorization': 'Bearer ' + create_access_token(identity=str(self.users['employee'].id))}
        token = self.access(app_id)
        PluginToken.query.filter_by(access_hash=digest(token)).update({'expires_at':datetime.utcnow()-timedelta(seconds=1)}); db.session.commit()
        self.assertEqual(self.call(token,'clients.list').status_code,401)
        token = self.access(app_id)
        self.users['employee'].is_active=False; db.session.commit()
        self.assertEqual(self.call(token,'clients.list').status_code,403)
        self.users['employee'].is_active=True; db.session.commit()
        response=self.client.delete('/api/plugins/apps/'+app_id+'/tokens',headers=self.headers['employee'])
        self.assertEqual(response.status_code,200)
        self.assertEqual(self.call(token,'clients.list').status_code,401)

    def test_disable_requires_reconsent_and_revision_conflicts(self):
        app_id, _ = self.install(); token = self.access(app_id)
        app = db.session.get(PluginApp,app_id); revision=app.revision
        self.assertEqual(self.post('/apps/'+app_id+'/disable',{'revision':revision-1}).status_code,409)
        self.assertEqual(self.post('/apps/'+app_id+'/disable',{'revision':revision}).status_code,200)
        self.assertEqual(self.call(token,'clients.list').status_code,401)
        app=db.session.get(PluginApp,app_id)
        self.post('/apps/'+app_id+'/enable',{'revision':app.revision})
        self.assertEqual(self.call(token,'clients.list').status_code,401)
        self.assertEqual(self.post('/apps/'+app_id+'/personal-token',{},'employee').status_code,403)

    def test_concurrent_manifest_mutation_uses_optimistic_lock(self):
        app_id, _ = self.install()
        with Session(db.engine) as first, Session(db.engine) as second:
            a=first.get(PluginApp,app_id); b=second.get(PluginApp,app_id)
            a.revision+=1; first.commit()
            b.revision+=1
            with self.assertRaises(StaleDataError): second.commit()

    def subscribe(self, token):
        response=self.client.post('/api/plugin-api/v1/subscriptions',json={'event':'client.updated.v1'},headers={'Authorization':'Bearer '+token})
        self.assertEqual(response.status_code,200,response.json)

    def test_events_are_transactional_private_and_deduplicated(self):
        app_id, _ = self.install(); token=self.access(app_id); self.subscribe(token)
        emit_client_event('client.updated.v1',self.own.id); db.session.rollback()
        self.assertEqual(PluginEvent.query.count(),0)
        emit_client_event('client.updated.v1',self.other.id); db.session.commit()
        self.assertEqual(PluginEvent.query.count(),0)
        with patch('app.plugins.worker.send_event',return_value=204) as send:
            emit_client_event('client.updated.v1',self.own.id); db.session.commit()
            self.assertEqual(run_once(),1); self.assertEqual(run_once(),0)
            body=json.loads(send.call_args.args[1])
            self.assertNotIn('name',body); self.assertNotIn('email',body)
            self.assertEqual(body['entity_id'],self.own.id)
        self.assertEqual(PluginDelivery.query.one().status,'delivered')

    def test_client_core_write_and_archive_emit_committed_events(self):
        app_id, _ = self.install(); token = self.access(app_id)
        for kind in ('client.created.v1', 'client.updated.v1', 'client.archived.v1'):
            response = self.client.post('/api/plugin-api/v1/subscriptions', json={'event':kind}, headers={'Authorization':'Bearer '+token})
            self.assertEqual(response.status_code, 200)
        created = self.client.post('/api/clients', json={'name':'New subscriber client','assignee_id':self.users['employee'].id}, headers=self.headers['employee'])
        self.assertEqual(created.status_code, 201, created.json)
        client_id = created.json['id']
        updated = self.client.put('/api/clients/'+str(client_id),json={'name':'Updated subscriber client'}, headers=self.headers['employee'])
        self.assertEqual(updated.status_code,200,updated.json)
        archived = self.client.delete('/api/clients/'+str(client_id),headers=self.headers['employee'])
        self.assertEqual(archived.status_code,200,archived.json)
        self.assertEqual({event.kind for event in PluginEvent.query.all()}, {'client.created.v1','client.updated.v1','client.archived.v1'})
        with patch('app.plugins.worker.send_event', return_value=204) as send:
            run_once()
            # Current state is archived: only its archival notification may leave CRM.
            self.assertEqual(send.call_count,1)
            self.assertEqual(json.loads(send.call_args.args[1])['event'],'client.archived.v1')

    def test_worker_preserves_live_lease_and_recovers_expired_claim(self):
        app_id, _ = self.install(); self.subscribe(self.access(app_id))
        emit_client_event('client.updated.v1',self.own.id); db.session.commit()
        delivery=PluginDelivery.query.one();delivery.status='sending';delivery.lease_token='old-worker'
        delivery.lease_until=datetime.utcnow()+timedelta(seconds=30);db.session.commit()
        with patch('app.plugins.worker.send_event',return_value=204) as send:
            self.assertEqual(run_once(),0);send.assert_not_called()
            delivery.lease_until=datetime.utcnow()-timedelta(seconds=1);db.session.commit()
            self.assertEqual(run_once(),1);send.assert_called_once()
        self.assertEqual(PluginDelivery.query.one().status,'delivered')

    def test_queue_pressure_preserves_crm_record_and_does_not_add_events(self):
        app_id, _ = self.install(); self.subscribe(self.access(app_id))
        with patch('app.plugins.events.PluginDelivery.query') as queue:
            queue.filter.return_value.count.return_value=10000
            emit_client_event('client.updated.v1',self.own.id)
            self.own.name='Still saved';db.session.commit()
        self.assertEqual(PluginEvent.query.count(),0)
        self.assertEqual(db.session.get(Client,self.own.id).name,'Still saved')

    def test_worker_rechecks_visibility_and_retries_without_redirects(self):
        app_id, _ = self.install(); self.subscribe(self.access(app_id))
        emit_client_event('client.updated.v1',self.own.id); db.session.commit()
        with patch('app.plugins.worker.send_event',return_value=503) as send:
            run_once(); delivery=PluginDelivery.query.one()
            self.assertEqual(delivery.status,'pending'); self.assertEqual(delivery.attempts,1)
            delivery.next_attempt_at=datetime.utcnow()-timedelta(seconds=1); db.session.commit()
            send.return_value=302; run_once()
            self.assertEqual(PluginDelivery.query.one().status,'failed')
        emit_client_event('client.updated.v1',self.own.id); db.session.commit()
        self.own.assignee_id=self.users['other'].id; db.session.commit()
        with patch('app.plugins.worker.send_event') as send:
            run_once(); send.assert_not_called()
        self.assertEqual(PluginDelivery.query.filter_by(status='cancelled').count(),1)

    def test_disable_cancels_pending_events_and_global_switch_stops_worker(self):
        app_id, _ = self.install(); self.subscribe(self.access(app_id))
        emit_client_event('client.updated.v1',self.own.id); db.session.commit()
        self.app.config['PLUGINS_ENABLED']=False
        with patch('app.plugins.worker.send_event') as send:
            self.assertEqual(run_once(),0); send.assert_not_called()
        self.app.config['PLUGINS_ENABLED']=True
        app=db.session.get(PluginApp,app_id); self.post('/apps/'+app_id+'/disable',{'revision':app.revision})
        self.assertEqual(PluginDelivery.query.one().status,'cancelled')

    def test_manifest_rejects_code_unbounded_unknown_and_malformed_values(self):
        manifest=self.remote()
        changes=[{'module':'os'}, {'manifest_version':True}, {'api_version':2}, {'scopes':['admin']},
            {'redirect_uris':[{}]}, {'redirect_uris':['https://crm.example.com/oauth']}, {'redirect_uris':['https://crm.example.com:443/oauth']},
            {'event_url':'https://user:secret@example.com/'}, {'event_url':'http://example.com/'},
            {'event_url':'https://example.com:8443/'}, {'event_url':'https://example.com/?token=secret'},
            {'placements':[{'id':'ui','slot':[],'label':'test','url':'https://example.com/'}]}]
        for change in changes:
            with self.subTest(change=change):
                with self.assertRaises(ValueError): validate_manifest({**manifest,**change})
        self.assertEqual(self.post('/apps',{**manifest,'description':'x'*40000}).status_code,400)
        self.assertEqual(self.client.post('/api/plugin-api/v1/oauth/token',json={'client_id':[]}).status_code,400)

    def test_rate_limit_is_per_grant_and_persisted(self):
        from app.models.auth_security import AuthRateLimit
        import time
        app_id, _=self.install(); token=self.access(app_id)
        grant=PluginGrant.query.filter_by(app_id=app_id,user_id=self.users['employee'].id).one()
        bucket=int(time.time())//60; key=hashlib.sha256(f'plugin-api:{grant.id}:{bucket}'.encode()).hexdigest()
        db.session.add(AuthRateLimit(key=key,count=120,expires_at=(bucket+1)*60)); db.session.commit()
        self.assertEqual(self.call(token,'clients.list').status_code,429)
        self.assertEqual(self.call(self.access(app_id,'other'),'clients.list').status_code,200)


class PluginTransportTest(unittest.TestCase):
    def test_header_watchdog_interrupts_socket_and_is_always_cancelled(self):
        with patch('app.plugins.transport.PublicHTTPS') as https, patch('app.plugins.transport.threading.Timer') as timer:
            https.return_value.getresponse.return_value.status = 204
            def inspect_timer():
                timer.call_args.args[1]()
                return https.return_value.getresponse.return_value
            https.return_value.getresponse.side_effect = inspect_timer
            send_event('https://example.com/events', b'{}', 'id', 'secret')
            self.assertEqual(timer.call_args.args[0], 10)
            https.return_value.sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
            timer.return_value.cancel.assert_called_once()

    def test_public_https_pin_and_tls_hostname(self):
        conn=PublicHTTPS('apps.example.com',443,timeout=5); conn._context=Mock()
        with patch('app.plugins.transport.public_socket') as connect:
            conn.connect()
            conn._context.wrap_socket.assert_called_once_with(connect.return_value,server_hostname='apps.example.com')
        conn.close()

    def test_private_mixed_dns_is_rejected_before_any_socket(self):
        addresses=[(socket.AF_INET,socket.SOCK_STREAM,6,'',(ip,443)) for ip in ('8.8.8.8','127.0.0.1')]
        with patch('socket.getaddrinfo',return_value=addresses), patch('socket.socket') as sock:
            with self.assertRaises(ValueError): PublicHTTPS('apps.example.com',443,timeout=5).connect()
            sock.assert_not_called()

    def test_signature_raw_body_no_redirect_no_response_read(self):
        with patch('app.plugins.transport.PublicHTTPS') as https, patch('app.plugins.transport.time.time',return_value=12345):
            https.return_value.getresponse.return_value.status=302
            self.assertEqual(send_event('https://example.com/events',b'{"a":1}','delivery','secret'),302)
            args=https.return_value.request.call_args
            expected=hmac.new(b'secret',b'12345.{"a":1}',hashlib.sha256).hexdigest()
            self.assertEqual(args.kwargs['headers']['X-ZenCRM-Signature'],'sha256='+expected)
            https.return_value.getresponse.return_value.read.assert_not_called()
            https.return_value.close.assert_called_once()
