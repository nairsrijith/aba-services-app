"""Add ServiceAccount and AutomationToken tables

Revision ID: 007
Revises: 006
Create Date: 2026-06-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'service_accounts',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('name', sa.String(length=120), nullable=False, unique=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
    )

    op.create_table(
        'automation_tokens',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('service_account_id', sa.Integer(), sa.ForeignKey('service_accounts.id'), nullable=False),
        sa.Column('created_by_id', sa.Integer(), sa.ForeignKey('employees.id'), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('last_used', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_automation_tokens_token_hash', 'automation_tokens', ['token_hash'], unique=False)


def downgrade():
    op.drop_index('ix_automation_tokens_token_hash', table_name='automation_tokens')
    op.drop_table('automation_tokens')
    op.drop_table('service_accounts')
