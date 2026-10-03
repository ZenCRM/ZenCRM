"""baseline schema

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-10-03 13:50:45.263495

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0001_baseline'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Installations from before migrations already have some of these tables; create only the missing ones.
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if 'auth_rate_limits' not in existing:
        op.create_table('auth_rate_limits',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('key')
        )
        with op.batch_alter_table('auth_rate_limits', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_auth_rate_limits_expires_at'), ['expires_at'], unique=False)

    if 'custom_fields' not in existing:
        op.create_table('custom_fields',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity', sa.String(length=40), nullable=False),
        sa.Column('label', sa.String(length=120), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('custom_fields', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_custom_fields_entity'), ['entity'], unique=False)

    if 'document_types' not in existing:
        op.create_table('document_types',
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('fields', sa.JSON(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('key')
        )

    if 'email_templates' not in existing:
        op.create_table('email_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=60), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('category', sa.String(length=40), nullable=True),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=False),
        sa.Column('variables', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('email_templates', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_email_templates_key'), ['key'], unique=True)

    if 'portal_configuration' not in existing:
        op.create_table('portal_configuration',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('data', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )

    if 'portal_spaces' not in existing:
        op.create_table('portal_spaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )

    if 'push_identity' not in existing:
        op.create_table('push_identity',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('private_key', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id')
        )

    if 'roles' not in existing:
        op.create_table('roles',
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('built_in', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('key')
        )

    if 'service_catalog' not in existing:
        op.create_table('service_catalog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('billing_type', sa.String(length=20), nullable=True),
        sa.Column('term_type', sa.String(length=20), nullable=True),
        sa.Column('default_billing_cycle', sa.String(length=20), nullable=True),
        sa.Column('default_price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('is_price_fixed', sa.Boolean(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )

    if 'settings' not in existing:
        op.create_table('settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('settings', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_settings_key'), ['key'], unique=True)

    if 'translation_entries' not in existing:
        op.create_table('translation_entries',
        sa.Column('locale', sa.String(length=16), nullable=False),
        sa.Column('key', sa.String(length=500), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('locale', 'key')
        )

    if 'translation_languages' not in existing:
        op.create_table('translation_languages',
        sa.Column('code', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('base_locale', sa.String(length=16), nullable=False),
        sa.PrimaryKeyConstraint('code')
        )

    if 'users' not in existing:
        op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('first_name', sa.String(length=50), nullable=False),
        sa.Column('last_name', sa.String(length=50), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('default_call_method', sa.String(length=20), nullable=True),
        sa.Column('email_notifications', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
        )

    if 'activities' not in existing:
        op.create_table('activities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('meta', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('activities', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_activities_entity_id'), ['entity_id'], unique=False)

    if 'attachments' not in existing:
        op.create_table('attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('storage_name', sa.String(length=64), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('storage_name')
        )
        with op.batch_alter_table('attachments', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_attachments_entity_id'), ['entity_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_attachments_entity_type'), ['entity_type'], unique=False)

    if 'clients' not in existing:
        op.create_table('clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('phone', sa.String(length=20), nullable=True),
        sa.Column('company', sa.String(length=200), nullable=True),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('assignee_id', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'comments' not in existing:
        op.create_table('comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('kind', sa.String(length=16), server_default='note', nullable=False),
        sa.Column('communication_status', sa.String(length=16), nullable=True),
        sa.Column('address', sa.String(length=254), nullable=True),
        sa.Column('entity_type', sa.String(length=20), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('comments', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_comments_entity_id'), ['entity_id'], unique=False)

    if 'custom_values' not in existing:
        op.create_table('custom_values',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('field_id', sa.Integer(), nullable=False),
        sa.Column('record_id', sa.Integer(), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['field_id'], ['custom_fields.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('field_id', 'record_id')
        )

    if 'password_resets' not in existing:
        op.create_table('password_resets',
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('password_version', sa.String(length=256), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('token_hash')
        )
        with op.batch_alter_table('password_resets', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_password_resets_user_id'), ['user_id'], unique=False)

    if 'portal_items' not in existing:
        op.create_table('portal_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('space_id', sa.Integer(), nullable=False),
        sa.Column('kind', sa.String(length=20), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('filename', sa.String(length=255), nullable=True),
        sa.Column('storage_name', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['space_id'], ['portal_spaces.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('portal_items', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_portal_items_space_id'), ['space_id'], unique=False)

    if 'portal_members' not in existing:
        op.create_table('portal_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('space_id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=200), nullable=False),
        sa.Column('password_hash', sa.String(length=256), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['space_id'], ['portal_spaces.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('space_id', 'email')
        )

    if 'push_subscriptions' not in existing:
        op.create_table('push_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('endpoint_hash', sa.String(length=64), nullable=False),
        sa.Column('subscription', sa.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('endpoint_hash')
        )
        with op.batch_alter_table('push_subscriptions', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_push_subscriptions_user_id'), ['user_id'], unique=False)

    if 'sms_devices' not in existing:
        op.create_table('sms_devices',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('token', sa.String(length=120), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('last_seen', sa.DateTime(), nullable=True),
        sa.Column('today_stats', sa.Text(), nullable=True),
        sa.Column('week_stats', sa.Text(), nullable=True),
        sa.Column('stats_updated_at', sa.DateTime(), nullable=True),
        sa.Column('last_sync_at', sa.DateTime(), nullable=True),
        sa.Column('sync_from', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('sms_devices', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_sms_devices_token'), ['token'], unique=True)

    if 'teams' not in existing:
        op.create_table('teams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=30), nullable=True),
        sa.Column('leader_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['leader_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )

    if 'templates' not in existing:
        op.create_table('templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('document_type_key', sa.String(length=50), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('variables', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['document_type_key'], ['document_types.key'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'leads' not in existing:
        op.create_table('leads',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('assignee_id', sa.Integer(), nullable=True),
        sa.Column('value', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('stage', sa.String(length=30), nullable=True),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('probability', sa.Integer(), nullable=True),
        sa.Column('expected_close_date', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('converted_to_client_id', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['converted_to_client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'offers' not in existing:
        op.create_table('offers',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('rendered_html', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('total_amount', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('public_token', sa.String(length=64), nullable=True),
        sa.Column('pdf_path', sa.String(length=500), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('number')
        )
        with op.batch_alter_table('offers', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_offers_public_token'), ['public_token'], unique=True)

    if 'permission_rules' not in existing:
        op.create_table('permission_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('role_key', sa.String(length=50), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('permission', sa.String(length=80), nullable=False),
        sa.Column('allowed', sa.Boolean(), nullable=False),
        sa.CheckConstraint('(role_key IS NULL) != (team_id IS NULL)', name='permission_one_subject'),
        sa.ForeignKeyConstraint(['role_key'], ['roles.key'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_key', 'permission', name='uq_permission_role'),
        sa.UniqueConstraint('team_id', 'permission', name='uq_permission_team')
        )

    if 'phone_calls' not in existing:
        op.create_table('phone_calls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('number', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.BigInteger(), nullable=True),
        sa.Column('call_time', sa.DateTime(), nullable=True),
        sa.Column('date_formatted', sa.String(length=50), nullable=True),
        sa.Column('duration_sec', sa.Integer(), nullable=True),
        sa.Column('duration_formatted', sa.String(length=50), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['device_id'], ['sms_devices.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('phone_calls', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_phone_calls_number'), ['number'], unique=False)
            batch_op.create_index(batch_op.f('ix_phone_calls_timestamp'), ['timestamp'], unique=False)

    if 'portal_client_spaces' not in existing:
        op.create_table('portal_client_spaces',
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('space_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['space_id'], ['portal_spaces.id'], ),
        sa.PrimaryKeyConstraint('client_id'),
        sa.UniqueConstraint('space_id')
        )

    if 'portal_replies' not in existing:
        op.create_table('portal_replies',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('item_id', sa.Integer(), nullable=False),
        sa.Column('author', sa.String(length=200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['item_id'], ['portal_items.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('portal_replies', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_portal_replies_item_id'), ['item_id'], unique=False)

    if 'portal_sessions' not in existing:
        op.create_table('portal_sessions',
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('member_id', sa.Integer(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['member_id'], ['portal_members.id'], ),
        sa.PrimaryKeyConstraint('token_hash')
        )

    if 'projects' not in existing:
        op.create_table('projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('manager_id', sa.Integer(), nullable=True),
        sa.Column('budget', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('task_stages', sa.Text(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['manager_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'services' not in existing:
        op.create_table('services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('catalog_id', sa.Integer(), nullable=True),
        sa.Column('billing_type', sa.String(length=20), nullable=True),
        sa.Column('term_type', sa.String(length=20), nullable=True),
        sa.Column('billing_cycle', sa.String(length=20), nullable=True),
        sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('risk_level', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('assignee_ids', sa.JSON(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['catalog_id'], ['service_catalog.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'sms_messages' not in existing:
        op.create_table('sms_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('address', sa.String(length=50), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.BigInteger(), nullable=True),
        sa.Column('message_time', sa.DateTime(), nullable=True),
        sa.Column('date_formatted', sa.String(length=50), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['device_id'], ['sms_devices.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('sms_messages', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_sms_messages_address'), ['address'], unique=False)
            batch_op.create_index(batch_op.f('ix_sms_messages_timestamp'), ['timestamp'], unique=False)

    if 'sms_queue' not in existing:
        op.create_table('sms_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('device_id', sa.Integer(), nullable=True),
        sa.Column('phone_number', sa.String(length=50), nullable=True),
        sa.Column('message', sa.Text(), nullable=True),
        sa.Column('action', sa.String(length=50), nullable=True),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('sent_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['device_id'], ['sms_devices.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'team_members' not in existing:
        op.create_table('team_members',
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('team_id', 'user_id')
        )

    if 'tickets' not in existing:
        op.create_table('tickets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_number', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('contact_name', sa.String(length=100), nullable=True),
        sa.Column('contact_email', sa.String(length=120), nullable=False),
        sa.Column('contact_phone', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('assignee_id', sa.Integer(), nullable=True),
        sa.Column('team_id', sa.Integer(), nullable=True),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('source', sa.String(length=30), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('tickets', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_tickets_contact_email'), ['contact_email'], unique=False)
            batch_op.create_index(batch_op.f('ix_tickets_ticket_number'), ['ticket_number'], unique=True)
            batch_op.create_index(batch_op.f('ix_tickets_token'), ['token'], unique=True)

    if 'contacts' not in existing:
        op.create_table('contacts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=120), nullable=True),
        sa.Column('phone', sa.String(length=30), nullable=True),
        sa.Column('position', sa.String(length=100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'documents' not in existing:
        op.create_table('documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('service_id', sa.Integer(), nullable=True),
        sa.Column('template_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('rendered_html', sa.Text(), nullable=True),
        sa.Column('data', sa.JSON(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('pdf_path', sa.String(length=500), nullable=True),
        sa.Column('public_token', sa.String(length=64), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['templates.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('documents', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_documents_public_token'), ['public_token'], unique=True)

    if 'meetings' not in existing:
        op.create_table('meetings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('organizer_id', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.ForeignKeyConstraint(['organizer_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'project_members' not in existing:
        op.create_table('project_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'user_id')
        )

    if 'tasks' not in existing:
        op.create_table('tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('priority', sa.String(length=10), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('client_id', sa.Integer(), nullable=True),
        sa.Column('lead_id', sa.Integer(), nullable=True),
        sa.Column('service_id', sa.Integer(), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('assignee_id', sa.Integer(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assignee_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ),
        sa.ForeignKeyConstraint(['lead_id'], ['leads.id'], ),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'ticket_messages' not in existing:
        op.create_table('ticket_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('sender_type', sa.String(length=20), nullable=True),
        sa.Column('sender_name', sa.String(length=100), nullable=True),
        sa.Column('sender_email', sa.String(length=120), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_internal', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('ticket_messages', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_ticket_messages_ticket_id'), ['ticket_id'], unique=False)

    if 'reminders' not in existing:
        op.create_table('reminders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=False),
        sa.Column('remind_at', sa.DateTime(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('link', sa.String(length=500), nullable=True),
        sa.Column('dismissed', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'task_id', name='uq_reminder_user_task')
        )
        with op.batch_alter_table('reminders', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_reminders_remind_at'), ['remind_at'], unique=False)
            batch_op.create_index(batch_op.f('ix_reminders_user_id'), ['user_id'], unique=False)

    if 'task_assignees' not in existing:
        op.create_table('task_assignees',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    if 'push_deliveries' not in existing:
        op.create_table('push_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('reminder_id', sa.Integer(), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('sent', sa.Boolean(), nullable=False),
        sa.Column('next_attempt', sa.DateTime(), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('lease', sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(['reminder_id'], ['reminders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['push_subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('subscription_id', 'reminder_id', 'scheduled_at', name='uq_push_delivery')
        )
        with op.batch_alter_table('push_deliveries', schema=None) as batch_op:
            batch_op.create_index('ix_push_delivery_pending', ['sent', 'next_attempt'], unique=False)



def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('push_deliveries', schema=None) as batch_op:
        batch_op.drop_index('ix_push_delivery_pending')

    op.drop_table('push_deliveries')
    op.drop_table('task_assignees')
    with op.batch_alter_table('reminders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reminders_user_id'))
        batch_op.drop_index(batch_op.f('ix_reminders_remind_at'))

    op.drop_table('reminders')
    with op.batch_alter_table('ticket_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ticket_messages_ticket_id'))

    op.drop_table('ticket_messages')
    op.drop_table('tasks')
    op.drop_table('project_members')
    op.drop_table('meetings')
    with op.batch_alter_table('documents', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_documents_public_token'))

    op.drop_table('documents')
    op.drop_table('contacts')
    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tickets_token'))
        batch_op.drop_index(batch_op.f('ix_tickets_ticket_number'))
        batch_op.drop_index(batch_op.f('ix_tickets_contact_email'))

    op.drop_table('tickets')
    op.drop_table('team_members')
    op.drop_table('sms_queue')
    with op.batch_alter_table('sms_messages', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sms_messages_timestamp'))
        batch_op.drop_index(batch_op.f('ix_sms_messages_address'))

    op.drop_table('sms_messages')
    op.drop_table('services')
    op.drop_table('projects')
    op.drop_table('portal_sessions')
    with op.batch_alter_table('portal_replies', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_portal_replies_item_id'))

    op.drop_table('portal_replies')
    op.drop_table('portal_client_spaces')
    with op.batch_alter_table('phone_calls', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_phone_calls_timestamp'))
        batch_op.drop_index(batch_op.f('ix_phone_calls_number'))

    op.drop_table('phone_calls')
    op.drop_table('permission_rules')
    with op.batch_alter_table('offers', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_offers_public_token'))

    op.drop_table('offers')
    op.drop_table('leads')
    op.drop_table('templates')
    op.drop_table('teams')
    with op.batch_alter_table('sms_devices', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_sms_devices_token'))

    op.drop_table('sms_devices')
    with op.batch_alter_table('push_subscriptions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_push_subscriptions_user_id'))

    op.drop_table('push_subscriptions')
    op.drop_table('portal_members')
    with op.batch_alter_table('portal_items', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_portal_items_space_id'))

    op.drop_table('portal_items')
    with op.batch_alter_table('password_resets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_password_resets_user_id'))

    op.drop_table('password_resets')
    op.drop_table('custom_values')
    with op.batch_alter_table('comments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_comments_entity_id'))

    op.drop_table('comments')
    op.drop_table('clients')
    with op.batch_alter_table('attachments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_attachments_entity_type'))
        batch_op.drop_index(batch_op.f('ix_attachments_entity_id'))

    op.drop_table('attachments')
    with op.batch_alter_table('activities', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_activities_entity_id'))

    op.drop_table('activities')
    op.drop_table('users')
    op.drop_table('translation_languages')
    op.drop_table('translation_entries')
    with op.batch_alter_table('settings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_settings_key'))

    op.drop_table('settings')
    op.drop_table('service_catalog')
    op.drop_table('roles')
    op.drop_table('push_identity')
    op.drop_table('portal_spaces')
    op.drop_table('portal_configuration')
    with op.batch_alter_table('email_templates', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_email_templates_key'))

    op.drop_table('email_templates')
    op.drop_table('document_types')
    with op.batch_alter_table('custom_fields', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_custom_fields_entity'))

    op.drop_table('custom_fields')
    with op.batch_alter_table('auth_rate_limits', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_auth_rate_limits_expires_at'))

    op.drop_table('auth_rate_limits')
    # ### end Alembic commands ###
