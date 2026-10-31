"""add_factor_unit_to_scope3_emissions

Revision ID: e4a719c28b3d
Revises: 6a8475783b53
Create Date: 2026-10-29 08:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e4a719c28b3d'
down_revision = '6a8475783b53'
branch_labels = None
depends_on = None


def _bind():
    return op.get_bind()


def _add(table, column):
    from schema_sync import has_column, has_table

    if has_table(_bind(), table) and not has_column(_bind(), table, column.name):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(column)


def upgrade():
    _add("scope3_emissions", sa.Column("factor_unit", sa.String(50), nullable=True))


def downgrade():
    pass
