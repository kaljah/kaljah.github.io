"""GB RY 2022 validation fixes: facility gas, flared volume split, JV partner archive, grid factors

Revision ID: n9e4a2b6c1d7
Revises: m8d3f6a94c25
Create Date: 2026-11-21 12:00:00.000000

- facilities.gas_ch4_mol_pct / gas_hhv_btu_scf: the facility's own gas for NGSI (D7)
- production_data.routine_ / non_routine_ / safety_flared_mmsm3: flared volume by flaring type (GB-054)
- jv_partners.is_archived: administrators archive partners instead of deleting them (D9)
- grid_factors: administrator-entered, dated and cited grid averages, used once approved (D3 / D4)
Columns are added only when missing; existing rows keep NULL (archived: false).
"""

import sqlalchemy as sa
from alembic import op

revision = "n9e4a2b6c1d7"
down_revision = "m8d3f6a94c25"
branch_labels = None
depends_on = None

_COLUMNS = [
    ("facilities", sa.Column("gas_ch4_mol_pct", sa.Float(), nullable=True)),
    ("facilities", sa.Column("gas_hhv_btu_scf", sa.Float(), nullable=True)),
    ("production_data", sa.Column("routine_flared_mmsm3", sa.Float(), nullable=True)),
    ("production_data", sa.Column("non_routine_flared_mmsm3", sa.Float(), nullable=True)),
    ("production_data", sa.Column("safety_flared_mmsm3", sa.Float(), nullable=True)),
    ("jv_partners", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false())),
]


def upgrade():
    from schema_sync import has_column, has_table

    bind = op.get_bind()
    for table, column in _COLUMNS:
        if has_table(bind, table) and not has_column(bind, table, column.name):
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.add_column(column.copy())
    if not has_table(bind, "grid_factors"):
        op.create_table(
            "grid_factors",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(120), nullable=False, index=True),
            sa.Column("country", sa.String(100), nullable=True, index=True),
            sa.Column("level", sa.String(20), nullable=False, server_default="national"),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("co2", sa.Float(), nullable=False),
            sa.Column("ch4", sa.Float(), nullable=True),
            sa.Column("n2o", sa.Float(), nullable=True),
            sa.Column("source", sa.String(255), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="Pending"),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("tenant_id", sa.String(64), nullable=False, server_default="default", index=True),
        )


def downgrade():
    from schema_sync import has_column, has_table

    bind = op.get_bind()
    if has_table(bind, "grid_factors"):
        op.drop_table("grid_factors")
    for table, column in reversed(_COLUMNS):
        if has_table(bind, table) and has_column(bind, table, column.name):
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.drop_column(column.name)
