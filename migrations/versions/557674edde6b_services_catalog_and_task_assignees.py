"""services catalog and task assignees (SQLite-safe)

Revision ID: 557674edde6b
Revises: 'ccb7bba724b3'
Create Date: 2026-09-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '557674edde6b'
down_revision = 'ccb7bba724b3'
branch_labels = None
depends_on = None


def _table_exists(name):
    bind = op.get_bind()
    insp = inspect(bind)
    return name in insp.get_table_names()


def _has_column(table, column):
    bind = op.get_bind()
    insp = inspect(bind)
    try:
        cols = [c['name'] for c in insp.get_columns(table)]
        return column in cols
    except Exception:
        return False


def upgrade():
    # ── NOWE TABELE ──

    # service_catalog
    if not _table_exists('service_catalog'):
        op.create_table(
            'service_catalog',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('name', sa.String(200), nullable=False),
            sa.Column('description', sa.Text()),
            sa.Column('billing_type', sa.String(20), default='subscription'),
            sa.Column('term_type', sa.String(20), default='indefinite'),
            sa.Column('default_billing_cycle', sa.String(20), default='monthly'),
            sa.Column('default_price', sa.Numeric(10, 2)),
            sa.Column('is_price_fixed', sa.Boolean(), default=True),
            sa.Column('content', sa.Text()),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('deleted_at', sa.DateTime()),
            sa.Column('created_at', sa.DateTime()),
            sa.Column('updated_at', sa.DateTime()),
        )

    # task_assignees
    if not _table_exists('task_assignees'):
        op.create_table(
            'task_assignees',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('task_id', sa.Integer(), sa.ForeignKey('tasks.id'), nullable=False),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('status', sa.String(20), default='pending'),
            sa.Column('comment', sa.Text()),
            sa.Column('updated_at', sa.DateTime()),
            sa.Column('created_at', sa.DateTime()),
        )

    # ── NOWE KOLUMNY – TASKS ──
    if not _has_column('tasks', 'service_id'):
        with op.batch_alter_table('tasks') as batch_op:
            batch_op.add_column(sa.Column('service_id', sa.Integer(), nullable=True))

    # ── NOWE KOLUMNY – DOCUMENTS ──
    if not _has_column('documents', 'service_id'):
        with op.batch_alter_table('documents') as batch_op:
            batch_op.add_column(sa.Column('service_id', sa.Integer(), nullable=True))

    # ── NOWE KOLUMNY – SERVICES ──
    with op.batch_alter_table('services') as batch_op:
        if not _has_column('services', 'catalog_id'):
            batch_op.add_column(sa.Column('catalog_id', sa.Integer(), nullable=True))
        if not _has_column('services', 'billing_type'):
            batch_op.add_column(sa.Column('billing_type', sa.String(20), server_default='subscription'))
        if not _has_column('services', 'term_type'):
            batch_op.add_column(sa.Column('term_type', sa.String(20), server_default='indefinite'))
        if not _has_column('services', 'risk_level'):
            batch_op.add_column(sa.Column('risk_level', sa.Integer(), nullable=True))
        if not _has_column('services', 'notes'):
            batch_op.add_column(sa.Column('notes', sa.Text()))
        if not _has_column('services', 'updated_at'):
            batch_op.add_column(sa.Column('updated_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('services') as batch_op:
        for col in ['updated_at', 'notes', 'risk_level', 'term_type', 'billing_type', 'catalog_id']:
            if _has_column('services', col):
                batch_op.drop_column(col)

    with op.batch_alter_table('documents') as batch_op:
        if _has_column('documents', 'service_id'):
            batch_op.drop_column('service_id')

    with op.batch_alter_table('tasks') as batch_op:
        if _has_column('tasks', 'service_id'):
            batch_op.drop_column('service_id')

    if _table_exists('task_assignees'):
        op.drop_table('task_assignees')
    if _table_exists('service_catalog'):
        op.drop_table('service_catalog')
