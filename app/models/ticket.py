import secrets
from datetime import datetime
from ..extensions import db


class Ticket(db.Model):
    __tablename__ = 'tickets'

    id = db.Column(db.Integer, primary_key=True)
    ticket_number = db.Column(db.String(30), unique=True, nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id', ondelete='SET NULL'), nullable=True)
    contact_name = db.Column(db.String(100), nullable=True)
    contact_email = db.Column(db.String(120), nullable=False, index=True)
    contact_phone = db.Column(db.String(50), nullable=True)
    category = db.Column(db.String(50), default='general', nullable=False)
    priority = db.Column(db.String(20), default='medium', nullable=False)  # 'low', 'medium', 'high', 'urgent'
    status = db.Column(db.String(30), default='new', nullable=False)  # 'new', 'open', 'pending_client', 'resolved', 'closed'
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='SET NULL'), nullable=True)
    token = db.Column(db.String(64), unique=True, index=True, nullable=False)
    source = db.Column(db.String(30), default='portal')  # 'portal', 'helpdesk', 'webhook', 'crm'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    closed_at = db.Column(db.DateTime, nullable=True)

    client = db.relationship('Client', foreign_keys=[client_id])
    assignee = db.relationship('User', foreign_keys=[assignee_id])
    team = db.relationship('Team', foreign_keys=[team_id])
    messages = db.relationship('TicketMessage', backref='ticket', cascade='all, delete-orphan',
                               order_by='TicketMessage.created_at.asc()')

    @classmethod
    def generate_number(cls):
        year = datetime.utcnow().strftime('%Y')
        count = cls.query.filter(cls.ticket_number.like(f'TIC-{year}-%')).count() + 1
        return f'TIC-{year}-{count:04d}'

    @classmethod
    def generate_token(cls):
        return secrets.token_urlsafe(32)

    def to_dict(self, include_messages=False):
        data = {
            'id': self.id,
            'ticket_number': self.ticket_number,
            'title': self.title,
            'description': self.description,
            'client_id': self.client_id,
            'client_name': self.client.name if self.client else None,
            'contact_name': self.contact_name,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'category': self.category,
            'priority': self.priority,
            'status': self.status,
            'assignee_id': self.assignee_id,
            'assignee': {
                'id': self.assignee.id,
                'first_name': self.assignee.first_name,
                'last_name': self.assignee.last_name,
                'email': self.assignee.email,
                'avatar_url': self.assignee.avatar_url
            } if self.assignee else None,
            'team_id': self.team_id,
            'team': {
                'id': self.team.id,
                'name': self.team.name,
                'color': self.team.color
            } if self.team else None,
            'token': self.token,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'closed_at': self.closed_at.isoformat() if self.closed_at else None,
            'messages_count': len(self.messages),
        }
        if include_messages:
            data['messages'] = [m.to_dict() for m in self.messages]
        return data


class TicketMessage(db.Model):
    __tablename__ = 'ticket_messages'

    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets.id', ondelete='CASCADE'), nullable=False, index=True)
    sender_type = db.Column(db.String(20), default='client')  # 'client', 'agent', 'system'
    sender_name = db.Column(db.String(100), nullable=True)
    sender_email = db.Column(db.String(120), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'ticket_id': self.ticket_id,
            'sender_type': self.sender_type,
            'sender_name': self.sender_name or (f"{self.user.first_name} {self.user.last_name}" if self.user else 'Klient'),
            'sender_email': self.sender_email or (self.user.email if self.user else None),
            'user_id': self.user_id,
            'user_avatar': self.user.avatar_url if self.user else None,
            'content': self.content,
            'is_internal': self.is_internal,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
