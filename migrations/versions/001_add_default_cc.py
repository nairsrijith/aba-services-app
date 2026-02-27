"""Add default_cc column to app_settings

Revision ID: 001
Revises: 
Create Date: 2026-01-24 10:58:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # If the table doesn't exist (fresh DB), create a minimal `app_settings` table
    if 'app_settings' not in inspector.get_table_names():
        op.create_table(
            'app_settings',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('org_name', sa.String(200)),
            sa.Column('org_address', sa.String(500)),
            sa.Column('org_phone', sa.String(50)),
            sa.Column('org_email', sa.String(120)),
            sa.Column('payment_email', sa.String(120)),
            sa.Column('logo_path', sa.String(500)),
            sa.Column('gmail_client_id', sa.String(200)),
            sa.Column('gmail_client_secret', sa.String(200)),
            sa.Column('gmail_refresh_token', sa.String(200)),
            sa.Column('testing_mode', sa.Boolean, default=False),
            sa.Column('testing_email', sa.String(120)),
        )
        # refresh inspector after creating table
        inspector = inspect(bind)

    # Add default_cc column if it doesn't exist
    existing_cols = {c['name'] for c in inspector.get_columns('app_settings')}
    if 'default_cc' not in existing_cols:
        op.add_column('app_settings', sa.Column('default_cc', sa.String(length=120), nullable=True))


def downgrade():
    # Remove default_cc column
    try:
        op.drop_column('app_settings', 'default_cc')
    except Exception:
        # column might not exist on older DBs — ignore
        pass
