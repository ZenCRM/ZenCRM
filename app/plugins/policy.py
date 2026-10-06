"""Every invocation intersects administrator approval, user consent and record access."""
from flask import abort, current_app
from ..extensions import db
from ..models.user import User
from ..models.client import Client
from ..models.task import Task
from ..models.task_assignee import TaskAssignee
from ..utils.api_security import password_version
from .models import PluginApp, PluginGrant, PluginAudit
from ..models.setting import Setting
from .bundled import ALL_USERS, bundled_metadata

PLATFORM_SETTING = 'plugins_enabled'


def configured_enabled():
    value = Setting.get_value(PLATFORM_SETTING)
    return value == 'true' if value is not None else bool(current_app.config.get('PLUGINS_ENABLED', False))


def platform_enabled():
    return not current_app.config.get('PLUGINS_LOCKED', False) and configured_enabled()


def require_enabled():
    if not platform_enabled():
        abort(503, description='Aplikacje są wyłączone w ustawieniach systemu.')


def app_or_404(app_id):
    require_enabled()
    if not isinstance(app_id, str) or len(app_id) > 40:
        abort(400)
    app = db.session.get(PluginApp, app_id)
    if not app:
        abort(404)
    return app


def audience(app, user):
    all_users = ALL_USERS in app.allowed_users and bundled_metadata(app)['bundled']
    return bool(user and user.is_active and app.installed and app.enabled and (all_users or user.id in app.allowed_users))


def principal(grant_id, *, app_revision=None, grant_revision=None, version=None):
    require_enabled()
    grant = db.session.get(PluginGrant, grant_id)
    app = db.session.get(PluginApp, grant.app_id) if grant else None
    user = db.session.get(User, grant.user_id) if grant else None
    if not grant or not grant.active or not app or not audience(app, user):
        abort(403)
    if app_revision is not None and app.revision != app_revision:
        abort(401)
    if grant_revision is not None and grant.revision != grant_revision:
        abort(401)
    if version is not None and password_version(user) != version:
        abort(401)
    return app, grant, user


def require_scope(app, grant, scope):
    if scope not in app.approved_scopes or scope not in app.manifest['scopes'] or scope not in grant.scopes:
        abort(403)


def visible_clients(user):
    query = Client.query.filter(Client.deleted_at.is_(None))
    # Explicit narrow policy for integrations; do not inherit unrestricted core GETs.
    return query if user.role == 'admin' else query.filter(Client.assignee_id == user.id)


def visible_tasks(user):
    query = Task.query.filter(Task.deleted_at.is_(None))
    if user.role != 'admin':
        assigned = db.select(TaskAssignee.task_id).where(TaskAssignee.user_id == user.id)
        query = query.filter(db.or_(Task.assignee_id == user.id, Task.id.in_(assigned)))
    return query


def visible_report_records(user, entity):
    """Explicit owner/member policies; never forward unrestricted core collection APIs."""
    from ..models.lead import Lead
    from ..models.project import Project, ProjectMember
    from ..models.ticket import Ticket
    from ..models.document import Document
    from ..models.offer import Offer
    from ..models.service import Service
    from ..models.meeting import Meeting
    if entity == 'clients':
        return visible_clients(user)
    if entity == 'tasks':
        return visible_tasks(user)
    model = {'leads': Lead, 'projects': Project, 'tickets': Ticket, 'documents': Document,
             'offers': Offer, 'services': Service, 'meetings': Meeting}[entity]
    query = model.query
    if hasattr(model, 'deleted_at'):
        query = query.filter(model.deleted_at.is_(None))
    if user.role == 'admin':
        return query
    if entity == 'projects':
        members = db.select(ProjectMember.project_id).where(ProjectMember.user_id == user.id)
        return query.filter(db.or_(Project.manager_id == user.id, Project.id.in_(members)))
    if entity == 'services':
        return query.filter(Service.client_id.in_(visible_clients(user).with_entities(Client.id)))
    field = 'created_by' if entity in ('documents', 'offers') else 'organizer_id' if entity == 'meetings' else 'assignee_id'
    return query.filter(getattr(model, field) == user.id)


def audit(app_id, user_id, action):
    db.session.add(PluginAudit(app_id=app_id, user_id=user_id, action=action))
