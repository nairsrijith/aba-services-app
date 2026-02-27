"""Add email_sent column to paystubs table

Revision ID: 003
Revises: 002
Create Date: 2026-02-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'paystubs' in inspector.get_table_names():
        existing = {c['name'] for c in inspector.get_columns('paystubs')}
        if 'email_sent' not in existing:
            op.add_column('paystubs', sa.Column('email_sent', sa.Boolean(), server_default='false', nullable=False))


def downgrade():
    try:
        op.drop_column('paystubs', 'email_sent')
    except Exception:
        pass
