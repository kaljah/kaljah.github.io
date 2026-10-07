"""Add Scope 2 dual reporting columns and CustomFactor approval workflow.

- scope2_emissions.co2e_location_based (Float)
- scope2_emissions.co2e_market_based (Float)
- scope2_emissions.market_instrument_type (String(50))
- scope2_emissions.market_emission_factor (Float)
- custom_factors.status (String(20), default 'Approved')
- custom_factors.approved_by (Integer, FK users.id)
- custom_factors.approved_at (DateTime)

Backfills existing scope2_emissions records so co2e_location_based = co2e
and co2e_market_based = co2e.

Revision ID: b2d5f8e31a42
Revises: a1c4e7f20b31
Create Date: 2026-10-05
"""
import sqlalchemy as sa
from alembic import op

revision = "b2d5f8e31a42"
down_revision = "a1c4e7f20b31"
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
    # 1. Scope 2 Dual Reporting Columns
    _add("scope2_emissions", sa.Column("co2e_location_based", sa.Float(), nullable=True))
    _add("scope2_emissions", sa.Column("co2e_market_based", sa.Float(), nullable=True))
    _add("scope2_emissions", sa.Column("market_instrument_type", sa.String(50), nullable=True))
    _add("scope2_emissions", sa.Column("market_emission_factor", sa.Float(), nullable=True))

    # 2. Custom Factor Maker-Checker Workflow Columns
    _add("custom_factors", sa.Column("status", sa.String(20), nullable=False, server_default="Approved"))
    _add("custom_factors", sa.Column("approved_by", sa.Integer(), nullable=True))
    _add("custom_factors", sa.Column("approved_at", sa.DateTime(), nullable=True))

    from schema_sync import has_column, has_table

    # 3. Backfill existing Scope 2 records (data preservation)
    if has_table(_bind(), "scope2_emissions"):
        if has_column(_bind(), "scope2_emissions", "co2e_location_based") and has_column(_bind(), "scope2_emissions", "co2e"):
            op.execute("UPDATE scope2_emissions SET co2e_location_based = co2e WHERE co2e_location_based IS NULL")
        if has_column(_bind(), "scope2_emissions", "co2e_market_based") and has_column(_bind(), "scope2_emissions", "co2e"):
            op.execute("UPDATE scope2_emissions SET co2e_market_based = co2e WHERE co2e_market_based IS NULL")


def downgrade():
    pass
