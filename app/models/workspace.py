from datetime import datetime
from ..extensions import db


class PortalConfiguration(db.Model):
    __tablename__ = 'portal_configuration'
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.JSON, nullable=False, default=dict)


class PortalClientSpace(db.Model):
    __tablename__ = 'portal_client_spaces'
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey('portal_spaces.id'), unique=True, nullable=False)


class CustomField(db.Model):
    __tablename__ = 'custom_fields'
    id = db.Column(db.Integer, primary_key=True)
    entity = db.Column(db.String(40), nullable=False, index=True)
    label = db.Column(db.String(120), nullable=False)
    kind = db.Column(db.String(20), nullable=False, default='text')
    required = db.Column(db.Boolean, default=False, nullable=False)

    def to_dict(self):
        return dict(id=self.id, entity=self.entity, label=self.label, kind=self.kind, required=bool(self.required))


class CustomValue(db.Model):
    __tablename__ = 'custom_values'
    id = db.Column(db.Integer, primary_key=True)
    field_id = db.Column(db.Integer, db.ForeignKey('custom_fields.id'), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    value = db.Column(db.Text, default='')
    __table_args__ = (db.UniqueConstraint('field_id', 'record_id'),)


class PortalSpace(db.Model):
    __tablename__ = 'portal_spaces'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, default='')

    def to_dict(self):
        return dict(id=self.id, name=self.name, description=self.description)


class PortalMember(db.Model):
    __tablename__ = 'portal_members'
    id = db.Column(db.Integer, primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey('portal_spaces.id'), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    __table_args__ = (db.UniqueConstraint('space_id', 'email'),)

    def to_dict(self):
        return dict(id=self.id, email=self.email, active=self.active)


class PortalSession(db.Model):
    __tablename__ = 'portal_sessions'
    token_hash = db.Column(db.String(64), primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('portal_members.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)


class PortalItem(db.Model):
    __tablename__ = 'portal_items'
    id = db.Column(db.Integer, primary_key=True)
    space_id = db.Column(db.Integer, db.ForeignKey('portal_spaces.id'), nullable=False, index=True)
    kind = db.Column(db.String(20), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default='')
    status = db.Column(db.String(20), default='open')
    filename = db.Column(db.String(255))
    storage_name = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return dict(id=self.id, kind=self.kind, title=self.title, content=self.content,
                    status=self.status, filename=self.filename, created_at=self.created_at.isoformat())


class PortalReply(db.Model):
    __tablename__ = 'portal_replies'
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('portal_items.id'), nullable=False, index=True)
    author = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return dict(id=self.id, author=self.author, content=self.content, created_at=self.created_at.isoformat())
