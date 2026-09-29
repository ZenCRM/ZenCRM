from ..extensions import db


class PasswordReset(db.Model):
    __tablename__ = 'password_resets'
    token_hash = db.Column(db.String(64), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    password_version = db.Column(db.String(256), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)


class AuthRateLimit(db.Model):
    __tablename__ = 'auth_rate_limits'
    key = db.Column(db.String(64), primary_key=True)
    count = db.Column(db.Integer, nullable=False, default=0)
    expires_at = db.Column(db.Integer, nullable=False, index=True)
