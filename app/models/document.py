from datetime import datetime
from ..extensions import db

class Document(db.Model):
    __tablename__ = 'documents'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), default='other')
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'))
    content = db.Column(db.Text)
    rendered_html = db.Column(db.Text)
    data = db.Column(db.JSON)
    file_path = db.Column(db.String(500))
    pdf_path = db.Column(db.String(500))
    public_token = db.Column(db.String(64), unique=True, index=True)
    status = db.Column(db.String(20), default='draft')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'title': self.title, 'type': self.type,
            'client_id': self.client_id, 'lead_id': self.lead_id,
            'service_id': self.service_id,
            'template_id': self.template_id,
            'content': self.content, 'rendered_html': self.rendered_html,
            'data': self.data,
            'file_path': self.file_path, 'pdf_path': self.pdf_path,
            'public_token': self.public_token, 'status': self.status,
            'created_by': self.created_by,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
