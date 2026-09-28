from datetime import datetime
from ..extensions import db

class Setting(db.Model):
    __tablename__ = 'settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    category = db.Column(db.String(50), default='general')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'category': self.category,
        }

    @classmethod
    def get_value(cls, key, default=None):
        s = cls.query.filter_by(key=key).first()
        return s.value if s else default

    @classmethod
    def set_value(cls, key, value, category='general'):
        s = cls.query.filter_by(key=key).first()
        if s:
            s.value = value
            if category:
                s.category = category
        else:
            s = cls(key=key, value=value, category=category)
            db.session.add(s)
        return s
