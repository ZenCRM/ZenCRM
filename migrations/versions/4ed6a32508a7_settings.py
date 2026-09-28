"""settings table

Revision ID: 4ed6a32508a7
Revises: f0578c6694b6
Create Date: 2026-09-24
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = '4ed6a32508a7'
down_revision = 'f0578c6694b6'
branch_labels = None
depends_on = None


def _table_exists(name):
    insp = inspect(op.get_bind())
    return name in insp.get_table_names()


def upgrade():
    if not _table_exists('settings'):
        op.create_table(
            'settings',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('key', sa.String(100), nullable=False, unique=True),
            sa.Column('value', sa.Text()),
            sa.Column('category', sa.String(50), default='general'),
            sa.Column('updated_at', sa.DateTime()),
        )
        op.create_index('ix_settings_key', 'settings', ['key'], unique=True)


def downgrade():
    if _table_exists('settings'):
        op.drop_index('ix_settings_key', table_name='settings')
        op.drop_table('settings')
