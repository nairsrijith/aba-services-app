"""Add email_sent column to paystubs table

Revision ID: 003
Revises: 002
Create Date: 2026-02-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Add email_sent column to paystubs table with default value False
    op.add_column('paystubs', sa.Column('email_sent', sa.Boolean(), server_default='false', nullable=False))


def downgrade():
    # Remove email_sent column from paystubs table
    op.drop_column('paystubs', 'email_sent')
