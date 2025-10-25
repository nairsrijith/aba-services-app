"""make payrates.client_id nullable

Revision ID: make_payrate_client_nullable
Revises: remove_intervention_ids
Create Date: 2025-10-25 19:50:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'make_payrate_client_nullable'
down_revision = 'remove_intervention_ids'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('payrates', schema=None) as batch_op:
        batch_op.alter_column('client_id', existing_type=sa.Integer(), nullable=True)


def downgrade():
    # Revert to NOT NULL - ensure no NULLs exist before running downgrade
    with op.batch_alter_table('payrates', schema=None) as batch_op:
        batch_op.alter_column('client_id', existing_type=sa.Integer(), nullable=False)
