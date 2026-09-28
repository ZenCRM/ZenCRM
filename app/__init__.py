import os
import sys
from pathlib import Path

# Ensure project venv site-packages are accessible even if run from another Python interpreter
_proj_root = Path(__file__).resolve().parent.parent
_venv_lib = _proj_root / 'venv' / ('Lib' if os.name == 'nt' else 'lib')
if _venv_lib.is_dir():
    for _sp in _venv_lib.glob('**/site-packages'):
        if _sp.is_dir() and str(_sp) not in sys.path:
            sys.path.insert(0, str(_sp))

from flask import Flask, send_from_directory, render_template
try:
    from flask_cors import CORS
except ImportError:
    class CORS:
        def __init__(self, *args, **kwargs):
            pass

from .extensions import db, migrate, jwt, ma
from .config import Config


def create_app(config_class=Config):
    frontend_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='', template_folder=frontend_dir)
    app.config.from_object(config_class)
    # Distinct delimiters preserve the Jinja examples in the document editor.
    app.jinja_env.block_start_string = '<%'
    app.jinja_env.block_end_string = '%>'
    app.jinja_env.variable_start_string = '[['
    app.jinja_env.variable_end_string = ']]'

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    ma.init_app(app)
    CORS(app, resources={r'/api/*': {'origins': '*'}})

    from .models import (user, client, lead, task, meeting, service,
                         template, offer, document, contact, comment, activity,
                         service_catalog, task_assignee, setting, sms, workspace, project, team, ticket, permission)

    from .api.push import push_bp
    app.register_blueprint(push_bp, url_prefix="/api/push")

    from .api.reminders import reminders_bp
    app.register_blueprint(reminders_bp, url_prefix='/api/reminders')

    from .api.notifications import notifications_bp
    app.register_blueprint(notifications_bp, url_prefix='/api/notifications')

    from .api.auth       import auth_bp
    from .api.clients    import clients_bp
    from .api.leads      import leads_bp
    from .api.tasks      import tasks_bp
    from .api.meetings   import meetings_bp
    from .api.services   import services_bp
    from .api.service_catalog import service_catalog_bp, service_catalog_alias_bp
    from .api.task_assignees  import task_assignees_bp
    from .api.offers     import offers_bp
    from .api.documents  import documents_bp
    from .api.templates  import templates_bp
    from .api.users      import users_bp
    from .api.stats      import stats_bp
    from .api.public     import public_bp
    from .api.contacts   import contacts_bp
    from .api.comments   import comments_bp
    from .api.activities import activities_bp
    from .api.avatars    import avatars_bp
    from .api.archive    import archive_bp
    from .api.settings   import settings_bp
    from .api.sms        import sms_bp
    from .api.projects   import projects_bp
    from .api.teams      import teams_bp
    from .api.tickets    import tickets_bp
    from .api.permissions import permissions_bp

    from .utils.permissions import guard_action
    app.before_request(guard_action)

    app.register_blueprint(auth_bp,       url_prefix='/api/auth')
    app.register_blueprint(clients_bp,    url_prefix='/api/clients')
    app.register_blueprint(leads_bp,      url_prefix='/api/leads')
    app.register_blueprint(tasks_bp,      url_prefix='/api/tasks')
    app.register_blueprint(projects_bp,   url_prefix='/api/projects')
    app.register_blueprint(teams_bp,      url_prefix='/api/teams')
    app.register_blueprint(permissions_bp, url_prefix='/api/permissions')
    app.register_blueprint(tickets_bp,    url_prefix='/api/tickets')
    app.register_blueprint(meetings_bp,   url_prefix='/api/meetings')
    app.register_blueprint(services_bp,   url_prefix='/api/services')
    app.register_blueprint(service_catalog_bp,       url_prefix='/api/service-catalog')
    app.register_blueprint(service_catalog_alias_bp, url_prefix='/api/service_catalog')
    app.register_blueprint(task_assignees_bp,  url_prefix='/api/task-assignees')
    app.register_blueprint(offers_bp,     url_prefix='/api/offers')
    app.register_blueprint(documents_bp,  url_prefix='/api/documents')
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
    from .api.custom_fields import custom_fields_bp
    from .api.portal import portal_bp
    from .api.emails import emails_bp
    app.register_blueprint(custom_fields_bp, url_prefix='/api/custom-fields')
    app.register_blueprint(portal_bp, url_prefix='/api/portal')
    app.register_blueprint(emails_bp, url_prefix='/api/emails')


    @app.before_request
    def serve_portal_address():
        from flask import request
        from .utils.portal import portal_path
        from .utils.helpdesk import helpdesk_path
        path = request.path.rstrip('/')
        if request.method in ('GET', 'HEAD') and path and not path.startswith('/api/') and '.' not in path:
            if path == portal_path():
                return send_from_directory(frontend_dir, 'portal.html')
            if path == helpdesk_path():
                return send_from_directory(frontend_dir, 'helpdesk.html')

    @app.route('/')
    @app.route('/index.html')
    def index():
        return render_template('index.html')

    @app.route('/<path:path>')
    def static_files(path):
        full = os.path.join(frontend_dir, path)
        if os.path.exists(full):
            return send_from_directory(frontend_dir, path)
        return render_template('index.html')

    from .models import (user, client, lead, task, meeting, service,
                         template, offer, document, contact, comment, activity,
                         service_catalog, task_assignee, setting, sms, workspace, project, team, ticket, email_template)

    with app.app_context():
        db.create_all()
        try:
            with db.engine.connect() as conn:
                # tasks migrations
                res_t = conn.execute(db.text("PRAGMA table_info(tasks)")).fetchall()
                cols_t = [r[1] for r in res_t] if res_t else []
                if cols_t and 'project_id' not in cols_t:
                    conn.execute(db.text("ALTER TABLE tasks ADD COLUMN project_id INTEGER"))
                    conn.commit()

                res_meetings = conn.execute(db.text("PRAGMA table_info(meetings)")).fetchall()
                cols_meetings = [r[1] for r in res_meetings] if res_meetings else []
                if cols_meetings and 'lead_id' not in cols_meetings:
                    conn.execute(db.text("ALTER TABLE meetings ADD COLUMN lead_id INTEGER"))
                    conn.commit()

                # custom_fields migrations
                res_cf = conn.execute(db.text("PRAGMA table_info(custom_fields)")).fetchall()
                cols_cf = [r[1] for r in res_cf] if res_cf else []
                if cols_cf and 'required' not in cols_cf:
                    conn.execute(db.text("ALTER TABLE custom_fields ADD COLUMN required BOOLEAN DEFAULT 0"))
                    conn.commit()

                # sms_devices migrations
                res = conn.execute(db.text("PRAGMA table_info(sms_devices)")).fetchall()
                cols = [r[1] for r in res] if res else []
                if cols and 'last_sync_at' not in cols:
                    conn.execute(db.text("ALTER TABLE sms_devices ADD COLUMN last_sync_at DATETIME"))
                    conn.commit()
                if cols and 'sync_from' not in cols:
                    conn.execute(db.text("ALTER TABLE sms_devices ADD COLUMN sync_from DATETIME"))
                    conn.commit()

                # sms_queue migrations
                res_q = conn.execute(db.text("PRAGMA table_info(sms_queue)")).fetchall()
                cols_q = [r[1] for r in res_q] if res_q else []
                if cols_q and 'action' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN action VARCHAR(50) DEFAULT 'send_sms'"))
                    conn.commit()
                if cols_q and 'payload' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN payload TEXT"))
                    conn.commit()
                if cols_q and 'client_id' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN client_id INTEGER"))
                    conn.commit()
                if cols_q and 'user_id' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN user_id INTEGER"))
                    conn.commit()
                if cols_q and 'error_message' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN error_message TEXT"))
                    conn.commit()
                if cols_q and 'sent_at' not in cols_q:
                    conn.execute(db.text("ALTER TABLE sms_queue ADD COLUMN sent_at DATETIME"))
                    conn.commit()

                # phone_calls migrations
                res_c = conn.execute(db.text("PRAGMA table_info(phone_calls)")).fetchall()
                cols_c = [r[1] for r in res_c] if res_c else []
                if cols_c and 'call_time' not in cols_c:
                    conn.execute(db.text("ALTER TABLE phone_calls ADD COLUMN call_time DATETIME"))
                    conn.commit()
                if cols_c and 'client_id' not in cols_c:
                    conn.execute(db.text("ALTER TABLE phone_calls ADD COLUMN client_id INTEGER"))
                    conn.commit()
                if cols_c and 'note' not in cols_c:
                    conn.execute(db.text("ALTER TABLE phone_calls ADD COLUMN note TEXT"))
                    conn.commit()

                # sms_messages migrations
                res_m = conn.execute(db.text("PRAGMA table_info(sms_messages)")).fetchall()
                cols_m = [r[1] for r in res_m] if res_m else []
                if cols_m and 'message_time' not in cols_m:
                    conn.execute(db.text("ALTER TABLE sms_messages ADD COLUMN message_time DATETIME"))
                    conn.commit()
                if cols_m and 'client_id' not in cols_m:
                    conn.execute(db.text("ALTER TABLE sms_messages ADD COLUMN client_id INTEGER"))
                    conn.commit()

                # users migrations
                res_u = conn.execute(db.text("PRAGMA table_info(users)")).fetchall()
                cols_u = [r[1] for r in res_u] if res_u else []
                if cols_u and 'default_call_method' not in cols_u:
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN default_call_method VARCHAR(20) DEFAULT 'link'"))
                    conn.commit()
                if cols_u and 'email_notifications' not in cols_u:
                    conn.execute(db.text("ALTER TABLE users ADD COLUMN email_notifications TEXT DEFAULT '{}'"))
                    conn.commit()

                # contacts migrations
                res_cnt = conn.execute(db.text("PRAGMA table_info(contacts)")).fetchall()
                cols_cnt = [r[1] for r in res_cnt] if res_cnt else []
                if cols_cnt and 'is_primary' not in cols_cnt:
                    conn.execute(db.text("ALTER TABLE contacts ADD COLUMN is_primary BOOLEAN DEFAULT 0"))
                    conn.commit()
        except Exception:
            pass

        try:
            email_template.EmailTemplate.seed_defaults()
        except Exception:
            pass

    from .services.push_service import start_push_worker
    start_push_worker(app)

    return app
