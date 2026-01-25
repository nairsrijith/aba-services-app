"""Add invoice reminder fields and settings

Revision ID: 002
Revises: 001
Create Date: 2026-01-24 11:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade():
    # Add reminder tracking columns to invoices table
    op.add_column('invoices', sa.Column('last_reminder_sent_date', postgresql.TIMESTAMP(), nullable=True))
    op.add_column('invoices', sa.Column('reminder_count', sa.Integer(), server_default='0', nullable=False))
    
    # Add reminder settings to app_settings table with server defaults
    op.add_column('app_settings', sa.Column('invoice_reminder_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('app_settings', sa.Column('invoice_reminder_days', sa.Integer(), server_default='5', nullable=False))
    op.add_column('app_settings', sa.Column('invoice_reminder_repeat_enabled', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('app_settings', sa.Column('invoice_reminder_repeat_days', sa.Integer(), server_default='3', nullable=False))


def downgrade():
    # Remove reminder tracking columns from invoices table
    op.drop_column('invoices', 'reminder_count')
    op.drop_column('invoices', 'last_reminder_sent_date')
    
    # Remove reminder settings from app_settings table
    op.drop_column('app_settings', 'invoice_reminder_repeat_days')
    op.drop_column('app_settings', 'invoice_reminder_repeat_enabled')
    op.drop_column('app_settings', 'invoice_reminder_days')
    op.drop_column('app_settings', 'invoice_reminder_enabled')
