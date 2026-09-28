"""service assignees (JSON)

Revision ID: a9cef9f2b9c6
Revises: 557674edde6b
Create Date: 2026-09-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'a9cef9f2b9c6'
down_revision = '557674edde6b'
branch_labels = None
depends_on = None


def _has_column(table, column):
    insp = inspect(op.get_bind())
    try:
        return column in [c['name'] for c in insp.get_columns(table)]
    except Exception:
        return False


def upgrade():
    if not _has_column('services', 'assignee_ids'):
        with op.batch_alter_table('services') as b:
            b.add_column(sa.Column('assignee_ids', sa.JSON(), nullable=True))


def downgrade():
    if _has_column('services', 'assignee_ids'):
        with op.batch_alter_table('services') as b:
            b.drop_column('assignee_ids')
