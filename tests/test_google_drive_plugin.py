import unittest
from io import BytesIO
from urllib.parse import urlsplit, parse_qs
from unittest.mock import patch
from tests import test_plugins as fixtures
from app.extensions import db
from app.plugins.bundled import seed_bundled
from app.plugins.models import PluginApp, PluginGrant, PluginStorage
from app.plugins import google_drive as drive


class GoogleDriveTests(unittest.TestCase):
    tearDown = fixtures.PluginTest.tearDown
    post = fixtures.PluginTest.post

    def setUp(self):
        fixtures.PluginTest.setUp(self)
        self.app.config.update(SECRET_KEY='drive-test-encryption-key-at-least-32-bytes',
                               GOOGLE_DRIVE_CLIENT_ID='test.apps.googleusercontent.com',
                               GOOGLE_DRIVE_CLIENT_SECRET='test-secret')
        seed_bundled()
        app = db.session.get(PluginApp, drive.APP_ID)
        result = self.post('/apps/'+app.id+'/consent', {'revision':app.revision, 'scopes':['drive.files']}, 'employee')
        self.assertEqual(result.status_code, 200, result.json)
        self.grant_id = PluginGrant.query.filter_by(app_id=app.id, user_id=self.users['employee'].id).one().id

    def connect(self):
        response = self.post('/google-drive/connect', {}, 'employee')
        self.assertEqual(response.status_code, 200, response.json)
        query = parse_qs(urlsplit(response.json['authorization_url']).query)
        self.assertEqual(query['scope'], [drive.SCOPE])
        self.assertEqual(query['code_challenge_method'], ['S256'])
        return query['state'][0]

    def connected(self):
        state = self.connect()
        with patch.object(drive, 'google_request', return_value={'access_token':'private-access', 'refresh_token':'private-refresh',
                  'expires_in':3600, 'scope':drive.SCOPE, 'token_type':'Bearer'}):
            response = self.client.get(drive.CALLBACK, query_string={'state':state, 'code':'test-code'})
        self.assertEqual(response.status_code, 302)
        return state

    def test_oauth_encrypted_single_use_and_cookie_bound(self):
        state = self.connected()
        row = PluginStorage.query.filter_by(grant_id=self.grant_id, key=drive.CONNECTION).one()
        self.assertNotIn('private-access', str(row.value))
        self.assertNotIn('private-refresh', str(row.value))
        self.assertEqual(self.client.get(drive.CALLBACK, query_string={'state':state, 'code':'replay'}).status_code, 400)
        status = self.client.get('/api/plugins/google-drive/status', headers=self.headers['employee'])
        self.assertTrue(status.json['connected'])
        self.assertNotIn('private-', str(status.json))

    def test_state_mismatch_and_denial_do_not_exchange_tokens(self):
        state = self.connect()
        with patch.object(drive, 'google_request') as provider:
            self.assertEqual(self.client.get(drive.CALLBACK, query_string={'state':'x'*43, 'code':'test'}).status_code, 400)
            response = self.client.get(drive.CALLBACK, query_string={'state':state, 'error':'access_denied'})
            self.assertEqual(response.status_code, 302)
            provider.assert_not_called()
        self.assertFalse(PluginStorage.query.filter_by(grant_id=self.grant_id, key=drive.CONNECTION).count())

    def test_private_files_query_and_safe_provider_links(self):
        self.connected()
        with patch.object(drive, 'google_request', return_value={'files':[{'id':'safe-file', 'name':'Report.csv', 'webViewLink':'https://evil.example'}]}) as provider:
            result = self.client.get('/api/plugins/google-drive/files', query_string={'search':"a'b"}, headers=self.headers['employee'])
        self.assertEqual(result.status_code, 200, result.json)
        self.assertEqual(result.json['files'][0]['url'], 'https://drive.google.com/file/d/safe-file/view')
        self.assertIn(drive.file_tag(self.grant_id), provider.call_args.kwargs['params']['q'])
        self.assertIn("a\\'b", provider.call_args.kwargs['params']['q'])
        self.assertEqual(self.client.get('/api/plugins/google-drive/files', headers=self.headers['other']).status_code, 403)

    def test_upload_creates_folder_and_tagged_file(self):
        self.connected()
        with patch.object(drive, 'google_request', side_effect=[{'files':[]}, {'id':'folder-id'}, {'id':'report-id', 'name':'Report.csv'}]) as provider:
            result = self.client.post('/api/plugins/google-drive/files', data={'file':(BytesIO(b'CSV-content'), 'Report.csv')}, headers=self.headers['employee'])
        self.assertEqual(result.status_code, 201, result.json)
        self.assertIn(b'CSV-content', provider.call_args.kwargs['data'])
        self.assertIn(drive.file_tag(self.grant_id).encode(), provider.call_args.kwargs['data'])
        self.assertEqual(provider.call_args.args[1], drive.UPLOAD)

    def test_disconnect_clears_locally_even_if_provider_unavailable(self):
        from werkzeug.exceptions import ServiceUnavailable
        self.connected()
        with patch.object(drive, 'google_request', side_effect=ServiceUnavailable()):
            result = self.client.delete('/api/plugins/google-drive/connection', headers=self.headers['employee'])
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.json['revoked_at_google'])
        self.assertFalse(PluginStorage.query.filter_by(grant_id=self.grant_id).count())

    def test_configuration_and_platform_required(self):
        self.app.config['GOOGLE_DRIVE_CLIENT_SECRET'] = ''
        self.assertEqual(self.post('/google-drive/connect', {}, 'employee').status_code, 409)
        self.app.config['PLUGINS_ENABLED'] = False
        self.assertEqual(self.client.get('/api/plugins/google-drive/status', headers=self.headers['employee']).status_code, 503)

    def settings(self, user='admin'):
        return self.client.get('/api/plugins/google-drive/settings', headers=self.headers[user])

    def save_settings(self, client_id='panel.apps.googleusercontent.com', secret='panel-private-secret', revision=None):
        revision = revision or self.settings().json['revision']
        return self.client.put('/api/plugins/google-drive/settings', headers=self.headers['admin'],
            json={'client_id':client_id,'client_secret':secret,'revision':revision})

    def test_panel_settings_encrypted_and_hidden_from_other_settings_apis(self):
        from app.models.setting import Setting
        result = self.save_settings()
        self.assertEqual(result.status_code, 200, result.json)
        self.assertEqual(result.json['source'], 'settings')
        self.assertTrue(result.json['secret_set'])
        self.assertNotIn('panel-private-secret', str(result.json))
        row = Setting.query.filter_by(key=drive.OAUTH_SETTING).one()
        self.assertNotIn('panel-private-secret', row.value)
        self.assertTrue(row.value.startswith('fernet:v1:'))
        self.assertEqual(drive.oauth_config()['client_secret'], 'panel-private-secret')
        for path in ['/api/settings', '/api/settings/full', '/api/settings/ui', '/api/settings/public', '/api/plugins/catalog']:
            response = self.client.get(path, headers=self.headers['admin'])
            self.assertEqual(response.status_code, 200, response.json)
            self.assertNotIn('panel-private-secret', str(response.json))
            self.assertNotIn(row.value, str(response.json))
        response = self.client.put('/api/settings', json={drive.OAUTH_SETTING:'plaintext'}, headers=self.headers['admin'])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(drive.oauth_config()['client_secret'], 'panel-private-secret')

    def test_panel_preserves_secret_and_requires_matching_client(self):
        self.assertEqual(self.save_settings().status_code, 200)
        self.assertEqual(self.save_settings(secret='').status_code, 200)
        self.assertEqual(drive.oauth_config()['client_secret'], 'panel-private-secret')
        self.assertEqual(self.save_settings(client_id='new.apps.googleusercontent.com', secret='').status_code, 400)
        self.assertEqual(drive.oauth_config()['client_id'], 'panel.apps.googleusercontent.com')
        self.assertEqual(self.save_settings(client_id='new.apps.googleusercontent.com', secret='new-private-secret').status_code, 200)

    def test_panel_requires_admin_and_prevents_stale_overwrites(self):
        self.assertEqual(self.settings('employee').status_code, 403)
        result = self.client.put('/api/plugins/google-drive/settings', json={}, headers=self.headers['employee'])
        self.assertEqual(result.status_code, 403)
        revision = self.settings().json['revision']
        self.assertEqual(self.save_settings(revision=revision).status_code, 200)
        self.assertEqual(self.save_settings(secret='stale-secret', revision=revision).status_code, 409)
        self.assertEqual(drive.oauth_config()['client_secret'], 'panel-private-secret')

    def test_panel_change_invalidates_existing_connections(self):
        self.connected()
        self.assertEqual(self.save_settings().status_code, 200)
        response = self.client.get('/api/plugins/google-drive/status', headers=self.headers['employee'])
        self.assertFalse(response.json['connected'])
        self.assertEqual(self.connect() and drive.oauth_config()['client_id'], 'panel.apps.googleusercontent.com')

    def test_panel_validates_credentials_and_encryption(self):
        for client_id, secret in [('bad-id','secret'), ('valid.apps.googleusercontent.com','a b'), ('valid.apps.googleusercontent.com','x'*4097)]:
            self.assertEqual(self.save_settings(client_id, secret).status_code, 400)
        self.app.config['SECRET_KEY'] = 'short'
        self.assertEqual(self.save_settings().status_code, 409)
