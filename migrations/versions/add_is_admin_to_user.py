"""Add is_admin to User model

Revision ID: add_is_admin_to_user
Revises: 6d9f095c4e82
Create Date: 2025-08-09
"""
revision = 'add_is_admin_to_user'
down_revision = '6d9f095c4e82'
branch_labels = None
depends_on = None
from alembic import op
import sqlalchemy as sa
def upgrade():
    op.add_column('user', sa.Column('is_admin', sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column('user', 'is_admin')
