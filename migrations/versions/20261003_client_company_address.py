"""Structured client addresses and company identifiers."""
from alembic import op
import sqlalchemy as sa
revision = '20261003_client_address'
down_revision = '20260929_document_types'
branch_labels = None
depends_on = None
FIELDS = {'nip': 20, 'regon': 14, 'krs': 10, 'street': 200, 'building_number': 20, 'apartment_number': 20, 'postal_code': 20, 'city': 120, 'country': 120}

def upgrade():
    existing = {c['name'] for c in sa.inspect(op.get_bind()).get_columns('clients')}
    with op.batch_alter_table('clients') as batch:
        for name, length in FIELDS.items():
            if name not in existing:
                batch.add_column(sa.Column(name, sa.String(length)))

def downgrade():
    with op.batch_alter_table('clients') as batch:
        for name in reversed(FIELDS):
            batch.drop_column(name)
