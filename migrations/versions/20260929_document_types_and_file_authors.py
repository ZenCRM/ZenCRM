"""Configurable document types and attachment authors."""
from alembic import op
import sqlalchemy as sa

revision = '20260929_document_types'
down_revision = '20260929_attachments'
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table('document_types'):
        op.create_table('document_types',
            sa.Column('key', sa.String(50), primary_key=True),
            sa.Column('name', sa.String(120), nullable=False),
            sa.Column('fields', sa.JSON(), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False))
    if 'created_by_id' not in {c['name'] for c in inspector.get_columns('attachments')}:
        with op.batch_alter_table('attachments') as batch:
            batch.add_column(sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('users.id')))
    if 'document_type_key' not in {c['name'] for c in inspector.get_columns('templates')}:
        with op.batch_alter_table('templates') as batch:
            batch.add_column(sa.Column('document_type_key', sa.String(50), sa.ForeignKey('document_types.key')))
    for key, name in [('contract', 'Umowa'), ('invoice', 'Faktura'), ('report', 'Raport'), ('other', 'Inne')]:
        op.get_bind().execute(sa.text('INSERT INTO document_types (key, name, fields, is_active) SELECT :key, :name, :fields, 1 WHERE NOT EXISTS (SELECT 1 FROM document_types WHERE key=:key)'),
                              {'key': key, 'name': name, 'fields': '[]'})


def downgrade():
    with op.batch_alter_table('templates') as batch:
        batch.drop_column('document_type_key')
    with op.batch_alter_table('attachments') as batch:
        batch.drop_column('created_by_id')
    op.drop_table('document_types')
