"""
Add cover_image to Article

Revision ID: 9b1a
Revises: add_is_admin_to_user
Create Date: 2025-08-14
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '9b1a'
down_revision = 'add_is_admin_to_user'
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table('article', schema=None) as batch_op:
        batch_op.add_column(sa.Column('cover_image', sa.String(length=255), nullable=True))


def downgrade():
    with op.batch_alter_table('article', schema=None) as batch_op:
        batch_op.drop_column('cover_image')
