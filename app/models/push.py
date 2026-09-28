"""Browser subscriptions and persistent delivery state (never public settings)."""
from datetime import datetime
from ..extensions import db


class PushIdentity(db.Model):
    __tablename__ = 'push_identity'
    id = db.Column(db.Integer, primary_key=True)
    private_key = db.Column(db.Text, nullable=False)


class PushSubscription(db.Model):
    __tablename__ = 'push_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    endpoint_hash = db.Column(db.String(64), unique=True, nullable=False)
    subscription = db.Column(db.JSON, nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)


class PushDelivery(db.Model):
    __tablename__ = 'push_deliveries'
    id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey('push_subscriptions.id'), nullable=False)
    reminder_id = db.Column(db.Integer, db.ForeignKey('reminders.id', ondelete='CASCADE'), nullable=False)
    scheduled_at = db.Column(db.DateTime, nullable=False)
    sent = db.Column(db.Boolean, nullable=False, default=False)
    next_attempt = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    attempts = db.Column(db.Integer, nullable=False, default=0)
    lease = db.Column(db.String(32))
    __table_args__ = (
        db.UniqueConstraint('subscription_id', 'reminder_id', 'scheduled_at', name='uq_push_delivery'),
        db.Index('ix_push_delivery_pending', 'sent', 'next_attempt'),
    )
