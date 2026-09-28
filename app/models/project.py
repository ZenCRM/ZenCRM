from datetime import datetime
from decimal import Decimal
from ..extensions import db


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    status = db.Column(db.String(30), default='in_progress', nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    budget = db.Column(db.Numeric(12, 2), default=0)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    task_stages = db.Column(db.Text, nullable=True)  # JSON string
    deleted_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client = db.relationship('Client', backref=db.backref('projects', lazy=True))
    manager = db.relationship('User', foreign_keys=[manager_id])
    members = db.relationship('ProjectMember', backref='project', cascade='all, delete-orphan')
    tasks = db.relationship('Task', backref='project_rel', foreign_keys='Task.project_id', lazy=True)

    def to_dict(self, include_tasks=False):
        import json
        tasks_list = [t for t in self.tasks if not t.deleted_at]
        total_tasks = len(tasks_list)
        done_tasks = len([t for t in tasks_list if t.status == 'done'])
        percent_done = int(round((done_tasks / total_tasks) * 100)) if total_tasks > 0 else 0

        manager_dict = None
        if self.manager:
            manager_dict = {
                'id': self.manager.id,
                'first_name': self.manager.first_name,
                'last_name': self.manager.last_name,
                'email': self.manager.email,
                'avatar_url': getattr(self.manager, 'avatar_url', None),
            }

        client_dict = None
        if self.client:
            client_dict = {
                'id': self.client.id,
                'name': self.client.name,
                'email': self.client.email,
                'phone': self.client.phone,
                'company': self.client.company,
            }

        stages = None
        if self.task_stages:
            try:
                stages = json.loads(self.task_stages)
            except Exception:
                stages = None

        result = {
            'id': self.id,
            'name': self.name,
            'description': self.description or '',
            'status': self.status,
            'client_id': self.client_id,
            'client': client_dict,
            'client_name': self.client.name if self.client else None,
            'manager_id': self.manager_id,
            'manager': manager_dict,
            'budget': float(self.budget) if self.budget is not None else 0.0,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'task_stages': stages,
            'members': [m.to_dict() for m in self.members],
            'member_ids': [m.user_id for m in self.members],
            'tasks_count': total_tasks,
            'tasks_done_count': done_tasks,
            'percent_done': percent_done,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_tasks:
            result['tasks'] = [t.to_dict() for t in tasks_list]

        return result


class ProjectMember(db.Model):
    __tablename__ = 'project_members'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    role = db.Column(db.String(50), default='member', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('project_id', 'user_id'),)

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        user_dict = None
        if self.user:
            user_dict = {
                'id': self.user.id,
                'first_name': self.user.first_name,
                'last_name': self.user.last_name,
                'email': self.user.email,
                'avatar_url': getattr(self.user, 'avatar_url', None),
            }
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role': self.role,
            'user': user_dict,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
