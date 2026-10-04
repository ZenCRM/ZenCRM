"""User preference for composing email."""
from alembic import op
import sqlalchemy as sa

revision = '20261004_email_preference'
down_revision = '20261004_mail_features'
branch_labels = None
depends_on = None


def upgrade():
    if 'default_email_method' not in {c['name'] for c in sa.inspect(op.get_bind()).get_columns('users')}:
        with op.batch_alter_table('users') as batch:
            batch.add_column(sa.Column('default_email_method', sa.String(20), nullable=False, server_default='mailto'))


def downgrade():
    with op.batch_alter_table('users') as batch:
        batch.drop_column('default_email_method')
