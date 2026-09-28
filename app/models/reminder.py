from datetime import datetime
from ..extensions import db


class Reminder(db.Model):
    __tablename__ = 'reminders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    title = db.Column(db.String(200), nullable=False)
    remind_at = db.Column(db.DateTime, nullable=False, index=True)
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), nullable=True)
    link = db.Column(db.String(500), nullable=True)
    dismissed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (db.UniqueConstraint('user_id', 'task_id', name='uq_reminder_user_task'),)

    def to_dict(self):
        return dict(
            id=self.id,
            title=self.title,
            remind_at=self.remind_at.isoformat() + 'Z' if self.remind_at else None,
            task_id=self.task_id,
            link=self.link,
            dismissed=self.dismissed,
            created_at=self.created_at.isoformat() + 'Z' if self.created_at else None
        )
