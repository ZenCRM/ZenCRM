# Optional application platform, isolated credentials and event delivery.
from alembic import op
import sqlalchemy as sa

revision = '20261006_plugins'
down_revision = '20261004_mail_polling'
branch_labels = None
depends_on = None

def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    if 'plugin_events' not in existing:
        op.create_table('plugin_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('kind', sa.String(length=80), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_plugin_events_created_at'), 'plugin_events', ['created_at'], unique=False)
    if 'plugin_apps' not in existing:
        op.create_table('plugin_apps',
        sa.Column('id', sa.String(length=40), nullable=False),
        sa.Column('manifest', sa.JSON(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('installed', sa.Boolean(), nullable=False),
        sa.Column('approved_scopes', sa.JSON(), nullable=False),
        sa.Column('allowed_users', sa.JSON(), nullable=False),
        sa.Column('configuration', sa.JSON(), nullable=False),
        sa.Column('client_secret_hash', sa.String(length=256), nullable=True),
        sa.Column('signing_secret_encrypted', sa.Text(), nullable=True),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
    if 'plugin_audit' not in existing:
        op.create_table('plugin_audit',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('app_id', sa.String(length=40), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=80), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
        op.create_index(op.f('ix_plugin_audit_app_id'), 'plugin_audit', ['app_id'], unique=False)
    if 'plugin_grants' not in existing:
        op.create_table('plugin_grants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('app_id', sa.String(length=40), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('scopes', sa.JSON(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['app_id'], ['plugin_apps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('app_id', 'user_id', name='uq_plugin_grant_user')
        )
    if 'plugin_codes' not in existing:
        op.create_table('plugin_codes',
        sa.Column('code_hash', sa.String(length=64), nullable=False),
        sa.Column('grant_id', sa.Integer(), nullable=False),
        sa.Column('redirect_uri', sa.String(length=2048), nullable=False),
        sa.Column('challenge', sa.String(length=43), nullable=False),
        sa.Column('app_revision', sa.Integer(), nullable=False),
        sa.Column('grant_revision', sa.Integer(), nullable=False),
        sa.Column('password_version', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('consumed', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['grant_id'], ['plugin_grants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('code_hash')
        )
    if 'plugin_deliveries' not in existing:
        op.create_table('plugin_deliveries',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('grant_id', sa.Integer(), nullable=False),
        sa.Column('app_revision', sa.Integer(), nullable=False),
        sa.Column('grant_revision', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('next_attempt_at', sa.DateTime(), nullable=False),
        sa.Column('lease_token', sa.String(length=36), nullable=True),
        sa.Column('lease_until', sa.DateTime(), nullable=True),
        sa.Column('last_status', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['plugin_events.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['grant_id'], ['plugin_grants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'grant_id', name='uq_plugin_delivery_event')
        )
        op.create_index(op.f('ix_plugin_deliveries_status'), 'plugin_deliveries', ['status'], unique=False)
    if 'plugin_storage' not in existing:
        op.create_table('plugin_storage',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('grant_id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=80), nullable=False),
        sa.Column('value', sa.JSON(), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['grant_id'], ['plugin_grants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('grant_id', 'key', name='uq_plugin_storage_key')
        )
    if 'plugin_subscriptions' not in existing:
        op.create_table('plugin_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('grant_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(['grant_id'], ['plugin_grants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('grant_id', 'kind', name='uq_plugin_subscription_kind')
        )
    if 'plugin_tokens' not in existing:
        op.create_table('plugin_tokens',
        sa.Column('access_hash', sa.String(length=64), nullable=False),
        sa.Column('refresh_hash', sa.String(length=64), nullable=True),
        sa.Column('family', sa.String(length=36), nullable=False),
        sa.Column('grant_id', sa.Integer(), nullable=False),
        sa.Column('app_revision', sa.Integer(), nullable=False),
        sa.Column('grant_revision', sa.Integer(), nullable=False),
        sa.Column('password_version', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('refresh_expires_at', sa.DateTime(), nullable=True),
        sa.Column('revoked', sa.Boolean(), nullable=False),
        sa.Column('refresh_used', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['grant_id'], ['plugin_grants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('access_hash'),
        sa.UniqueConstraint('refresh_hash')
        )
        op.create_index(op.f('ix_plugin_tokens_family'), 'plugin_tokens', ['family'], unique=False)

def downgrade():
    op.drop_index(op.f('ix_plugin_tokens_family'), table_name='plugin_tokens')
    op.drop_table('plugin_tokens')
    op.drop_table('plugin_subscriptions')
    op.drop_table('plugin_storage')
    op.drop_index(op.f('ix_plugin_deliveries_status'), table_name='plugin_deliveries')
    op.drop_table('plugin_deliveries')
    op.drop_table('plugin_codes')
    op.drop_table('plugin_grants')
    op.drop_index(op.f('ix_plugin_audit_app_id'), table_name='plugin_audit')
    op.drop_table('plugin_audit')
    op.drop_table('plugin_apps')
    op.drop_index(op.f('ix_plugin_events_created_at'), table_name='plugin_events')
    op.drop_table('plugin_events')
