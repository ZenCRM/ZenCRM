from datetime import datetime
from ..extensions import db

class Template(db.Model):
    __tablename__ = 'templates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # offer | document
    document_type_key = db.Column(db.String(50), db.ForeignKey('document_types.key'))
    content = db.Column(db.Text, nullable=False)
    variables = db.Column(db.JSON)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id, 'name': self.name, 'type': self.type,
            'document_type_key': self.document_type_key,
            'content': self.content, 'variables': self.variables,
            'is_active': self.is_active
        }
