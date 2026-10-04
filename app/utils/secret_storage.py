"""Versioned encryption for installation secrets stored in settings."""
import base64
import hashlib
from cryptography.fernet import Fernet
from flask import current_app

PREFIX = 'fernet:v1:'


def _cipher():
    # Separate from MAILBOX_ENCRYPTION_KEY so deploying that option cannot
    # silently change the key protecting existing notification credentials.
    secret = current_app.config['SECRET_KEY']
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def seal(value):
    return PREFIX + _cipher().encrypt(value.encode()).decode()


def unseal(value):
    if not value:
        return ''
    if not value.startswith(PREFIX):
        raise ValueError('SMTP password requires migration; run seed.py')
    return _cipher().decrypt(value[len(PREFIX):].encode()).decode()


def migrate_smtp_password():
    """Encrypt legacy plaintext once, during schema preparation under its lock."""
    from ..extensions import db
    from ..models.setting import Setting
    setting = Setting.query.filter_by(key='smtp_password').first()
    if setting and setting.value and not setting.value.startswith(PREFIX):
        setting.value = seal(setting.value)
        db.session.commit()
