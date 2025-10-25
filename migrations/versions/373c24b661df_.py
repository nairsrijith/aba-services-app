"""empty message

Revision ID: 373c24b661df
Revises: 482b27abb285, 712b3c250eb5, make_payrate_client_nullable
Create Date: 2025-10-25 15:58:54.801677

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '373c24b661df'
down_revision = ('482b27abb285', '712b3c250eb5', 'make_payrate_client_nullable')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
