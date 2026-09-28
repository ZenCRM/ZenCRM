from datetime import datetime
from ..extensions import db

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    kind = db.Column(db.String(16), nullable=False, default='note', server_default='note')
    communication_status = db.Column(db.String(16))
    address = db.Column(db.String(254))
    entity_type = db.Column(db.String(20), nullable=False)   # 'client' | 'lead'
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
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
            'content': self.content,
            'kind': self.kind or 'note',
            'communication_status': self.communication_status,
            'address': self.address,
            'entity_type': self.entity_type,
            'entity_id': self.entity_id,
            'user_id': self.user_id,
            'user': user,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
