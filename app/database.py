"""Database schema preparation: Alembic migrations plus a one-time bridge for older installations."""
import logging
import sqlite3
from contextlib import contextmanager
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None

try:
    import msvcrt
except ImportError:
    msvcrt = None

from alembic.script import ScriptDirectory
from flask import current_app
from flask_migrate import upgrade
from sqlalchemy import event, inspect, text
from sqlalchemy.engine import Engine

from .extensions import db

MIGRATIONS_DIR = str(Path(__file__).resolve().parent.parent / 'migrations')
# Revisions of the migration chain replaced by 0001_baseline; databases stamped with them are upgraded
# like installations that never ran migrations.
REMOVED_REVISIONS = frozenset({
    '1a4521a23b68', '20260927_notes', '20260928_meeting_lead', '20260928_merge_heads',
    '20260928_phone_call_note', '20260928_reminder_link', '20260928_reminders',
    '20260928_roles_permissions', '20260929_attachments', '20260929_document_types', '260e3ed4c5ce',
    '3ee44d0cd943', '4ed6a32508a7', '557674edde6b', 'a9cef9f2b9c6', 'ccb7bba724b3', 'db1fd8fa5d98',
    'e69d1dc06ace', 'f0578c6694b6',
})

# Columns that installations created before Alembic was used may lack. Their tables were built by
# create_all at some earlier version and patched by these statements on start (SQLite syntax).
LEGACY_COLUMNS = (
    ('translation_languages', 'base_locale', "VARCHAR(16) NOT NULL DEFAULT 'pl'"),
    ('attachments', 'created_by_id', 'INTEGER'),
    ('templates', 'document_type_key', 'VARCHAR(50)'),
    ('tasks', 'project_id', 'INTEGER'),
    ('meetings', 'lead_id', 'INTEGER'),
    ('custom_fields', 'required', 'BOOLEAN DEFAULT 0'),
    ('sms_devices', 'user_id', 'INTEGER REFERENCES users(id)'),
    ('sms_devices', 'last_sync_at', 'DATETIME'),
    ('sms_devices', 'sync_from', 'DATETIME'),
    ('sms_queue', 'action', "VARCHAR(50) DEFAULT 'send_sms'"),
    ('sms_queue', 'payload', 'TEXT'),
    ('sms_queue', 'client_id', 'INTEGER'),
    ('sms_queue', 'user_id', 'INTEGER'),
    ('sms_queue', 'error_message', 'TEXT'),
    ('sms_queue', 'sent_at', 'DATETIME'),
    ('phone_calls', 'call_time', 'DATETIME'),
    ('phone_calls', 'client_id', 'INTEGER'),
    ('phone_calls', 'note', 'TEXT'),
    ('sms_messages', 'message_time', 'DATETIME'),
    ('sms_messages', 'client_id', 'INTEGER'),
    ('users', 'default_call_method', "VARCHAR(20) DEFAULT 'link'"),
    ('users', 'email_notifications', "TEXT DEFAULT '{}'"),
    ('contacts', 'is_primary', 'BOOLEAN DEFAULT 0'),
)

logger = logging.getLogger('zencrm.database')


