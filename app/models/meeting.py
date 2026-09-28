from datetime import datetime
from ..extensions import db

class Meeting(db.Model):
    __tablename__ = 'meetings'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(200))
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'))
    organizer_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    status = db.Column(db.String(20), default='scheduled')
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'description': self.description,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'location': self.location, 'client_id': self.client_id, 'lead_id': self.lead_id,
            'organizer_id': self.organizer_id, 'status': self.status,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
        }
