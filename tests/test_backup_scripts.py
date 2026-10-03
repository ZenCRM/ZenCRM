"""Backup and restore scripts of the backup service, run against temporary directories."""
import os
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / 'backup'


@unittest.skipUnless(shutil.which('sqlite3') and shutil.which('tar'), 'sqlite3 and tar CLIs are required')
class BackupScriptsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.instance, self.uploads, self.backups = self.root / 'instance', self.root / 'uploads', self.root / 'backups'
        (self.instance / 'attachments').mkdir(parents=True)
        (self.instance / 'attachments' / 'contract.pdf').write_bytes(b'signed contract')
        (self.instance / 'portal_files').mkdir()
        (self.instance / 'portal_files' / 'brief.txt').write_text('portal file')
        (self.instance / 'zencrm.db.before-legacy.bak').write_bytes(b'pre-migration copy')
        (self.uploads / 'avatars').mkdir(parents=True)
        (self.uploads / 'avatars' / 'user_1.png').write_bytes(b'original avatar')
        self.write_rows('zencrm.db', ['Acme', 'Globex'])
        self.write_rows('security.sqlite', ['jwt-key'])
        self.env = {**os.environ, 'INSTANCE_DIR': str(self.instance), 'UPLOADS_DIR': str(self.uploads),
                    'BACKUP_DIR': str(self.backups), 'BACKUP_RETENTION': '3'}

    def tearDown(self):
        self.tmp.cleanup()

    def write_rows(self, name, values):
        conn = sqlite3.connect(self.instance / name)
        with conn:
            conn.execute('CREATE TABLE IF NOT EXISTS items (value TEXT)')
            conn.execute('DELETE FROM items')
            conn.executemany('INSERT INTO items VALUES (?)', [(value,) for value in values])
        conn.close()

    def read_rows(self, name):
        conn = sqlite3.connect(self.instance / name)
        try:
            return [row[0] for row in conn.execute('SELECT value FROM items ORDER BY value')]
        finally:
            conn.close()

    def run_script(self, name, *args, env=None):
        return subprocess.run(['sh', str(SCRIPTS / name), *args], env=env or self.env, capture_output=True, text=True)

    def backup(self):
        result = self.run_script('backup.sh')
        self.assertEqual(result.returncode, 0, result.stderr)
        archives = sorted(self.backups.glob('zencrm-*.tar.gz'))
        return archives[-1]

    def damage_current_data(self):
        self.write_rows('zencrm.db', ['Initech'])
        (self.instance / 'attachments' / 'contract.pdf').unlink()
        (self.uploads / 'avatars' / 'user_1.png').write_bytes(b'changed avatar')
        (self.uploads / 'stray.txt').write_text('added after the backup')

    def make_archive(self, build):
        staging = self.root / 'staging'
        (staging / 'instance').mkdir(parents=True)
        build(staging)
        archive = self.root / 'crafted.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            for name in sorted(os.listdir(staging)):
                tar.add(staging / name, arcname=name)
        return archive

    def test_archive_holds_instance_files_and_uploads_but_not_leftovers(self):
        archive = self.backup()
        self.assertEqual(archive.stat().st_mode & 0o077, 0)
        with tarfile.open(archive) as tar:
            names = set(tar.getnames())
        self.assertTrue({'instance/zencrm.db', 'instance/security.sqlite', 'instance/attachments/contract.pdf',
                         'instance/portal_files/brief.txt', 'uploads/avatars/user_1.png'} <= names)
        self.assertNotIn('instance/zencrm.db.before-legacy.bak', names)

    def test_backup_skips_interrupted_restore_staging(self):
        (self.uploads / '.restore-20260101-000000').mkdir()
        (self.uploads / '.restore-20260101-000000' / 'half.png').write_bytes(b'partial')
        with tarfile.open(self.backup()) as tar:
            self.assertFalse(any('.restore-' in name for name in tar.getnames()))

    def test_restore_brings_back_databases_keys_attachments_and_uploads(self):
        archive = self.backup()
        self.damage_current_data()
        result = self.run_script('restore.sh', str(archive))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_rows('zencrm.db'), ['Acme', 'Globex'])
        self.assertEqual(self.read_rows('security.sqlite'), ['jwt-key'])
        self.assertEqual((self.instance / 'attachments' / 'contract.pdf').read_bytes(), b'signed contract')
        self.assertEqual((self.uploads / 'avatars' / 'user_1.png').read_bytes(), b'original avatar')
        self.assertFalse((self.uploads / 'stray.txt').exists())
        replaced = list(self.instance.glob('replaced-*'))
        self.assertEqual(len(replaced), 1)
        self.assertTrue((replaced[0] / 'instance' / 'zencrm.db').exists())
        self.assertTrue((replaced[0] / 'uploads' / 'stray.txt').exists())
        self.assertEqual(list(self.instance.glob('.restore-*')) + list(self.uploads.glob('.restore-*')), [])
        self.assertTrue((self.instance / 'zencrm.db.before-legacy.bak').exists())

    def test_failed_swap_puts_the_previous_files_back(self):
        archive = self.backup()
        self.damage_current_data()
        shim = self.root / 'bin'
        shim.mkdir()
        (shim / 'mv').write_text('#!/bin/sh\ncase "$1" in */uploads/.restore-*/*) exit 1 ;; esac\nexec /bin/mv "$@"\n')
        (shim / 'mv').chmod(0o755)
        result = self.run_script('restore.sh', str(archive), env={**self.env, 'PATH': f'{shim}:{os.environ["PATH"]}'})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.read_rows('zencrm.db'), ['Initech'])
        self.assertFalse((self.instance / 'attachments' / 'contract.pdf').exists())
        self.assertEqual((self.uploads / 'stray.txt').read_text(), 'added after the backup')
        self.assertEqual(list(self.instance.glob('replaced-*')), [])
        self.assertEqual(list(self.instance.glob('.restore-*')) + list(self.uploads.glob('.restore-*')), [])

    def test_archive_without_keys_keeps_the_current_keys(self):
        def build(staging):
            shutil.copy(self.instance / 'zencrm.db', staging / 'instance' / 'zencrm.db')
        archive = self.make_archive(build)
        result = self.run_script('restore.sh', str(archive))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_rows('security.sqlite'), ['jwt-key'])

    def test_restore_refuses_archives_with_symbolic_links(self):
        def build(staging):
            shutil.copy(self.instance / 'zencrm.db', staging / 'instance' / 'zencrm.db')
            (staging / 'uploads').mkdir()
            os.symlink('/etc/passwd', staging / 'uploads' / 'link')
        result = self.run_script('restore.sh', str(self.make_archive(build)))
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.uploads / 'link').exists())

    def test_restore_refuses_a_damaged_database_and_keeps_current_data(self):
        def build(staging):
            (staging / 'instance' / 'zencrm.db').write_bytes(b'not a database')
        result = self.run_script('restore.sh', str(self.make_archive(build)))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.read_rows('zencrm.db'), ['Acme', 'Globex'])
        self.assertEqual(list(self.instance.glob('replaced-*')), [])

    def test_old_archives_beyond_retention_are_removed(self):
        self.backups.mkdir()
        for day in range(1, 6):
            (self.backups / f'zencrm-2026010{day}-020000.tar.gz').write_bytes(b'old')
        self.backup()
        kept = sorted(path.name for path in self.backups.glob('zencrm-*.tar.gz'))
        self.assertEqual(len(kept), 3)
        self.assertEqual(kept[:2], ['zencrm-20260104-020000.tar.gz', 'zencrm-20260105-020000.tar.gz'])

    def test_backup_fails_without_a_database(self):
        (self.instance / 'zencrm.db').unlink()
        result = self.run_script('backup.sh')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(list(self.backups.glob('zencrm-*.tar.gz')) if self.backups.exists() else [], [])


if __name__ == '__main__':
    unittest.main()
