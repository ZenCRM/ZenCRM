"""lead assignee + idempotentne dodanie kolumn (SQLite-safe)

Revision ID: e69d1dc06ace
Revises: '260e3ed4c5ce'
Create Date: 2026-09-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'e69d1dc06ace'
down_revision = '260e3ed4c5ce'
branch_labels = None
depends_on = None


def _has_column(table, column):
    """Sprawdza, czy kolumna już istnieje (idempotentne)."""
    bind = op.get_bind()
    insp = inspect(bind)
    try:
        cols = [c['name'] for c in insp.get_columns(table)]
        return column in cols
    except Exception:
        return False


def upgrade():
    # ── leads.assignee_id (NOWE) ──
    if not _has_column('leads', 'assignee_id'):
        with op.batch_alter_table('leads') as batch_op:
            batch_op.add_column(sa.Column('assignee_id', sa.Integer(), nullable=True))

    # ── leads.converted_to_client_id (jeśli brakuje) ──
    if not _has_column('leads', 'converted_to_client_id'):
        with op.batch_alter_table('leads') as batch_op:
            batch_op.add_column(sa.Column('converted_to_client_id', sa.Integer(), nullable=True))

    # ── documents.lead_id (jeśli brakuje) ──
    if not _has_column('documents', 'lead_id'):
        with op.batch_alter_table('documents') as batch_op:
            batch_op.add_column(sa.Column('lead_id', sa.Integer(), nullable=True))

    # ── tasks.lead_id (jeśli brakuje) ──
    if not _has_column('tasks', 'lead_id'):
        with op.batch_alter_table('tasks') as batch_op:
            batch_op.add_column(sa.Column('lead_id', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('tasks') as batch_op:
        if _has_column('tasks', 'lead_id'):
            batch_op.drop_column('lead_id')
    with op.batch_alter_table('documents') as batch_op:
        if _has_column('documents', 'lead_id'):
            batch_op.drop_column('lead_id')
    with op.batch_alter_table('leads') as batch_op:
        if _has_column('leads', 'converted_to_client_id'):
            batch_op.drop_column('converted_to_client_id')
        if _has_column('leads', 'assignee_id'):
            batch_op.drop_column('assignee_id')
