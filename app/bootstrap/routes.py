"""Register existing API routes without changing endpoint identities."""
import os
from flask import send_from_directory


def register_api(app):
    from ..api.mailboxes import mailboxes_bp
    app.register_blueprint(mailboxes_bp, url_prefix='/api/mailboxes')
    from ..models import (user, client, lead, task, meeting, service,
                         template, offer, document, contact, comment, activity,
                         service_catalog, task_assignee, setting, sms, workspace, project, team, ticket, permission, email_template, auth_security, attachment, document_type, translation)

    from ..api.push import push_bp
    app.register_blueprint(push_bp, url_prefix="/api/push")

    from ..api.reminders import reminders_bp
    app.register_blueprint(reminders_bp, url_prefix='/api/reminders')

    from ..api.notifications import notifications_bp
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')

    from ..api.auth       import auth_bp
    from ..api.clients    import clients_bp
    from ..api.leads      import leads_bp
    from ..api.tasks      import tasks_bp
    from ..api.meetings   import meetings_bp
    from ..api.services   import services_bp
    from ..api.service_catalog import service_catalog_bp, service_catalog_alias_bp
    from ..api.task_assignees  import task_assignees_bp
    from ..api.offers     import offers_bp
    from ..api.documents  import documents_bp
    from ..api.attachments import attachments_bp
    from ..api.document_types import document_types_bp
    from ..api.templates  import templates_bp
    from ..api.users      import users_bp
    from ..api.stats      import stats_bp
    from ..api.public     import public_bp
    from ..api.contacts   import contacts_bp
    from ..api.comments   import comments_bp
    from ..api.activities import activities_bp
    from ..api.avatars    import avatars_bp
    from ..api.archive    import archive_bp
    from ..api.settings   import settings_bp
    from ..api.sms        import sms_bp
    from ..api.projects   import projects_bp
    from ..api.teams      import teams_bp
    from ..api.tickets    import tickets_bp
    from ..api.permissions import permissions_bp
    from ..api.translations import translations_bp
    from ..api.updates import updates_bp

    from ..utils.permissions import guard_action
    app.before_request(guard_action)

    app.register_blueprint(auth_bp,       url_prefix='/api/auth')
    app.register_blueprint(clients_bp,    url_prefix='/api/clients')
    app.register_blueprint(leads_bp,      url_prefix='/api/leads')
    app.register_blueprint(tasks_bp,      url_prefix='/api/tasks')
    app.register_blueprint(projects_bp,   url_prefix='/api/projects')
    app.register_blueprint(teams_bp,      url_prefix='/api/teams')
    app.register_blueprint(permissions_bp, url_prefix='/api/permissions')
    app.register_blueprint(translations_bp, url_prefix='/api/translations')
    app.register_blueprint(updates_bp, url_prefix='/api/updates')
    app.register_blueprint(tickets_bp,    url_prefix='/api/tickets')
    app.register_blueprint(meetings_bp,   url_prefix='/api/meetings')
    app.register_blueprint(services_bp,   url_prefix='/api/services')
    app.register_blueprint(service_catalog_bp,       url_prefix='/api/service-catalog')
    app.register_blueprint(service_catalog_alias_bp, url_prefix='/api/service_catalog')
    app.register_blueprint(task_assignees_bp,  url_prefix='/api/task-assignees')
    app.register_blueprint(offers_bp,     url_prefix='/api/offers')
    app.register_blueprint(documents_bp,  url_prefix='/api/documents')
    app.register_blueprint(attachments_bp, url_prefix='/api/attachments')
    app.register_blueprint(document_types_bp, url_prefix='/api/document-types')
    app.register_blueprint(templates_bp,  url_prefix='/api/templates')
    app.register_blueprint(users_bp,      url_prefix='/api/users')
    app.register_blueprint(stats_bp,      url_prefix='/api/stats')
    app.register_blueprint(public_bp,     url_prefix='/api/public')
    app.register_blueprint(contacts_bp,   url_prefix='/api/contacts')
    from flask import Blueprint, abort

    branding_bp = Blueprint('branding', __name__)
    brand_dir = os.path.abspath(os.path.join(app.root_path, '..', 'uploads', 'branding'))
    os.makedirs(brand_dir, exist_ok=True)

    @branding_bp.route('/<path:filename>', methods=['GET'])
    def serve_branding_file(filename):
        if '..' in filename or filename.startswith('/'):
            abort(404)
        full = os.path.join(brand_dir, filename)
        if not os.path.exists(full):
            abort(404)
        return send_from_directory(brand_dir, filename)

    app.register_blueprint(branding_bp, url_prefix='/api/branding')
    app.register_blueprint(comments_bp,   url_prefix='/api/comments')
    app.register_blueprint(activities_bp, url_prefix='/api/activities')
    app.register_blueprint(avatars_bp,    url_prefix='/api/avatars')
    app.register_blueprint(archive_bp,    url_prefix='/api/archive')
    app.register_blueprint(settings_bp,   url_prefix='/api/settings')
    app.register_blueprint(sms_bp,        url_prefix='/api/sms')
    from ..api.custom_fields import custom_fields_bp
    from ..api.portal import portal_bp
    from ..api.emails import emails_bp
    app.register_blueprint(custom_fields_bp, url_prefix='/api/custom-fields')
    app.register_blueprint(portal_bp, url_prefix='/api/portal')
    app.register_blueprint(emails_bp, url_prefix='/api/emails')
