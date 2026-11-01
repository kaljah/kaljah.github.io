"""add_part2_period_lock_recalc_versioning

Revision ID: f1b82d47c3e1
Revises: e4a719c28b3d
Create Date: 2026-11-01 13:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f1b82d47c3e1'
down_revision = 'e4a719c28b3d'
branch_labels = None
depends_on = None


def _bind():
    return op.get_bind()


def _add_col(table, column):
    from schema_sync import has_column, has_table

    if has_table(_bind(), table) and not has_column(_bind(), table, column.name):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(column)


def upgrade():
    # 1. Custom factors versioning
    _add_col("custom_factors", sa.Column("valid_from", sa.String(20), nullable=True))
    _add_col("custom_factors", sa.Column("parent_factor_id", sa.Integer(), nullable=True))

    # 2. Scope 1 prior period adjustment
    _add_col("emissions", sa.Column("is_prior_period_adjustment", sa.Boolean(), server_default="0", nullable=False))
    _add_col("emissions", sa.Column("prior_period_year", sa.Integer(), nullable=True))

    # 3. Scope 2 versioning & prior period adjustment
    _add_col("scope2_emissions", sa.Column("factor_version", sa.String(50), nullable=True))
    _add_col("scope2_emissions", sa.Column("factor_source", sa.String(100), nullable=True))
    _add_col("scope2_emissions", sa.Column("gwp_version", sa.String(20), server_default="AR5", nullable=True))
    _add_col("scope2_emissions", sa.Column("is_prior_period_adjustment", sa.Boolean(), server_default="0", nullable=False))
    _add_col("scope2_emissions", sa.Column("prior_period_year", sa.Integer(), nullable=True))

    # 4. Scope 3 versioning & prior period adjustment
    _add_col("scope3_emissions", sa.Column("factor_version", sa.String(50), nullable=True))
    _add_col("scope3_emissions", sa.Column("factor_source", sa.String(100), nullable=True))
    _add_col("scope3_emissions", sa.Column("gwp_version", sa.String(20), server_default="AR5", nullable=True))
    _add_col("scope3_emissions", sa.Column("is_prior_period_adjustment", sa.Boolean(), server_default="0", nullable=False))
    _add_col("scope3_emissions", sa.Column("prior_period_year", sa.Integer(), nullable=True))

    # 5. Period locks table
    from schema_sync import has_table
    if not has_table(_bind(), "period_locks"):
        op.create_table(
            "period_locks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("year", sa.Integer(), nullable=False, index=True),
            sa.Column("month", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(20), server_default="locked", nullable=False),
            sa.Column("locked_at", sa.DateTime(), nullable=True),
            sa.Column("locked_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("signoff_signatory", sa.String(120), nullable=True),
            sa.Column("signoff_notes", sa.Text(), nullable=True),
            sa.Column("unlocked_at", sa.DateTime(), nullable=True),
            sa.Column("unlocked_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("unlock_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    # 6. Recalculation requests table
    if not has_table(_bind(), "recalculation_requests"):
        op.create_table(
            "recalculation_requests",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("target_year", sa.Integer(), nullable=True),
            sa.Column("target_facility_id", sa.Integer(), sa.ForeignKey("facilities.id"), nullable=True),
            sa.Column("target_scope", sa.String(20), nullable=True),
            sa.Column("target_factor_id", sa.Integer(), sa.ForeignKey("custom_factors.id"), nullable=True),
            sa.Column("target_factor_version", sa.String(50), nullable=True),
            sa.Column("target_gwp_standard", sa.String(20), nullable=True),
            sa.Column("trigger_type", sa.String(50), nullable=False),
            sa.Column("justification", sa.Text(), nullable=False),
            sa.Column("status", sa.String(30), server_default="pending_approval", nullable=False),
            sa.Column("records_affected", sa.Integer(), server_default="0", nullable=False),
            sa.Column("tco2e_before", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("tco2e_after", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("delta_tco2e", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("delta_pct", sa.Float(), server_default="0.0", nullable=False),
            sa.Column("requested_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("requested_at", sa.DateTime(), nullable=True),
            sa.Column("approved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
        )

    # 7. Recalculation history table
    if not has_table(_bind(), "recalculation_history"):
        op.create_table(
            "recalculation_history",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("request_id", sa.Integer(), sa.ForeignKey("recalculation_requests.id"), nullable=True, index=True),
            sa.Column("record_id", sa.String(50), nullable=False, index=True),
            sa.Column("scope", sa.Integer(), nullable=False),
            sa.Column("facility_id", sa.Integer(), nullable=True),
            sa.Column("year", sa.Integer(), nullable=True),
            sa.Column("old_co2e", sa.Float(), nullable=False),
            sa.Column("new_co2e", sa.Float(), nullable=False),
            sa.Column("old_factor_version", sa.String(50), nullable=True),
            sa.Column("new_factor_version", sa.String(50), nullable=True),
            sa.Column("old_gwp_version", sa.String(20), nullable=True),
            sa.Column("new_gwp_version", sa.String(20), nullable=True),
            sa.Column("timestamp", sa.DateTime(), nullable=True),
        )


def downgrade():
    pass
