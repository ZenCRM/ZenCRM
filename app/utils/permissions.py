"""Action permissions for CRM records. Admin is always unrestricted."""
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request

from ..extensions import db
from ..models.permission import Role, PermissionRule
from ..utils.deletion import current_user

BUILTIN_ROLES = {'admin': 'Administrator', 'manager': 'Manager', 'employee': 'Pracownik'}
MODULES = {
    'clients': 'Klienci', 'leads': 'Leady', 'contacts': 'Kontakty',
    'tasks': 'Zadania', 'meetings': 'Spotkania', 'projects': 'Projekty',
    'services': 'Usługi', 'service_catalog': 'Katalog usług',
    'offers': 'Oferty', 'documents': 'Dokumenty',
    'templates': 'Szablony', 'tickets': 'Zgłoszenia',
}
ACTIONS = {'create': 'Dodawanie', 'edit': 'Edycja', 'delete': 'Przenoszenie do archiwum'}
PERMISSIONS = {f'{module}.{action}': f'{label} · {action_label}'
               for module, label in MODULES.items() for action, action_label in ACTIONS.items()}
PERMISSIONS['archive.restore'] = 'Archiwum · przywracanie'

ENDPOINT_ACTIONS = {}
for _module in MODULES:
    _names = ('create_item', 'update_item', 'delete_item')
    if _module == 'projects':
        _names = ('create_project', 'update_project', 'delete_project')
    if _module == 'tickets':
        _names = ('create_ticket', 'update_ticket', 'delete_ticket')
    for _name, _action in zip(_names, ACTIONS):
        ENDPOINT_ACTIONS[f'{_module}.{_name}'] = f'{_module}.{_action}'
ENDPOINT_ACTIONS.update({
    'archive.restore_item': 'archive.restore',
    'clients.restore_item': 'archive.restore',
    'leads.restore_item': 'archive.restore',
    'contacts.restore_item': 'archive.restore',
    'services.restore_item': 'archive.restore',
    'service_catalog.restore_item': 'archive.restore',
    'leads.convert_lead': 'leads.edit',
    'projects.add_member': 'projects.edit',
    'projects.remove_member': 'projects.edit',
    'projects.update_project_stages': 'projects.edit',
    'tickets.add_agent_message': 'tickets.edit',
    'task_assignees.set_assignees': 'tasks.edit',
    'task_assignees.update_assignee': 'tasks.edit',
    'task_assignees.remove_assignee': 'tasks.edit',
    'documents.generate_document': 'documents.edit',
    'documents.share_link': 'documents.edit',
    'offers.generate_offer': 'offers.edit',
    'offers.share_link': 'offers.edit',
    'service_catalog_alias.alias_create': 'service_catalog.create',
    'service_catalog_alias.alias_update': 'service_catalog.edit',
    'service_catalog_alias.alias_delete': 'service_catalog.delete',
})


def ensure_builtin_roles():
    for key, name in BUILTIN_ROLES.items():
        if db.session.get(Role, key) is None:
            db.session.add(Role(key=key, name=name, built_in=True))
    db.session.flush()


def has_permission(user, permission):
    if not user or not user.is_active or permission not in PERMISSIONS:
        return False
    if user.role == 'admin':
        return True
    role = PermissionRule.query.filter_by(role_key=user.role, permission=permission).first()
    allowed = role.allowed if role else user.role in ('manager', 'employee')
    team_ids = [team.id for team in user.teams]
    if team_ids:
        team_rules = PermissionRule.query.filter(
            PermissionRule.team_id.in_(team_ids), PermissionRule.permission == permission).all()
        if any(not rule.allowed for rule in team_rules):
            return False
        if any(rule.allowed for rule in team_rules):
            return True
    return allowed


def effective_permissions(user):
    if not user or not user.is_active:
        return {key: False for key in PERMISSIONS}
    if user.role == 'admin':
        return {key: True for key in PERMISSIONS}
    role_rules = {rule.permission: rule.allowed for rule in PermissionRule.query.filter_by(role_key=user.role).all()}
    team_ids = [team.id for team in user.teams]
    team_rules = PermissionRule.query.filter(PermissionRule.team_id.in_(team_ids)).all() if team_ids else []
    result = {}
    for key in PERMISSIONS:
        value = role_rules.get(key, user.role in ('manager', 'employee'))
        matching = [rule.allowed for rule in team_rules if rule.permission == key]
        result[key] = False if False in matching else True if True in matching else value
    return result


def guard_action():
    permission = ENDPOINT_ACTIONS.get(request.endpoint)
    if not permission or request.method == 'OPTIONS':
        return None
    verify_jwt_in_request()
    if not has_permission(current_user(), permission):
        return jsonify({'error': 'Brak uprawnienia do tej operacji'}), 403
    return None
