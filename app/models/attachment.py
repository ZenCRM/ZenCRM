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
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return dict(id=self.id, filename=self.filename, size=self.size,
                    created_at=self.created_at.isoformat())
