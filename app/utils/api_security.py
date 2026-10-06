"""Require an active CRM account unless an entry point has been reviewed."""
import hashlib
import hmac
from flask import abort, request
from flask_jwt_extended import verify_jwt_in_request
from ..extensions import db, jwt
from .deletion import current_user

PUBLIC = {
    'auth.login': {'POST'}, 'auth.forgot_password': {'POST'},
    'auth.reset_password': {'POST'},
    'auth.setup_status': {'GET', 'HEAD'},
    'auth.setup_admin': {'POST'},
    'settings.public_settings': {'GET', 'HEAD'},
    'settings.serve_branding': {'GET', 'HEAD'},
    'branding.serve_branding_file': {'GET', 'HEAD'},
    'avatars.serve': {'GET', 'HEAD'},
    'portal.login': {'POST'}, 'portal.logout': {'POST'},
    'portal.configuration': {'GET', 'HEAD'}, 'portal.branding': {'GET', 'HEAD'},
    'tickets.public_helpdesk_config': {'GET', 'HEAD'},
    'tickets.public_submit_ticket': {'POST'},
    # One-time OAuth state, HttpOnly browser cookie and grant binding verified by this handler.
    'plugins.google_drive_callback': {'GET', 'HEAD'},
}
# These specific handlers check their own capability or device tokens.
TOKEN_HANDLERS = {
    'public.view_offer', 'public.view_document',
    'tickets.public_track_ticket', 'tickets.public_reply_ticket',
    'tickets.webhook_submit_ticket', 'leads.webhook_submit_lead',
    'sms.get_next_task', 'sms.report_sms_status', 'sms.receive_stats',
    'sms.receive_call_history', 'sms.receive_sms_history',
}
# Each calls access(space_id), checking portal token expiry and client scope.
PORTAL_HANDLERS = {
    'portal.space_detail', 'portal.create_item', 'portal.update_item',
    'portal.replies', 'portal.attachment',
}


def password_version(user):
    return hashlib.sha256((user.password_hash or '').encode()).hexdigest()


def init_api_security(app):
    @jwt.additional_claims_loader
    def password_claim(identity):
        from ..models.user import User
        try:
            user = db.session.get(User, int(identity))
        except (TypeError, ValueError):
            user = None
        return {'password_version': password_version(user)} if user else {}

    @jwt.token_in_blocklist_loader
    def stale_password(header, payload):
        from ..models.user import User
        try:
            user = db.session.get(User, int(payload['sub']))
        except (KeyError, TypeError, ValueError):
            return True
        if not user:
            return True
        version = payload.get('password_version')
        return not isinstance(version, str) or not hmac.compare_digest(version, password_version(user))

    @app.before_request
    def authenticate_api():
        if not request.path.startswith('/api/') or request.method == 'OPTIONS':
            return
        endpoint = request.endpoint
        if not endpoint or endpoint in ('static', 'static_files'):
            abort(404)
        from ..plugins.integration_api import INTEGRATION_ENDPOINTS, authenticate_integration
        if request.method in INTEGRATION_ENDPOINTS.get(endpoint, set()):
            return authenticate_integration()
        if request.method in PUBLIC.get(endpoint, set()) or endpoint in TOKEN_HANDLERS:
            return
        if endpoint in PORTAL_HANDLERS and request.headers.get('X-Portal-Token'):
            return
        verify_jwt_in_request(refresh=endpoint == 'auth.refresh')
        user = current_user()
        if user is None or not user.is_active:
            abort(403)

    @app.after_request
    def security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'no-referrer'
        # Only the workspace view is embedded, by the same-origin portal admin page.
        response.headers['X-Frame-Options'] = 'SAMEORIGIN' if request.path == '/workspace.html' else 'DENY'
        if response.mimetype == 'image/svg+xml':
            response.headers['Content-Security-Policy'] = "sandbox; default-src 'none'"
        if request.path.startswith('/api/') and response.mimetype == 'text/html' and 'Content-Security-Policy' not in response.headers:
            response.headers['Content-Security-Policy'] = "sandbox; default-src 'none'; img-src data: https:; style-src 'unsafe-inline'; font-src data:"
        if request.is_secure:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        if request.path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response
