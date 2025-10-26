"""fix payrates client_id constraint

Revision ID: e42b871653db
Revises: d42a871653da
Create Date: 2025-10-25 23:42:15.080537

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e42b871653db'
down_revision = 'd42a871653da'
branch_labels = None
depends_on = None


def upgrade():
    # Ensure existing rows have a non-null value before making the column NOT NULL.
    # Backfill NULLs to True (safe default) so ALTER ... SET NOT NULL will succeed.
    op.execute("UPDATE clients SET is_active = true WHERE is_active IS NULL;")
    op.execute("UPDATE employees SET is_active = true WHERE is_active IS NULL;")

    # Keep payrates.client_id nullable since there are existing NULL values
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.alter_column('is_active',
               existing_type=sa.Boolean(),
               server_default=sa.text('true'),
               nullable=False)

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.alter_column('is_active',
               existing_type=sa.Boolean(),
               server_default=sa.text('true'),
               nullable=False)


def downgrade():
    with op.batch_alter_table('clients', schema=None) as batch_op:
        batch_op.alter_column('is_active',
               existing_type=sa.Boolean(),
               server_default=None,
               nullable=True)

    with op.batch_alter_table('employees', schema=None) as batch_op:
        batch_op.alter_column('is_active',
               existing_type=sa.Boolean(),
               server_default=None,
               nullable=True)
