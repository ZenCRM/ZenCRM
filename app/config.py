import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///zencrm.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-dev-secret')
    JWT_ACCESS_TOKEN_EXPIRES = 3600          # 1 godzina
    JWT_REFRESH_TOKEN_EXPIRES = 2592000      # 30 dni

    PUSH_ENABLED = os.getenv("PUSH_ENABLED", "true").lower() == "true"
    MAIL_POLLING_ENABLED = os.getenv('MAIL_POLLING_ENABLED', 'true').lower() == 'true'
    MAILBOX_ENCRYPTION_KEY = os.getenv('MAILBOX_ENCRYPTION_KEY', '').strip() or None
    VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:admin@example.com")
    GUS_API_KEY = os.getenv('GUS_API_KEY', '').strip()
    GUS_TEST_MODE = os.getenv('GUS_TEST_MODE', 'false').lower() == 'true'
    MAX_CONTENT_LENGTH = 21 * 1024 * 1024
    CORS_ORIGINS = [origin.strip() for origin in os.getenv('CORS_ORIGINS', '').split(',') if origin.strip()]
    PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').strip()
    TRUSTED_PROXY_HOPS = int(os.getenv('TRUSTED_PROXY_HOPS', '0'))
    # Disable in application workers when a separate step (seed.py) migrates the database first.
    PREPARE_DATABASE = os.getenv('PREPARE_DATABASE', 'true').lower() == 'true'
    # Initial state until an administrator saves the platform switch in CRM settings.
    PLUGINS_ENABLED = os.getenv('PLUGINS_ENABLED', 'false').lower() == 'true'
    # Emergency server veto; the CRM panel cannot override it.
    PLUGINS_LOCKED = os.getenv('PLUGINS_LOCKED', 'false').lower() == 'true'
    GOOGLE_DRIVE_CLIENT_ID = os.getenv('GOOGLE_DRIVE_CLIENT_ID', '').strip()
    GOOGLE_DRIVE_CLIENT_SECRET = os.getenv('GOOGLE_DRIVE_CLIENT_SECRET', '').strip()
