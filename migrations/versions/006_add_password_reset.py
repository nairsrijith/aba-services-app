"""Add password reset fields to employees table

Revision ID: 006
Revises: 005
Create Date: 2026-04-05 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Get existing columns
    existing_cols = {c['name'] for c in inspector.get_columns('employees')}

    # Add password reset key column if it doesn't exist
    if 'password_reset_key' not in existing_cols:
        op.add_column('employees', sa.Column('password_reset_key', sa.String(64), nullable=True, default=None))
    
    # Add password reset requested timestamp if it doesn't exist
    if 'password_reset_requested_at' not in existing_cols:
        op.add_column('employees', sa.Column('password_reset_requested_at', sa.DateTime, nullable=True, default=None))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Get existing columns
    existing_cols = {c['name'] for c in inspector.get_columns('employees')}

    # Drop columns if they exist
    if 'password_reset_key' in existing_cols:
        op.drop_column('employees', 'password_reset_key')
    
    if 'password_reset_requested_at' in existing_cols:
        op.drop_column('employees', 'password_reset_requested_at')
