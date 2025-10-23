"""remove intervention_ids from invoices

Revision ID: remove_intervention_ids
Revises: 4fe5e5e68042
Create Date: 2025-10-23
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'remove_intervention_ids'
down_revision = '4fe5e5e68042'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the intervention_ids column if it exists
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.drop_column('intervention_ids')


def downgrade():
    # Add the column back
    with op.batch_alter_table('invoices') as batch_op:
        batch_op.add_column(sa.Column('intervention_ids', sa.String(), nullable=True))
