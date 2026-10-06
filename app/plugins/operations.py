"""Versioned, field-limited application API; no URL, SQL or core-handler forwarding."""
import re
import secrets
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from flask import abort
from ..extensions import db
from ..models.client import Client
from ..models.task import Task
from ..utils.permissions import has_permission
from .manifest import OPERATIONS, bounded_json
from .models import PluginStorage
from .policy import principal, require_scope, visible_clients, visible_tasks, audit


def client_data(client):
    return {key: getattr(client, key) for key in ('id', 'name', 'email', 'phone', 'company', 'status')}


def number(value, default=1, maximum=100000):
    value = default if value is None else value
    if type(value) is not int or not 1 <= value <= maximum:
        abort(400)
    return value


def invoke(app, grant, user, operation, params):
    app, grant, user = principal(grant.id)
    if not isinstance(operation, str) or operation not in OPERATIONS or not isinstance(params, dict):
        abort(400)
    bounded_json(params)
    require_scope(app, grant, OPERATIONS[operation])
    if operation == 'app.config.get':
        if params:
            abort(400)
        return {'configuration': app.configuration}
    if operation == 'reports.summary':
        if params:
            abort(400)
        clients = visible_clients(user)
        tasks = visible_tasks(user)
        return {'clients': clients.count(), 'open_tasks': tasks.filter(Task.status != 'done').count(),
                'client_statuses': {status: count for status, count in clients.with_entities(Client.status, func.count(Client.id)).group_by(Client.status).all()}}
    if operation == 'reports.aggregate':
        from .reports import aggregate_report
        return aggregate_report(user, params)
    if operation in ('clients.list', 'tasks.list'):
        if set(params) - {'page', 'limit', 'search'}:
            abort(400)
        page = number(params.get('page'))
        limit = number(params.get('limit'), 25, 100)
        query = visible_clients(user) if operation == 'clients.list' else visible_tasks(user)
        search = params.get('search', '')
        if not isinstance(search, str) or len(search) > 120:
            abort(400)
        model = query.column_descriptions[0]['entity']
        if search:
            field = model.name if operation == 'clients.list' else model.title
            query = query.filter(field.ilike('%' + search.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_') + '%', escape='\\'))
        total = query.count()
        rows = query.order_by(model.id).offset((page - 1) * limit).limit(limit).all()
        items = [client_data(row) if operation == 'clients.list' else
                 {key: getattr(row, key) for key in ('id', 'title', 'status', 'priority')} for row in rows]
        return {'items': items, 'total': total, 'page': page}
    if operation in ('clients.get', 'clients.update'):
        if set(params) - ({'id'} if operation == 'clients.get' else {'id', 'fields'}):
            abort(400)
        client = visible_clients(user).filter(Client.id == number(params.get('id'), None)).first_or_404()
        if operation == 'clients.update':
            if not has_permission(user, 'clients.edit'):
                abort(403)
            fields = params.get('fields')
            allowed = {'name': 200, 'email': 120, 'phone': 20, 'company': 200}
            if not isinstance(fields, dict) or not fields or set(fields) - set(allowed):
                abort(400)
            for key, value in fields.items():
                if value is not None and (not isinstance(value, str) or len(value) > allowed[key] or any(ord(c) < 32 for c in value)):
                    abort(400)
                if key == 'name' and (not value or not value.strip()):
                    abort(400)
            for key, value in fields.items():
                setattr(client, key, value.strip() if isinstance(value, str) else None)
            from .events import emit_client_event
            emit_client_event('client.updated.v1', client.id)
            audit(app.id, user.id, 'clients.update')
            db.session.commit()
        return client_data(client)
    if operation.startswith('storage.'):
        allowed_params = {'key', 'value', 'revision'} if operation == 'storage.put' else {'key', 'revision'}
        if set(params) - allowed_params or not isinstance(params.get('key'), str) or not re.fullmatch(r'[a-zA-Z0-9._-]{1,80}', params['key']):
            abort(400)
        key = params['key']
        row = PluginStorage.query.filter_by(grant_id=grant.id, key=key).first()
        if operation == 'storage.get':
            return {'key': key, 'value': row.value if row else None, 'revision': row.revision if row else 0}
        revision = params.get('revision')
        if type(revision) is not int or not 0 <= revision < 2 ** 53 - 1:
            abort(400)
        next_revision = revision + 1
        if operation == 'storage.delete':
            changed = PluginStorage.query.filter_by(grant_id=grant.id, key=key, revision=revision).delete()
            if not changed:
                abort(409)
        else:
            if 'value' not in params or params['value'] is None:
                abort(400)
            bounded_json(params['value'], 8192)
            if row:
                changed = PluginStorage.query.filter_by(id=row.id, revision=revision).update(
                    {'value': params['value'], 'revision': revision + 1}, synchronize_session=False)
                if not changed:
                    abort(409)
            else:
                if revision != 0:
                    abort(409)
                # Serialize writes to this grant, including the quota check.
                from .models import PluginGrant
                PluginGrant.query.filter_by(id=grant.id).update({'revision': PluginGrant.revision}, synchronize_session=False)
                if PluginStorage.query.filter_by(grant_id=grant.id).count() >= 100:
                    abort(409)
                # Safe JS integer nonce avoids reusing an old CAS version after delete/recreate.
                next_revision = secrets.randbelow(2 ** 52) + 1
                db.session.add(PluginStorage(grant_id=grant.id, key=key, value=params['value'], revision=next_revision))
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            abort(409)
        return {'key': key, 'revision': next_revision}
    abort(400)
