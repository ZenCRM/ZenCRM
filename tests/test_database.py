import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from app import create_app
from app.config import Config
from app.database import MIGRATIONS_DIR, prepare_database
from app.extensions import db


class DatabasePreparationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        database_path = Path(self.tmp.name) / 'zencrm.db'

        class TestConfig(Config):
            TESTING = True
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{database_path}'
            JWT_SECRET_KEY = 'database-test-key-with-at-least-32-bytes'
            PUSH_ENABLED = False
            PREPARE_DATABASE = False
        self.app = create_app(TestConfig)
        self.ctx = self.app.app_context()
        self.ctx.push()
        self.head = ScriptDirectory(MIGRATIONS_DIR).get_current_head()

    def tearDown(self):
        db.session.remove()
        db.engine.dispose()
        self.ctx.pop()
        self.tmp.cleanup()

    def version(self):
        with db.engine.connect() as conn:
            return conn.execute(text('SELECT version_num FROM alembic_version')).scalar()

    def columns(self, table):
        return {column['name'] for column in inspect(db.engine).get_columns(table)}

    def create_legacy_schema(self):
        """Tables as create_all built them before migrations: without what revision 0002 adds."""
        db.create_all()
        with db.engine.begin() as conn:
            conn.execute(text('DROP INDEX ix_sms_queue_status'))
            conn.execute(text('ALTER TABLE sms_queue DROP COLUMN claimed_at'))

    def test_migrations_match_models(self):
        prepare_database()
        self.assertEqual(self.version(), self.head)
        with db.engine.connect() as conn:
            diff = compare_metadata(MigrationContext.configure(conn), db.metadata)
        self.assertEqual(diff, [])

    def test_installation_from_before_migrations_is_upgraded_and_stamped(self):
        self.create_legacy_schema()
        with db.engine.begin() as conn:
            conn.execute(text('ALTER TABLE contacts DROP COLUMN is_primary'))
            conn.execute(text('DROP TABLE ticket_messages'))
        prepare_database()
        self.assertEqual(self.version(), self.head)
        self.assertIn('is_primary', self.columns('contacts'))
        self.assertIn('claimed_at', self.columns('sms_queue'))
        self.assertIn('ticket_messages', inspect(db.engine).get_table_names())

    def test_legacy_installation_missing_a_table_reaches_head(self):
        self.create_legacy_schema()
        with db.engine.begin() as conn:
            conn.execute(text('DROP TABLE sms_queue'))
        prepare_database()
        prepare_database()
        self.assertEqual(self.version(), self.head)
        self.assertIn('claimed_at', self.columns('sms_queue'))

    def test_unknown_newer_revision_is_left_untouched(self):
        prepare_database()
        with db.engine.begin() as conn:
            conn.execute(text("UPDATE alembic_version SET version_num = '9999_future'"))
        with self.assertRaises(RuntimeError):
            prepare_database()
        self.assertEqual(self.version(), '9999_future')

    def test_sqlite_database_is_backed_up_before_migrating(self):
        self.create_legacy_schema()
        prepare_database()
        backups = list(Path(self.tmp.name).glob('zencrm.db.before-*.bak'))
        self.assertEqual(len(backups), 1)

    def test_concurrent_preparation_converges(self):
        self.create_legacy_schema()
        db.engine.dispose()
        script = (
            'import sys\n'
            'from app import create_app\n'
            'from app.config import Config\n'
            'class C(Config):\n'
            '    SQLALCHEMY_DATABASE_URI = sys.argv[1]\n'
            '    JWT_SECRET_KEY = "concurrency-test-key-with-at-least-32-bytes"\n'
            '    PUSH_ENABLED = False\n'
            'create_app(C)\n'
        )
        url = self.app.config['SQLALCHEMY_DATABASE_URI']
        root = Path(__file__).resolve().parent.parent
        workers = [subprocess.Popen([sys.executable, '-c', script, url], cwd=root,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.PIPE) for _ in range(4)]
        errors = [worker.communicate(timeout=120)[1].decode() for worker in workers]
        self.assertEqual([worker.returncode for worker in workers], [0] * 4, errors)
        self.assertEqual(self.version(), self.head)
        self.assertIn('claimed_at', self.columns('sms_queue'))
        with db.engine.connect() as conn:
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM plugin_apps')).scalar(), 3)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM plugin_grants')).scalar(), 0)

    def test_revision_from_removed_migration_chain_is_replaced(self):
        self.create_legacy_schema()
        with db.engine.begin() as conn:
            conn.execute(text('CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)'))
            conn.execute(text("INSERT INTO alembic_version VALUES ('20260929_document_types')"))
        prepare_database()
        self.assertEqual(self.version(), self.head)
        self.assertIn('claimed_at', self.columns('sms_queue'))

    def test_preparation_is_idempotent_and_seeds_defaults(self):
        prepare_database()
        prepare_database()
        self.assertEqual(self.version(), self.head)
        with db.engine.connect() as conn:
            self.assertGreater(conn.execute(text('SELECT COUNT(*) FROM document_types')).scalar(), 0)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM plugin_apps')).scalar(), 3)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM plugin_grants')).scalar(), 0)
            self.assertEqual(conn.execute(text('SELECT COUNT(*) FROM plugin_tokens')).scalar(), 0)

    def test_sqlite_connections_enforce_foreign_keys(self):
        prepare_database()
        with db.engine.connect() as conn:
            self.assertEqual(conn.execute(text('PRAGMA foreign_keys')).scalar(), 1)


if __name__ == '__main__':
    unittest.main()
