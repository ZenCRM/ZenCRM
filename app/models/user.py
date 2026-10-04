from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(50), default='employee')
    is_active = db.Column(db.Boolean, default=True)
    avatar_url = db.Column(db.String(500))
    default_call_method = db.Column(db.String(20), default='link')  # 'link' or 'android'
    default_email_method = db.Column(db.String(20), nullable=False, default='mailto', server_default='mailto')
    email_notifications = db.Column(db.Text, default='{}')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_email_notifications(self):
        import json
        try:
            if not self.email_notifications:
                return {}
            data = json.loads(self.email_notifications)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def can_receive_email(self, event_key):
        """Sprawdza, czy użytkownik ma włączone powiadomienie e-mail (domyślnie True)."""
        if not self.email or not self.is_active:
            return False
        prefs = self.get_email_notifications()
        # Domyślnie włączone jeśli nie zdefiniowano w preferencjach
        return prefs.get(event_key, True) is not False

    def to_dict(self):
        user_teams = []
        try:
            if hasattr(self, 'teams'):
                t_list = self.teams.all() if hasattr(self.teams, 'all') else self.teams
                user_teams = [{'id': t.id, 'name': t.name, 'color': t.color or '#018bfc'} for t in (t_list or [])]
        except Exception:
            pass

        devices_list = []
        try:
            if hasattr(self, 'sms_devices'):
                devs = self.sms_devices.all() if hasattr(self.sms_devices, 'all') else self.sms_devices
                devices_list = [{'id': d.id, 'name': d.name, 'phone_number': d.phone_number, 'is_online': d.is_online} for d in (devs or [])]
        except Exception:
            pass

        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role,
            'is_active': self.is_active,
            'avatar_url': self.avatar_url,
            'default_call_method': self.default_call_method or 'link',
            'default_email_method': self.default_email_method or 'mailto',
            'devices': devices_list,
            'phone': devices_list[0]['phone_number'] if devices_list and devices_list[0].get('phone_number') else None,
            'email_notifications': self.get_email_notifications(),
            'teams': user_teams,
            'team_ids': [t['id'] for t in user_teams],
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
