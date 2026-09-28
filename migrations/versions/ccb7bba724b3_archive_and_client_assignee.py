"""archive and client assignee (SQLite-safe)

Revision ID: ccb7bba724b3
Revises: 'e69d1dc06ace'
Create Date: 2026-09-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'ccb7bba724b3'
down_revision = 'e69d1dc06ace'
branch_labels = None
depends_on = None


def _has_column(table, column):
    bind = op.get_bind()
    insp = inspect(bind)
    try:
        cols = [c['name'] for c in insp.get_columns(table)]
        return column in cols
    except Exception:
        return False


def upgrade():
    # ── deleted_at do wszystkich tabel ──
    tables_with_deleted = [
        'clients', 'leads', 'contacts', 'tasks', 'meetings',
        'services', 'offers', 'documents',
    ]
    for tbl in tables_with_deleted:
        if not _has_column(tbl, 'deleted_at'):
            with op.batch_alter_table(tbl) as batch_op:
                batch_op.add_column(sa.Column('deleted_at', sa.DateTime(), nullable=True))

    # ── clients.assignee_id ──
    if not _has_column('clients', 'assignee_id'):
        with op.batch_alter_table('clients') as batch_op:
            batch_op.add_column(sa.Column('assignee_id', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('clients') as batch_op:
        if _has_column('clients', 'assignee_id'):
            batch_op.drop_column('assignee_id')

    for tbl in ['documents', 'offers', 'services', 'meetings',
                'tasks', 'contacts', 'leads', 'clients']:
        with op.batch_alter_table(tbl) as batch_op:
            if _has_column(tbl, 'deleted_at'):
                batch_op.drop_column('deleted_at')
