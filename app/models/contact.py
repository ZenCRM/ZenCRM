from datetime import datetime
from ..extensions import db

class Contact(db.Model):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=True, default='')
    email = db.Column(db.String(120))
    phone = db.Column(db.String(30))
    position = db.Column(db.String(100))
    notes = db.Column(db.Text)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'))
    is_primary = db.Column(db.Boolean, default=False, nullable=False)
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'first_name': self.first_name, 'last_name': self.last_name or '',
            'full_name': f'{self.first_name or ""} {self.last_name or ""}'.strip(),
            'email': self.email, 'phone': self.phone, 'position': self.position,
            'notes': self.notes, 'client_id': self.client_id, 'lead_id': self.lead_id,
            'is_primary': bool(self.is_primary),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
