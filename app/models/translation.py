from ..extensions import db


class TranslationLanguage(db.Model):
    __tablename__ = 'translation_languages'
    code = db.Column(db.String(16), primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    base_locale = db.Column(db.String(16), nullable=False, default='pl')


class TranslationEntry(db.Model):
    __tablename__ = 'translation_entries'
    locale = db.Column(db.String(16), primary_key=True)
    key = db.Column(db.String(500), primary_key=True)
    value = db.Column(db.Text, nullable=False)
