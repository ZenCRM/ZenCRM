from datetime import datetime
from ..extensions import db

class Client(db.Model):
    __tablename__ = 'clients'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    company = db.Column(db.String(200))
    address = db.Column(db.Text)
    status = db.Column(db.String(20), default='active')
    notes = db.Column(db.Text)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        assignee = None
        if self.assignee_id:
            from .user import User
            u = db.session.get(User, self.assignee_id)
            if u:
                assignee = {
                    'id': u.id, 'first_name': u.first_name,
                    'last_name': u.last_name, 'avatar_url': u.avatar_url,
                }
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'company': self.company,
            'address': self.address,
            'status': self.status,
            'notes': self.notes,
            'assignee_id': self.assignee_id,
            'assignee': assignee,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
