"""Configurable role and team action permissions."""
from alembic import op
import sqlalchemy as sa

revision = '20260928_roles_permissions'
down_revision = '20260928_phone_call_note'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    role_type = next((c['type'] for c in inspector.get_columns('users') if c['name'] == 'role'), None)
    if role_type is not None and getattr(role_type, 'length', None) == 20:
        with op.batch_alter_table('users') as batch:
            batch.alter_column('role', existing_type=sa.String(20), type_=sa.String(50))
    if not inspector.has_table('roles'):
        op.create_table('roles',
            sa.Column('key', sa.String(50), primary_key=True),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('built_in', sa.Boolean(), nullable=False))
    roles = sa.table('roles', sa.column('key', sa.String), sa.column('name', sa.String), sa.column('built_in', sa.Boolean))
    for key, name in [('admin', 'Administrator'), ('manager', 'Manager'), ('employee', 'Pracownik')]:
        existing = op.get_bind().execute(sa.text('SELECT 1 FROM roles WHERE key = :key'), {'key': key}).first()
        if not existing:
            op.bulk_insert(roles, [{'key': key, 'name': name, 'built_in': True}])
    if not inspector.has_table('permission_rules'):
        op.create_table('permission_rules',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('role_key', sa.String(50), sa.ForeignKey('roles.key', ondelete='CASCADE')),
            sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id', ondelete='CASCADE')),
            sa.Column('permission', sa.String(80), nullable=False),
            sa.Column('allowed', sa.Boolean(), nullable=False),
            sa.CheckConstraint('(role_key IS NULL) != (team_id IS NULL)', name='permission_one_subject'),
            sa.UniqueConstraint('role_key', 'permission', name='uq_permission_role'),
            sa.UniqueConstraint('team_id', 'permission', name='uq_permission_team'))


def downgrade():
    op.drop_table('permission_rules')
    op.drop_table('roles')
    with op.batch_alter_table('users') as batch:
        batch.alter_column('role', existing_type=sa.String(50), type_=sa.String(20))
