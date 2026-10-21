"""add_gas_composition_and_scope_fields

Revision ID: 6a8475783b53
Revises: d4e8a1b7c2f0
Create Date: 2026-10-21 10:37:25.957010

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a8475783b53'
down_revision = 'd4e8a1b7c2f0'
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
    # 1. Custom Factors
    _add("custom_factors", sa.Column("facility_id", sa.Integer(), nullable=True))
    _add("custom_factors", sa.Column("region", sa.String(100), nullable=True))
    _add("custom_factors", sa.Column("gas_composition", sa.Text(), nullable=True))

    # 2. Emissions (Scope 1)
    _add("emissions", sa.Column("gas_composition", sa.Text(), nullable=True))

    # 3. Scope 2 Emissions
    _add("scope2_emissions", sa.Column("gas_composition", sa.Text(), nullable=True))

    # 4. Scope 3 Emissions
    _add("scope3_emissions", sa.Column("region", sa.String(100), nullable=True))
    _add("scope3_emissions", sa.Column("gas_composition", sa.Text(), nullable=True))


def downgrade():
    pass
