"""Add invoice reminder fields and settings

Revision ID: 002
Revises: 001
Create Date: 2026-01-24 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Add reminder tracking columns to invoices table
    bind = op.get_bind()
    inspector = inspect(bind)

    # invoices columns
    inv_cols = {c['name'] for c in inspector.get_columns('invoices')} if 'invoices' in inspector.get_table_names() else set()
    if 'last_reminder_sent_date' not in inv_cols:
        op.add_column('invoices', sa.Column('last_reminder_sent_date', postgresql.TIMESTAMP(), nullable=True))
    if 'reminder_count' not in inv_cols:
        op.add_column('invoices', sa.Column('reminder_count', sa.Integer(), server_default='0', nullable=False))

    # app_settings columns
    app_cols = {c['name'] for c in inspector.get_columns('app_settings')} if 'app_settings' in inspector.get_table_names() else set()
    if 'invoice_reminder_enabled' not in app_cols:
        op.add_column('app_settings', sa.Column('invoice_reminder_enabled', sa.Boolean(), server_default='false', nullable=False))
    if 'invoice_reminder_days' not in app_cols:
        op.add_column('app_settings', sa.Column('invoice_reminder_days', sa.Integer(), server_default='5', nullable=False))
    if 'invoice_reminder_repeat_enabled' not in app_cols:
        op.add_column('app_settings', sa.Column('invoice_reminder_repeat_enabled', sa.Boolean(), server_default='false', nullable=False))
    if 'invoice_reminder_repeat_days' not in app_cols:
        op.add_column('app_settings', sa.Column('invoice_reminder_repeat_days', sa.Integer(), server_default='3', nullable=False))


def downgrade():
    # Remove reminder tracking columns from invoices table
    try:
        op.drop_column('invoices', 'reminder_count')
    except Exception:
        pass
    try:
        op.drop_column('invoices', 'last_reminder_sent_date')
    except Exception:
        pass

    # Remove reminder settings from app_settings table
    for col in ('invoice_reminder_repeat_days', 'invoice_reminder_repeat_enabled', 'invoice_reminder_days', 'invoice_reminder_enabled'):
        try:
            op.drop_column('app_settings', col)
        except Exception:
            pass
