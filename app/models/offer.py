from datetime import datetime
from ..extensions import db

class Offer(db.Model):
    __tablename__ = 'offers'
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(50), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'))
    content = db.Column(db.Text)
    rendered_html = db.Column(db.Text)
    data = db.Column(db.JSON)
    total_amount = db.Column(db.Numeric(10, 2))
    status = db.Column(db.String(20), default='draft')
    valid_until = db.Column(db.Date)
    public_token = db.Column(db.String(64), unique=True, index=True)
    pdf_path = db.Column(db.String(500))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'number': self.number, 'title': self.title,
            'client_id': self.client_id, 'template_id': self.template_id,
            'content': self.content, 'rendered_html': self.rendered_html,
            'data': self.data,
            'total_amount': float(self.total_amount) if self.total_amount else 0,
            'status': self.status,
            'valid_until': self.valid_until.isoformat() if self.valid_until else None,
            'public_token': self.public_token, 'pdf_path': self.pdf_path,
            'created_by': self.created_by,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
