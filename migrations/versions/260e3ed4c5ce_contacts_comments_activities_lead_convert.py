"""contacts_comments_activities_lead_convert

Revision ID: 260e3ed4c5ce
Revises: 3ee44d0cd943
Create Date: 2026-09-24T19:34:07.027278
"""
from alembic import op
import sqlalchemy as sa


revision = '260e3ed4c5ce'
down_revision = '3ee44d0cd943'
branch_labels = None
depends_on = None


def upgrade():
    # ── Contacts ──
    op.create_table(
        'contacts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('first_name', sa.String(100), nullable=False),
        sa.Column('last_name',  sa.String(100), nullable=False),
        sa.Column('email',      sa.String(120)),
        sa.Column('phone',      sa.String(30)),
        sa.Column('position',   sa.String(100)),
        sa.Column('notes',      sa.Text()),
        sa.Column('client_id',  sa.Integer(), sa.ForeignKey('clients.id')),
        sa.Column('lead_id',    sa.Integer(), sa.ForeignKey('leads.id')),
        sa.Column('created_at', sa.DateTime()),
    )

    # ── Comments ──
    op.create_table(
        'comments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('content',     sa.Text(), nullable=False),
        sa.Column('entity_type', sa.String(20), nullable=False),
        sa.Column('entity_id',   sa.Integer(), nullable=False),
        sa.Column('user_id',     sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at',  sa.DateTime()),
    )
    op.create_index('ix_comments_entity_id', 'comments', ['entity_id'])

    # ── Activities ──
    op.create_table(
        'activities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('action',      sa.String(50), nullable=False),
        sa.Column('description', sa.Text()),
        sa.Column('entity_type', sa.String(20), nullable=False),
        sa.Column('entity_id',   sa.Integer(), nullable=False),
        sa.Column('user_id',     sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('meta',        sa.JSON()),
        sa.Column('created_at',  sa.DateTime()),
    )
    op.create_index('ix_activities_entity_id', 'activities', ['entity_id'])

    # ── Dodanie kolumn przez batch_alter_table (SQLite-safe) ──
    with op.batch_alter_table('documents') as batch_op:
        batch_op.add_column(sa.Column('lead_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('leads') as batch_op:
        batch_op.add_column(sa.Column('converted_to_client_id', sa.Integer(), nullable=True))

    with op.batch_alter_table('tasks') as batch_op:
        batch_op.add_column(sa.Column('lead_id', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('tasks') as batch_op:
        batch_op.drop_column('lead_id')
    with op.batch_alter_table('leads') as batch_op:
        batch_op.drop_column('converted_to_client_id')
    with op.batch_alter_table('documents') as batch_op:
        batch_op.drop_column('lead_id')
    op.drop_index('ix_activities_entity_id', table_name='activities')
    op.drop_table('activities')
    op.drop_index('ix_comments_entity_id', table_name='comments')
    op.drop_table('comments')
    op.drop_table('contacts')
