"""empty message

Revision ID: 9af9783bfaaa
Revises: d2953519d1c0, remove_intervention_ids
Create Date: 2025-10-23 10:09:42.028107

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9af9783bfaaa'
down_revision = ('d2953519d1c0', 'remove_intervention_ids')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
