"""Standalone receiver example, OUTSIDE the CRM process.

Use HTTPS reverse proxy, a stable signing key and persistent app-owned storage.
ZENCRM_WEBHOOK_KEY=... ZENCRM_APP_ID=client-tools-demo flask --app webhook run
OAuth/provider secrets and a Google SDK belong to this external service.
"""
import hashlib
import hmac
import os
import sqlite3
import time
from flask import Flask, abort, request

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 8192
KEY = os.environ['ZENCRM_WEBHOOK_KEY'].encode()
APP_ID = os.environ.get('ZENCRM_APP_ID', 'client-tools-demo')
DATABASE = os.environ.get('APP_EVENT_DATABASE', 'app-events.sqlite')


@app.post('/events')
def events():
    raw = request.get_data()
    timestamp = request.headers.get('X-ZenCRM-Timestamp', '')
    if not timestamp.isdigit() or len(timestamp) > 12 or abs(time.time() - int(timestamp)) > 300:
        abort(401)
    expected = 'sha256=' + hmac.new(KEY, timestamp.encode() + b'.' + raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, request.headers.get('X-ZenCRM-Signature', '')):
        abort(401)
    event = request.get_json()
    if not isinstance(event, dict) or event.get('app_id') != APP_ID or event.get('delivery_id') != request.headers.get('X-ZenCRM-Delivery'):
        abort(400)
    # Transactional deduplication: retries must not perform an action twice.
    with sqlite3.connect(DATABASE) as connection:
        connection.execute('CREATE TABLE IF NOT EXISTS events (id TEXT PRIMARY KEY, payload BLOB NOT NULL)')
        connection.execute('INSERT OR IGNORE INTO events (id, payload) VALUES (?, ?)', (event['delivery_id'], raw))
        # Process persisted events through a separate application worker.
    return '', 204
