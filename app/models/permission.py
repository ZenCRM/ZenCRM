from ..extensions import db


class Role(db.Model):
    __tablename__ = 'roles'
    key = db.Column(db.String(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    built_in = db.Column(db.Boolean, nullable=False, default=False)

    def to_dict(self):
        return {'key': self.key, 'name': self.name, 'built_in': self.built_in}


class PermissionRule(db.Model):
    __tablename__ = 'permission_rules'
    id = db.Column(db.Integer, primary_key=True)
    role_key = db.Column(db.String(50), db.ForeignKey('roles.key', ondelete='CASCADE'), nullable=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id', ondelete='CASCADE'), nullable=True)
    permission = db.Column(db.String(80), nullable=False)
    allowed = db.Column(db.Boolean, nullable=False)
    __table_args__ = (
        db.CheckConstraint('(role_key IS NULL) != (team_id IS NULL)', name='permission_one_subject'),
        db.UniqueConstraint('role_key', 'permission', name='uq_permission_role'),
        db.UniqueConstraint('team_id', 'permission', name='uq_permission_team'),
    )
