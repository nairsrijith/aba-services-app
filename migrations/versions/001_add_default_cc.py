"""Add default_cc column to app_settings

Revision ID: 001
Revises: 
Create Date: 2026-01-24 10:58:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add default_cc column if it doesn't exist
    op.add_column('app_settings', sa.Column('default_cc', sa.String(length=120), nullable=True))


def downgrade():
    # Remove default_cc column
    op.drop_column('app_settings', 'default_cc')
