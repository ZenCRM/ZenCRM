"""Personal and shared mailboxes. Credentials are never serialized."""
from datetime import datetime
from ..extensions import db


class Mailbox(db.Model):
    __tablename__ = 'mailboxes'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'))
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='CASCADE'))
    username = db.Column(db.String(254), nullable=False)
    password_encrypted = db.Column(db.Text, nullable=False)
    imap_host = db.Column(db.String(254), nullable=False)
    imap_port = db.Column(db.Integer, default=993, nullable=False)
    smtp_host = db.Column(db.String(254), nullable=False)
    smtp_port = db.Column(db.Integer, default=587, nullable=False)
    smtp_security = db.Column(db.String(10), default='starttls', nullable=False)
    signature = db.Column(db.Text, default='', nullable=False)
    signature_format = db.Column(db.String(10), default='text', nullable=False)
    last_sync_at = db.Column(db.DateTime)
    sync_interval_minutes = db.Column(db.Integer, default=5, nullable=False)
    next_sync_at = db.Column(db.DateTime)
    sync_claim_token = db.Column(db.String(36))
    sync_claim_until = db.Column(db.DateTime)
    uid_validity = db.Column(db.String(50))
    messages = db.relationship('MailMessage', cascade='all, delete-orphan', passive_deletes=True)
    __table_args__ = (db.CheckConstraint('(user_id IS NULL) != (team_id IS NULL)', name='mailbox_owner'),)

    def to_dict(self):
        fields = ('id', 'name', 'email', 'user_id', 'team_id', 'username', 'imap_host',
                  'imap_port', 'smtp_host', 'smtp_port', 'smtp_security', 'signature', 'signature_format', 'sync_interval_minutes')
        return {**{key: getattr(self, key) for key in fields},
                'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None}


class MailMessage(db.Model):
    __tablename__ = 'mail_messages'
    id = db.Column(db.Integer, primary_key=True)
    mailbox_id = db.Column(db.Integer, db.ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False, index=True)
    remote_uid = db.Column(db.String(100))
    message_id = db.Column(db.String(998))
    folder = db.Column(db.String(20), default='inbox', nullable=False)
    sender = db.Column(db.String(254), nullable=False)
    recipients = db.Column(db.JSON, default=list, nullable=False)
    cc = db.Column(db.JSON, default=list, nullable=False)
    bcc = db.Column(db.JSON, default=list, nullable=False)
    body_html = db.Column(db.Text, default='', nullable=False)
    attachments = db.Column(db.JSON, default=list, nullable=False)
    content_version = db.Column(db.Integer, default=0, nullable=False)
    subject = db.Column(db.Text, default='')
    body = db.Column(db.Text, default='')
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (db.UniqueConstraint('mailbox_id', 'remote_uid', name='mail_message_uid'),)

    def to_dict(self):
        return {**{key: getattr(self, key) for key in ('id', 'mailbox_id', 'folder', 'sender',
                'recipients', 'cc', 'bcc', 'subject', 'body', 'body_html', 'attachments', 'is_read', 'message_id')},
                'created_at': self.created_at.isoformat()}
