"""Configurable document categories and their form fields."""
from ..extensions import db


DEFAULT_DOCUMENT_TYPES = (
    ('contract', 'Umowa'), ('invoice', 'Faktura'),
    ('report', 'Raport'), ('other', 'Inne'),
)


class DocumentType(db.Model):
    __tablename__ = 'document_types'
    key = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    fields = db.Column(db.JSON, nullable=False, default=list)
    is_active = db.Column(db.Boolean, nullable=False, default=True)

    def to_dict(self):
        return dict(key=self.key, name=self.name, fields=self.fields or [],
                    is_active=bool(self.is_active))

    @classmethod
    def seed_defaults(cls):
        for key, name in DEFAULT_DOCUMENT_TYPES:
            if db.session.get(cls, key) is None:
                db.session.add(cls(key=key, name=name, fields=[]))
        db.session.commit()
