from datetime import datetime
from ..extensions import db


class Service(db.Model):
    """Konkretna usluga klienta."""
    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    catalog_id = db.Column(db.Integer, db.ForeignKey('service_catalog.id'))
    billing_type = db.Column(db.String(20), default='subscription')
    term_type = db.Column(db.String(20), default='indefinite')
    billing_cycle = db.Column(db.String(20), default='monthly')
    price = db.Column(db.Numeric(10, 2))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='good')
    risk_level = db.Column(db.Integer)
    notes = db.Column(db.Text)
    assignee_ids = db.Column(db.JSON)  # lista user_id
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def assignees_list(self):
        """Zwraca pelne obiekty userow przypisanych do uslugi."""
        from .user import User
        ids = self.assignee_ids or []
        if not isinstance(ids, list):
            return []
        result = []
        for uid in ids:
            try:
                u = db.session.get(User, int(uid))
            except (ValueError, TypeError):
                u = None
            if u:
                result.append({
                    'id': u.id,
                    'first_name': u.first_name,
                    'last_name': u.last_name,
                    'avatar_url': u.avatar_url,
                    'role': u.role,
                })
        return result

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'description': self.description,
            'client_id': self.client_id, 'catalog_id': self.catalog_id,
            'billing_type': self.billing_type, 'term_type': self.term_type,
            'billing_cycle': self.billing_cycle,
            'price': float(self.price) if self.price else 0,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'status': self.status, 'risk_level': self.risk_level,
            'notes': self.notes,
            'assignee_ids': self.assignee_ids or [],
            'assignees': self.assignees_list(),
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
