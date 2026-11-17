"""Scope 2 gas masses and production-data terms of marketed gas

Revision ID: l7c2e5f83b14
Revises: k6b1d4e72a90
Create Date: 2026-11-17 12:00:00.000000

Blind audit 2026-11-17:
- BA-009: a Scope 2 record kept CO2e only, so steam CO2 / CH4 / N2O were reported as all CO2 and a GWP change
  could not re-weight them. scope2_emissions gains the gas masses (tonnes) the calculation produced.
- BA-053 / BA-054: methane intensity on the OGCI / OGMP volume basis divides by marketed gas = gross - injected -
  flared - vented - on-site fuel - NGL shrinkage. production_data gains the terms it did not have (production
  data takes priority; emission records are the fallback).
Columns are added only when missing; existing rows keep NULL / 0 (no recalculation).
"""

import sqlalchemy as sa
from alembic import op

revision = "l7c2e5f83b14"
down_revision = "k6b1d4e72a90"
branch_labels = None
depends_on = None

_SCOPE2 = ("co2_emissions", "ch4_emissions", "n2o_emissions")
_PRODUCTION = ("flared_gas_mmsm3", "vented_gas_mmsm3", "fuel_gas_consumed_mmsm3", "ngl_shrinkage_mmsm3")


def _add(table, column):
    from schema_sync import has_column, has_table

    bind = op.get_bind()
    if has_table(bind, table) and not has_column(bind, table, column.name):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(column)


def _drop(table, name):
    from schema_sync import has_column, has_table

    bind = op.get_bind()
    if has_table(bind, table) and has_column(bind, table, name):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_column(name)


def upgrade():
    for name in _SCOPE2:
        _add("scope2_emissions", sa.Column(name, sa.Float(), nullable=True))
    for name in _PRODUCTION:
        _add("production_data", sa.Column(name, sa.Float(), nullable=True))


def downgrade():
    for name in _PRODUCTION:
        _drop("production_data", name)
    for name in _SCOPE2:
        _drop("scope2_emissions", name)
