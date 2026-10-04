"""Personal and team mailbox storage."""
from alembic import op
import sqlalchemy as sa

revision = '20261004_mailboxes'
down_revision = '20261003_client_address'
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    # Legacy bridge may already contain these tables from create_all.
    if 'mailboxes' in existing and 'mail_messages' in existing:
        return
    op.create_table('mailboxes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('email', sa.String(254), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE')),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id', ondelete='CASCADE')),
        sa.Column('username', sa.String(254), nullable=False),
        sa.Column('password_encrypted', sa.Text(), nullable=False),
        sa.Column('imap_host', sa.String(254), nullable=False),
        sa.Column('imap_port', sa.Integer(), nullable=False),
        sa.Column('smtp_host', sa.String(254), nullable=False),
        sa.Column('smtp_port', sa.Integer(), nullable=False),
        sa.Column('smtp_security', sa.String(10), nullable=False),
        sa.Column('signature', sa.Text(), nullable=False),
        sa.Column('last_sync_at', sa.DateTime()),
        sa.Column('uid_validity', sa.String(50)),
        sa.CheckConstraint('(user_id IS NULL) != (team_id IS NULL)', name='mailbox_owner'))
    op.create_table('mail_messages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('mailbox_id', sa.Integer(), sa.ForeignKey('mailboxes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('remote_uid', sa.String(100)), sa.Column('message_id', sa.String(998)),
        sa.Column('folder', sa.String(20), nullable=False), sa.Column('sender', sa.String(254), nullable=False),
        sa.Column('recipients', sa.JSON(), nullable=False), sa.Column('subject', sa.Text()),
        sa.Column('body', sa.Text()), sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('mailbox_id', 'remote_uid', name='mail_message_uid'))
    op.create_index('ix_mail_messages_mailbox_id', 'mail_messages', ['mailbox_id'])


def downgrade():
    op.drop_table('mail_messages')
    op.drop_table('mailboxes')
