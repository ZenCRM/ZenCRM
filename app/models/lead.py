from datetime import datetime
from ..extensions import db

class Lead(db.Model):
    __tablename__ = 'leads'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    value = db.Column(db.Numeric(10, 2))
    stage = db.Column(db.String(30), default='new')
    source = db.Column(db.String(100))
    probability = db.Column(db.Integer, default=0)
    expected_close_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    converted_to_client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
            'id': self.id, 'title': self.title, 'client_id': self.client_id,
            'assignee_id': self.assignee_id, 'assignee': assignee,
            'value': float(self.value) if self.value else 0,
            'stage': self.stage, 'source': self.source,
            'probability': self.probability,
            'expected_close_date': self.expected_close_date.isoformat() if self.expected_close_date else None,
            'notes': self.notes,
            'converted_to_client_id': self.converted_to_client_id,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
