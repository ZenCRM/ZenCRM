from datetime import datetime
from ..extensions import db

class ServiceCatalog(db.Model):
    __tablename__ = 'service_catalog'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    billing_type = db.Column(db.String(20), default='subscription')  # subscription | one_time
    term_type = db.Column(db.String(20), default='indefinite')       # fixed | indefinite
    default_billing_cycle = db.Column(db.String(20), default='monthly')  # monthly | yearly
    default_price = db.Column(db.Numeric(10, 2))
    is_price_fixed = db.Column(db.Boolean, default=True)
    content = db.Column(db.Text)             # wzory, opis, warunki
    is_active = db.Column(db.Boolean, default=True)
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'description': self.description,
            'billing_type': self.billing_type, 'term_type': self.term_type,
            'default_billing_cycle': self.default_billing_cycle,
            'default_price': float(self.default_price) if self.default_price else 0,
            'is_price_fixed': self.is_price_fixed,
            'content': self.content, 'is_active': self.is_active,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
