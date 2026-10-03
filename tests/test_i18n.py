"""Localization coverage and preservation of user-authored content."""
import ast
import json
import re
import subprocess
import unittest
from html.parser import HTMLParser
from pathlib import Path

from flask import Flask, abort, jsonify
from app.utils.i18n import init_i18n, t, default_email, activity_text
from app.models.email_template import DEFAULT_TEMPLATES
from tools.audit_i18n import ROOT, catalog, calls, backend_messages


class CatalogTests(unittest.TestCase):
    def test_used_keys_exist_in_both_languages(self):
        pl, en = catalog('pl'), catalog('en')
        self.assertEqual(pl.keys(), en.keys())
        missing = [(p, n, k) for p, n, k in [*calls(), *backend_messages()] if k not in pl or k not in en]
        self.assertEqual(missing, [])
        for key in pl:
            self.assertTrue(en[key].strip(), key)
            self.assertEqual(sorted(re.findall(r'\{\w+\}', pl[key])), sorted(re.findall(r'\{\w+\}', en[key])), key)

    def test_all_default_email_copy_has_catalog_entries(self):
        en = catalog('en')
        for row in DEFAULT_TEMPLATES:
            for key in [row['name'], row['subject'], *re.findall(r'>([^<>]+)<', row['body_html'])]:
                key = key.strip()
                if re.search('[A-Za-ząćęłńóśźż]', re.sub(r'\{\{.*?\}\}', '', key)):
                    self.assertTrue(key in en, key)

    def test_frontend_scripts_and_template_expressions_compile(self):
        payload = []
        for path in (ROOT / 'frontend/js').rglob('*.js'):
            payload.append([str(path), 'script', path.read_text(encoding='utf-8')])
        payload.append(['sw.js', 'script', (ROOT / 'frontend/sw.js').read_text(encoding='utf-8')])

        class Expressions(HTMLParser):
            def handle_starttag(self, tag, attrs):
                for name, value in attrs:
                    if value and (name.startswith(':') or name in ('x-text', 'x-html', 'x-show', 'x-if', 'x-data')):
                        payload.append([f'{path}:{self.getpos()[0]}:{name}', 'expression', value])
                    elif value and (name.startswith('@') or name == 'x-init'):
                        payload.append([f'{path}:{self.getpos()[0]}:{name}', 'statement', value])

        for path in [*(ROOT / 'frontend/views').glob('*.html'), ROOT / 'frontend/helpdesk.html', ROOT / 'frontend/portal.html', ROOT / 'frontend/workspace.html']:
            source = path.read_text(encoding='utf-8')
            Expressions().feed(source)
            for script in re.findall(r'<script>([\s\S]*?)</script>', source):
                payload.append([str(path), 'script', script])
            self.assertNotRegex(source, r'<option[^>]*>\s*<span')
            self.assertNotIn('<<span', source)
        checker = """
const fs = require('fs'), vm = require('vm');
const AsyncFunction = Object.getPrototypeOf(async function(){}).constructor;
for (const [file, kind, code] of JSON.parse(fs.readFileSync(0, 'utf8'))) {
  try {
    if (kind === 'script') new vm.Script(code, {filename:file});
    else if (kind === 'expression') new Function('return (' + code + ')');
    else new AsyncFunction(code);
  } catch (error) { console.error(file, error.message); process.exitCode = 1; }
}
"""
        result = subprocess.run(['node', '-e', checker], input=json.dumps(payload), text=True, encoding='utf-8', capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        init_i18n(self.app)

        @self.app.route('/api/message')
        def message():
            return jsonify(error='Brak dostępu', title='Brak dostępu', records=[{'message': 'Brak dostępu'}])

        @self.app.route('/api/missing')
        def missing():
            abort(404)

        @self.app.route('/api/sms-record')
        def sms_record():
            return jsonify(id=7, message='Brak dostępu', phone_number='123')

        @self.app.route('/api/success')
        def success():
            return jsonify(ok=True, message='Wysłano pomyślnie')

    def test_api_translates_only_system_message_fields(self):
        client = self.app.test_client()
        response = client.get('/api/message', headers={'Accept-Language': 'en-GB,en;q=0.9'})
        self.assertEqual(response.json['error'], 'Access denied')
        self.assertEqual(response.json['title'], 'Brak dostępu')
        self.assertEqual(response.json['records'][0]['message'], 'Brak dostępu')
        self.assertIn('Accept-Language', response.headers['Vary'])
        self.assertEqual(client.get('/api/message').json['error'], 'Brak dostępu')
        self.assertEqual(client.get('/api/missing', headers={'Accept-Language': 'en'}).json['error'], 'Resource not found.')
        self.assertEqual(client.get('/api/sms-record', headers={'Accept-Language': 'en'}).json['message'], 'Brak dostępu')
        self.assertEqual(client.get('/api/success', headers={'Accept-Language': 'en'}).json['message'], 'Sent successfully')

    def test_parameter_values_are_not_retranslated_or_replaced(self):
        self.assertEqual(t('Utworzono klienta: {name}', {'name': 'Łódź {other}'}, locale='en'), 'Client created: Łódź {other}')

    def test_default_email_is_translated_but_custom_template_is_untouched(self):
        with self.app.test_request_context(headers={'Accept-Language': 'en'}):
            row = DEFAULT_TEMPLATES[0]
            subject = default_email(row['key'], 'subject', row['subject'])
            body = default_email(row['key'], 'body_html', row['body_html'])
            self.assertIn('Ticket confirmation', subject)
            self.assertIn('{{ticket_title}}', subject)
            self.assertIn('Your ticket has been registered', body)
            self.assertIn('{{client_name}}', body)
            self.assertEqual(default_email(row['key'], 'body_html', '<p>Moja własna treść</p>'), '<p>Moja własna treść</p>')

    def test_activity_preserves_names_and_note_content(self):
        with self.app.test_request_context(headers={'Accept-Language': 'en'}):
            self.assertEqual(activity_text('Utworzono klienta: Łódź', 'created'), 'Client created: Łódź')
            self.assertEqual(activity_text('Notatka: Dzień dobry', 'comment'), 'Note: Dzień dobry')
            self.assertEqual(activity_text('Własna treść', 'comment'), 'Własna treść')


if __name__ == '__main__':
    unittest.main()
