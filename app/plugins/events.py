"""Transactional client events. Only explicitly subscribed, visible records are queued."""
import uuid
from datetime import datetime
from flask import current_app
from ..extensions import db
from ..models.user import User
from .manifest import EVENTS
from .models import PluginApp, PluginGrant, PluginSubscription, PluginEvent, PluginDelivery
from .policy import audience


def emit_client_event(kind, entity_id):
    if not current_app.config.get('PLUGINS_ENABLED', False):
        return
    if kind not in EVENTS:
        raise ValueError('Nieobsługiwane zdarzenie aplikacji.')
    from ..models.client import Client
    client = db.session.get(Client, entity_id)
    if not client or (kind != 'client.archived.v1' and client.deleted_at is not None):
        return
    subscriptions = db.session.query(PluginSubscription, PluginGrant, PluginApp, User).join(
        PluginGrant, PluginGrant.id == PluginSubscription.grant_id).join(
        PluginApp, PluginApp.id == PluginGrant.app_id).join(User, User.id == PluginGrant.user_id).filter(
        PluginSubscription.kind == kind, PluginGrant.active.is_(True),
        PluginApp.enabled.is_(True), User.is_active.is_(True)).all()
    recipients = []
    for subscription, grant, app, user in subscriptions:
        required = {'clients.read', 'events.clients'}
        if not audience(app, user) or not required <= set(grant.scopes) & set(app.approved_scopes) & set(app.manifest['scopes']):
            continue
        # Archived events include only the ID of a record this actor owned before archival.
        visible = user.role == 'admin' or client.assignee_id == user.id
        if visible:
            recipients.append((app, grant))
    if not recipients:
        return
    queued = PluginDelivery.query.filter(PluginDelivery.status.in_(['pending', 'sending'])).count()
    if queued + len(recipients) > 10000:
        # Preserve CRM availability; this exceptional loss is explicit and monitored.
        current_app.logger.error('Plugin delivery queue full; client event not queued')
        return
    event = PluginEvent(id=str(uuid.uuid4()), kind=kind, entity_id=entity_id)
    db.session.add(event)
    db.session.flush()
    for app, grant in recipients:
        db.session.add(PluginDelivery(id=str(uuid.uuid4()), event_id=event.id, grant_id=grant.id,
            app_revision=app.revision, grant_revision=grant.revision, status='pending',
            next_attempt_at=datetime.utcnow()))
    # Caller owns commit/rollback. Never send an HTTP request from this transaction.
