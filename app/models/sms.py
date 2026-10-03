import json
from datetime import datetime, timedelta
from ..extensions import db


class SmsDevice(db.Model):
    __tablename__ = 'sms_devices'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(50))
    token = db.Column(db.String(120), unique=True, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime)
    today_stats = db.Column(db.Text)   # JSON string
    week_stats = db.Column(db.Text)    # JSON string
    stats_updated_at = db.Column(db.DateTime)
    last_sync_at = db.Column(db.DateTime)
    sync_from = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('sms_devices', lazy='dynamic'))
    queue_items = db.relationship('SmsQueue', backref='device', lazy='dynamic', cascade='all, delete-orphan')
    calls = db.relationship('PhoneCall', backref='device', lazy='dynamic', cascade='all, delete-orphan')
    messages = db.relationship('SmsMessage', backref='device', lazy='dynamic', cascade='all, delete-orphan')

    @property
    def is_online(self):
        if not self.last_seen:
            return False
        # Phone polls every 5 seconds; consider online if seen within 90 seconds
        return (datetime.utcnow() - self.last_seen) < timedelta(seconds=90)

    def to_dict(self):
        today_parsed = None
        week_parsed = None
        try:
            if self.today_stats:
                today_parsed = json.loads(self.today_stats)
        except Exception:
            pass
        try:
            if self.week_stats:
                week_parsed = json.loads(self.week_stats)
        except Exception:
            pass

        user_data = None
        if self.user:
            user_data = {
                'id': self.user.id,
                'name': f"{self.user.first_name} {self.user.last_name}".strip(),
                'email': self.user.email,
                'role': self.user.role
            }

        return {
            'id': self.id,
            'name': self.name,
            'phone_number': self.phone_number,
            'token': self.token,
            'user_id': self.user_id,
            'user_name': f"{self.user.first_name} {self.user.last_name}".strip() if self.user else None,
            'user': user_data,
            'is_active': bool(self.is_active),
            'is_online': self.is_online,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'today_stats': today_parsed,
            'week_stats': week_parsed,
            'stats_updated_at': self.stats_updated_at.isoformat() if self.stats_updated_at else None,
            'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
            'sync_from': self.sync_from.strftime('%Y-%m-%d') if self.sync_from else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class SmsQueue(db.Model):
    __tablename__ = 'sms_queue'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('sms_devices.id'), nullable=True)
    phone_number = db.Column(db.String(50))
    message = db.Column(db.Text)
    action = db.Column(db.String(50), default='send_sms')  # send_sms, get_stats, get_stats_sms, get_full_history, get_sms_history, get_sms_history_by_date
    payload = db.Column(db.Text)  # JSON string for extra action parameters
    status = db.Column(db.String(20), default='pending', index=True)   # pending, processing, sent, failed, completed
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime)
    claimed_at = db.Column(db.DateTime)

    def to_dict(self):
        payload_data = None
        if self.payload:
            try:
                payload_data = json.loads(self.payload)
            except Exception:
                payload_data = self.payload

        device_name = self.device.name if self.device else None
        client_name = None
        if self.client_id:
            from .client import Client
            c = db.session.get(Client, self.client_id)
            if c:
                client_name = c.name

        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': device_name,
            'phone_number': self.phone_number,
            'message': self.message,
            'action': self.action,
            'payload': payload_data,
            'status': self.status,
            'client_id': self.client_id,
            'client_name': client_name,
            'user_id': self.user_id,
            'error_message': self.error_message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'sent_at': self.sent_at.isoformat() if self.sent_at else None,
        }


class PhoneCall(db.Model):
    __tablename__ = 'phone_calls'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('sms_devices.id'), nullable=True)
    number = db.Column(db.String(50), nullable=False, index=True)
    name = db.Column(db.String(100))  # Caller name from phone's phonebook
    type = db.Column(db.String(20), nullable=False)  # incoming, outgoing, missed, rejected
    timestamp = db.Column(db.BigInteger, index=True)  # Unix epoch ms from phone
    call_time = db.Column(db.DateTime)
    date_formatted = db.Column(db.String(50))
    duration_sec = db.Column(db.Integer, default=0)
    duration_formatted = db.Column(db.String(50))
    note = db.Column(db.Text)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        device_name = self.device.name if self.device else None
        user_name = f"{self.device.user.first_name} {self.device.user.last_name}".strip() if (self.device and self.device.user) else None
        user_id = self.device.user_id if self.device else None
        client_data = None
        if self.client_id:
            from .client import Client
            c = db.session.get(Client, self.client_id)
            if c:
                client_data = {'id': c.id, 'name': c.name, 'company': c.company}

        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': device_name,
            'user_id': user_id,
            'user_name': user_name,
            'number': self.number,
            'name': self.name,
            'type': self.type,
            'timestamp': self.timestamp,
            'call_time': self.call_time.isoformat() if self.call_time else None,
            'date_formatted': self.date_formatted,
            'duration_sec': self.duration_sec,
            'duration_formatted': self.duration_formatted,
            'note': self.note or '',
            'client_id': self.client_id,
            'client': client_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class SmsMessage(db.Model):
    __tablename__ = 'sms_messages'

    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey('sms_devices.id'), nullable=True)
    address = db.Column(db.String(50), nullable=False, index=True)
    body = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False)  # received, sent
    timestamp = db.Column(db.BigInteger, index=True)
    message_time = db.Column(db.DateTime)
    date_formatted = db.Column(db.String(50))
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        device_name = self.device.name if self.device else None
        user_name = f"{self.device.user.first_name} {self.device.user.last_name}".strip() if (self.device and self.device.user) else None
        user_id = self.device.user_id if self.device else None
        client_data = None
        if self.client_id:
            from .client import Client
            c = db.session.get(Client, self.client_id)
            if c:
                client_data = {'id': c.id, 'name': c.name, 'company': c.company}

        return {
            'id': self.id,
            'device_id': self.device_id,
            'device_name': device_name,
            'user_id': user_id,
            'user_name': user_name,
            'address': self.address,
            'body': self.body,
            'type': self.type,
            'timestamp': self.timestamp,
            'message_time': self.message_time.isoformat() if self.message_time else None,
            'date_formatted': self.date_formatted,
            'client_id': self.client_id,
            'client': client_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
