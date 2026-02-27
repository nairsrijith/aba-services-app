"""empty migration to repair missing revision 004

Revision ID: 004
Revises: 003
Create Date: 2026-02-27 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # this migration was missing from repository on earlier deployments
    # schema changes (if any) already exist in the database so no-op here
    bind = op.get_bind()
    inspector = inspect(bind)
    if 'app_settings' in inspector.get_table_names():
        existing = {c['name'] for c in inspector.get_columns('app_settings')}
        if 'invoice_reminder_time' not in existing:
            op.add_column('app_settings', sa.Column('invoice_reminder_time', sa.String(length=10),
                                                    nullable=False, server_default='06:00'))
    pass


def downgrade():
    # nothing to undo
    pass
