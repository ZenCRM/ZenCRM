from datetime import datetime
from ..extensions import db


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='todo')
    priority = db.Column(db.String(10), default='medium')
    due_date = db.Column(db.DateTime)
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id'))
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=True)
    assignee_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    deleted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def assignees(self):
        # Import lokalny aby uniknac cyklicznego importu
        from .task_assignee import TaskAssignee
        return TaskAssignee.query.filter_by(task_id=self.id).all()

    def recompute_status(self):
        """Ustawia status zadania na podstawie statusow wykonawcow."""
        from .task_assignee import TaskAssignee
        from ..utils.task_stages import get_task_stages
        rows = TaskAssignee.query.filter_by(task_id=self.id).all()
        if not rows:
            return
        statuses = [r.status for r in rows]
        if all(s == 'done' for s in statuses):
            self.status = 'done'
        elif any(s in ('in_progress', 'done') for s in statuses):
            intermediate = [stage['id'] for stage in get_task_stages() if stage['id'] not in ('todo', 'done')]
            self.status = self.status if self.status in intermediate else (intermediate[0] if intermediate else 'todo')
        else:
            self.status = 'todo'

    def to_dict(self):
        assignees = [ta.to_dict() for ta in self.assignees]
        assignee_legacy = None
        if self.assignee_id:
            from .user import User
            u = db.session.get(User, self.assignee_id)
            if u:
                assignee_legacy = {
                    'id': u.id, 'first_name': u.first_name,
                    'last_name': u.last_name, 'avatar_url': u.avatar_url,
                }
        return {
            'id': self.id, 'title': self.title, 'description': self.description,
            'status': self.status, 'priority': self.priority,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'client_id': self.client_id, 'lead_id': self.lead_id,
            'service_id': self.service_id, 'project_id': self.project_id,
            'assignee_id': self.assignee_id,
            'assignee': assignee_legacy,
            'assignees': assignees,
            'deleted_at': self.deleted_at.isoformat() if self.deleted_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
