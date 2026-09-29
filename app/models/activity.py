from datetime import datetime
from ..extensions import db

class Activity(db.Model):
    __tablename__ = 'activities'
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text)
    entity_type = db.Column(db.String(20), nullable=False)
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    meta = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        from ..utils.i18n import activity_text
        user = None
        if self.user_id:
            from .user import User
            u = db.session.get(User, self.user_id)
            if u:
                user = {
                    'id': u.id, 'first_name': u.first_name,
                    'last_name': u.last_name, 'avatar_url': u.avatar_url,
                }
        return {
            'id': self.id,
            'action': self.action,
            'description': activity_text(self.description, self.action, self.meta),
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'user_id': self.user_id,
            'user': user,
            'meta': self.meta,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
