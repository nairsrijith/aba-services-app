"""Add two-factor authentication fields to employees

Revision ID: 008
Revises: 007
Create Date: 2026-07-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_cols = {c['name'] for c in inspector.get_columns('employees')} if 'employees' in inspector.get_table_names() else set()

    if 'two_factor_enabled' not in existing_cols:
        op.add_column('employees', sa.Column('two_factor_enabled', sa.Boolean(), nullable=False, server_default='false'))
    if 'two_factor_secret' not in existing_cols:
        op.add_column('employees', sa.Column('two_factor_secret', sa.String(length=64), nullable=True))


def downgrade():
    op.drop_column('employees', 'two_factor_secret')
    op.drop_column('employees', 'two_factor_enabled')
