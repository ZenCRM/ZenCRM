from datetime import datetime
from ..extensions import db

class TaskAssignee(db.Model):
    __tablename__ = 'task_assignees'
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending|in_progress|done
    comment = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        from .user import User
        u = db.session.get(User, self.user_id)
        user = {'id': u.id, 'first_name': u.first_name, 'last_name': u.last_name,
                'avatar_url': u.avatar_url} if u else None
        return {
            'id': self.id, 'task_id': self.task_id, 'user_id': self.user_id,
            'user': user, 'status': self.status, 'comment': self.comment,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
