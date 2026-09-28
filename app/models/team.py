from datetime import datetime
from ..extensions import db

team_members = db.Table(
    'team_members',
    db.Column('team_id', db.Integer, db.ForeignKey('teams.id', ondelete='CASCADE'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow)
)


class Team(db.Model):
    __tablename__ = 'teams'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    color = db.Column(db.String(30), default='#018bfc')
    leader_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    leader = db.relationship('User', foreign_keys=[leader_id])
    members = db.relationship('User', secondary=team_members, backref=db.backref('teams', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'color': self.color or '#018bfc',
            'leader_id': self.leader_id,
            'leader': {
                'id': self.leader.id,
                'first_name': self.leader.first_name,
                'last_name': self.leader.last_name,
                'email': self.leader.email,
                'avatar_url': self.leader.avatar_url,
            } if self.leader else None,
            'member_ids': [m.id for m in self.members],
            'members': [{
                'id': m.id,
                'first_name': m.first_name,
                'last_name': m.last_name,
                'email': m.email,
                'avatar_url': m.avatar_url,
                'role': m.role,
            } for m in self.members],
            'members_count': len(self.members),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
