"""Add comprehensive parent details to clients table

Revision ID: 005
Revises: 004
Create Date: 2026-02-28 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    # Get existing columns
    existing_cols = {c['name'] for c in inspector.get_columns('clients')}

    # Add new parent 1 columns if they don't exist
    if 'parent_firstname' not in existing_cols:
        op.add_column('clients', sa.Column('parent_firstname', sa.String(51), nullable=True))
    
    if 'parent_lastname' not in existing_cols:
        op.add_column('clients', sa.Column('parent_lastname', sa.String(51), nullable=True))
    
    if 'parent_cell' not in existing_cols:
        op.add_column('clients', sa.Column('parent_cell', sa.String(10), nullable=True))
    
    if 'parent_email' not in existing_cols:
        op.add_column('clients', sa.Column('parent_email', sa.String(120), nullable=True))

    # Add new parent 2 columns if they don't exist
    if 'parent2_firstname' not in existing_cols:
        op.add_column('clients', sa.Column('parent2_firstname', sa.String(51), nullable=True))
    
    if 'parent2_lastname' not in existing_cols:
        op.add_column('clients', sa.Column('parent2_lastname', sa.String(51), nullable=True))
    
    if 'parent2_email' not in existing_cols:
        op.add_column('clients', sa.Column('parent2_email', sa.String(120), nullable=True))
    
    if 'parent2_cell' not in existing_cols:
        op.add_column('clients', sa.Column('parent2_cell', sa.String(10), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)

    existing_cols = {c['name'] for c in inspector.get_columns('clients')}

    # Drop new columns in reverse order
    if 'parent2_cell' in existing_cols:
        op.drop_column('clients', 'parent2_cell')
    
    if 'parent2_email' in existing_cols:
        op.drop_column('clients', 'parent2_email')
    
    if 'parent2_lastname' in existing_cols:
        op.drop_column('clients', 'parent2_lastname')
    
    if 'parent2_firstname' in existing_cols:
        op.drop_column('clients', 'parent2_firstname')
    
    if 'parent_email' in existing_cols:
        op.drop_column('clients', 'parent_email')
    
    if 'parent_cell' in existing_cols:
        op.drop_column('clients', 'parent_cell')
    
    if 'parent_lastname' in existing_cols:
        op.drop_column('clients', 'parent_lastname')
    
    if 'parent_firstname' in existing_cols:
        op.drop_column('clients', 'parent_firstname')