@event.listens_for(Engine, 'connect')
def configure_sqlite_connection(dbapi_connection, _connection_record):
    """Enforce foreign keys and wait for locks instead of failing under concurrent workers."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA busy_timeout=5000')
        cursor.close()


def prepare_database():
    """Bring the schema to the latest revision and seed default records. Requires an app context."""
    with _schema_lock():
        script = ScriptDirectory(MIGRATIONS_DIR)
        head = script.get_current_head()
        tables = set(inspect(db.engine).get_table_names())
        versions = _current_revisions(tables)
        known = {revision.revision for revision in script.walk_revisions()}
        unknown = set(versions) - known - REMOVED_REVISIONS
        if unknown:
            raise RuntimeError(f'Database revision {", ".join(sorted(unknown))} is newer than this application; '
                               'deploy a release that includes it instead of downgrading.')
        legacy = bool(tables - {'alembic_version'}) and (not versions or set(versions) <= REMOVED_REVISIONS)
        if legacy or (tables and versions != [head]):
            _backup_sqlite(versions[0] if versions else 'legacy')
        if legacy:
            _bridge_legacy_schema(tables)
        upgrade(directory=MIGRATIONS_DIR)
        if legacy:
            _report_orphans()
        _seed_defaults()


@contextmanager
def _schema_lock():
    """Serialise schema changes when several processes start at once."""
    url = db.engine.url
    backend = url.get_backend_name()
    if backend == 'sqlite' and url.database and url.database != ':memory:' and (fcntl or msvcrt):
        with open(f'{url.database}.migrate.lock', 'a+b') as handle:
            if fcntl:
                fcntl.flock(handle, fcntl.LOCK_EX)
            else:
                # Windows can lock beyond EOF. Never write before acquiring the lock:
                # another starter may already hold byte zero of this initially empty file.
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                if fcntl:
                    fcntl.flock(handle, fcntl.LOCK_UN)
                else:
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    elif backend in ('mysql', 'mariadb', 'postgresql'):
        acquire, release = {
            'postgresql': ('SELECT pg_advisory_lock(80412)', 'SELECT pg_advisory_unlock(80412)'),
        }.get(backend, ("SELECT GET_LOCK('zencrm_schema', 600)", "SELECT RELEASE_LOCK('zencrm_schema')"))
        with db.engine.connect() as conn:
            if conn.execute(text(acquire)).scalar() == 0:
                raise RuntimeError('Timed out waiting for another process to finish migrating the database')
            try:
                yield
            finally:
                conn.execute(text(release))
    else:
        yield


def _current_revisions(tables):
    if 'alembic_version' not in tables:
        return []
    with db.engine.connect() as conn:
        return [row[0] for row in conn.execute(text('SELECT version_num FROM alembic_version'))]


def _backup_sqlite(label):
    """Copy a SQLite database before migrating it; SQLite DDL cannot be rolled back if a migration fails."""
    url = db.engine.url
    if url.get_backend_name() != 'sqlite' or not url.database or url.database == ':memory:':
        return
    target = f'{url.database}.before-{label}.bak'
    source = sqlite3.connect(url.database)
    try:
        with sqlite3.connect(target) as copy:
            source.backup(copy)
    finally:
        source.close()
    logger.warning('Backed up the database to %s before migrating', target)


def _bridge_legacy_schema(tables):
    """Add columns older installations lack, then let the baseline create any missing tables."""
    logger.warning('Upgrading a database created before Alembic migrations')
    with db.engine.begin() as conn:
        inspector = inspect(conn)
        for table, column, definition in LEGACY_COLUMNS:
            if table in tables and column not in {c['name'] for c in inspector.get_columns(table)}:
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {definition}'))
        if 'alembic_version' in tables:
            conn.execute(text('DELETE FROM alembic_version'))


def _report_orphans():
    """Rows left dangling while SQLite did not enforce foreign keys; deletes involving them may now fail."""
    if db.engine.url.get_backend_name() != 'sqlite':
        return
    with db.engine.connect() as conn:
        orphans = conn.execute(text('PRAGMA foreign_key_check')).fetchall()
    if orphans:
        counts = {}
        for table, *_ in orphans:
            counts[table] = counts.get(table, 0) + 1
        logger.warning('Rows referencing missing records: %s', counts)


def _seed_defaults():
    from .utils.secret_storage import migrate_smtp_password
    migrate_smtp_password()
    from .models.document_type import DocumentType
    from .models.email_template import EmailTemplate
    from .plugins.bundled import seed_bundled
    seed_bundled()
    DocumentType.seed_defaults()
    try:
        EmailTemplate.seed_defaults()
    except Exception:
        current_app.logger.exception('Seeding default email templates failed')
