from datetime import datetime
from ..extensions import db


class Attachment(db.Model):
    __tablename__ = 'attachments'
    id = db.Column(db.Integer, primary_key=True)
    entity_type = db.Column(db.String(20), nullable=False, index=True)
    entity_id = db.Column(db.Integer, nullable=False, index=True)
    filename = db.Column(db.String(255), nullable=False)
    storage_name = db.Column(db.String(64), nullable=False, unique=True)
    size = db.Column(db.Integer, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        from .user import User
        user = db.session.get(User, self.created_by_id) if self.created_by_id else None
        return dict(id=self.id, filename=self.filename, size=self.size,
                    created_by_id=self.created_by_id,
                    created_by={'id': user.id, 'name': f'{user.first_name} {user.last_name}'.strip(),
                                'avatar_url': user.avatar_url} if user else None,
                    created_at=self.created_at.isoformat())
