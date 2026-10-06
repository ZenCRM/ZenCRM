"""Application metadata; credentials returned once and otherwise stored as hashes."""
from datetime import datetime
from ..extensions import db


class PluginApp(db.Model):
    __tablename__ = 'plugin_apps'
    id = db.Column(db.String(40), primary_key=True)
    manifest = db.Column(db.JSON, nullable=False)
    revision = db.Column(db.Integer, nullable=False, default=1)
    enabled = db.Column(db.Boolean, nullable=False, default=False)
    installed = db.Column(db.Boolean, nullable=False, default=False)
    approved_scopes = db.Column(db.JSON, nullable=False, default=list)
    allowed_users = db.Column(db.JSON, nullable=False, default=list)
    configuration = db.Column(db.JSON, nullable=False, default=dict)
    client_secret_hash = db.Column(db.String(256))
    signing_secret_encrypted = db.Column(db.Text)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __mapper_args__ = {'version_id_col': revision, 'version_id_generator': False}


class PluginGrant(db.Model):
    __tablename__ = 'plugin_grants'
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(40), db.ForeignKey('plugin_apps.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    scopes = db.Column(db.JSON, nullable=False, default=list)
    revision = db.Column(db.Integer, nullable=False, default=1)
    active = db.Column(db.Boolean, nullable=False, default=True)
    __table_args__ = (db.UniqueConstraint('app_id', 'user_id', name='uq_plugin_grant_user'),)
    __mapper_args__ = {'version_id_col': revision, 'version_id_generator': False}


class PluginCode(db.Model):
    __tablename__ = 'plugin_codes'
    code_hash = db.Column(db.String(64), primary_key=True)
    grant_id = db.Column(db.Integer, db.ForeignKey('plugin_grants.id', ondelete='CASCADE'), nullable=False)
    redirect_uri = db.Column(db.String(2048), nullable=False)
    challenge = db.Column(db.String(43), nullable=False)
    app_revision = db.Column(db.Integer, nullable=False)
    grant_revision = db.Column(db.Integer, nullable=False)
    password_version = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    consumed = db.Column(db.Boolean, nullable=False, default=False)


class PluginToken(db.Model):
    __tablename__ = 'plugin_tokens'
    access_hash = db.Column(db.String(64), primary_key=True)
    refresh_hash = db.Column(db.String(64), unique=True)
    family = db.Column(db.String(36), nullable=False, index=True)
    grant_id = db.Column(db.Integer, db.ForeignKey('plugin_grants.id', ondelete='CASCADE'), nullable=False)
    app_revision = db.Column(db.Integer, nullable=False)
    grant_revision = db.Column(db.Integer, nullable=False)
    password_version = db.Column(db.String(64), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    refresh_expires_at = db.Column(db.DateTime)
    revoked = db.Column(db.Boolean, nullable=False, default=False)
    refresh_used = db.Column(db.Boolean, nullable=False, default=False)


class PluginStorage(db.Model):
    __tablename__ = 'plugin_storage'
    id = db.Column(db.Integer, primary_key=True)
    grant_id = db.Column(db.Integer, db.ForeignKey('plugin_grants.id', ondelete='CASCADE'), nullable=False)
    key = db.Column(db.String(80), nullable=False)
    value = db.Column(db.JSON, nullable=False)
    revision = db.Column(db.Integer, nullable=False, default=1)
    __table_args__ = (db.UniqueConstraint('grant_id', 'key', name='uq_plugin_storage_key'),)


class PluginEvent(db.Model):
    __tablename__ = 'plugin_events'
    id = db.Column(db.String(36), primary_key=True)
    kind = db.Column(db.String(80), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)


class PluginSubscription(db.Model):
    __tablename__ = 'plugin_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    grant_id = db.Column(db.Integer, db.ForeignKey('plugin_grants.id', ondelete='CASCADE'), nullable=False)
    kind = db.Column(db.String(80), nullable=False)
    __table_args__ = (db.UniqueConstraint('grant_id', 'kind', name='uq_plugin_subscription_kind'),)


class PluginDelivery(db.Model):
    __tablename__ = 'plugin_deliveries'
    id = db.Column(db.String(36), primary_key=True)
    event_id = db.Column(db.String(36), db.ForeignKey('plugin_events.id', ondelete='CASCADE'), nullable=False)
    grant_id = db.Column(db.Integer, db.ForeignKey('plugin_grants.id', ondelete='CASCADE'), nullable=False)
    app_revision = db.Column(db.Integer, nullable=False)
    grant_revision = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    next_attempt_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    lease_token = db.Column(db.String(36))
    lease_until = db.Column(db.DateTime)
    last_status = db.Column(db.Integer)
    __table_args__ = (db.UniqueConstraint('event_id', 'grant_id', name='uq_plugin_delivery_event'),)


class PluginAudit(db.Model):
    __tablename__ = 'plugin_audit'
    id = db.Column(db.Integer, primary_key=True)
    app_id = db.Column(db.String(40), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))
    action = db.Column(db.String(80), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
