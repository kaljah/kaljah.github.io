"""add_ogmp2_level4_level5_tables

Revision ID: j5f0c2d41b23
Revises: i4e9b1c30a12
Create Date: 2026-11-11 23:50:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "j5f0c2d41b23"
down_revision = "i4e9b1c30a12"
branch_labels = None
depends_on = None


_NEW_TABLES = (
    "ogmp_audit_trails",
    "ogmp_implementation_plans",
    "ogmp_site_measurements",
    "ogmp_emission_sources",
    "ogmp_asset_reports",
    "ogmp_annual_reports",
    "ogmp_assets",
    "ogmp_targets",
    "ogmp_reporting_entities",
)


def _create_index_if_missing(bind, table, name, cols):
    from schema_sync import has_column, has_index, has_table

    if not has_table(bind, table):
        return
    if not all(has_column(bind, table, c) for c in cols):
        return
    if not has_index(bind, table, name):
        op.create_index(name, table, list(cols), unique=False)


def upgrade():
    from schema_sync import has_table

    bind = op.get_bind()

    if not has_table(bind, "ogmp_reporting_entities"):
        op.create_table(
            "ogmp_reporting_entities",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("facility_id", sa.Integer(), nullable=True),
            sa.Column("entity_name", sa.String(length=160), nullable=False),
            sa.Column("asset_name", sa.String(length=160), nullable=True),
            sa.Column("segment", sa.String(length=50), nullable=True),
            sa.Column("sub_segment", sa.String(length=100), nullable=True),
            sa.Column("country", sa.String(length=100), nullable=True),
            sa.Column("operator_status", sa.String(length=20), nullable=True),
            sa.Column("operating_company", sa.String(length=160), nullable=True),
            sa.Column("working_interest_pct", sa.Float(), nullable=True),
            sa.Column("has_operational_control", sa.Boolean(), nullable=True),
            sa.Column("membership_year", sa.Integer(), nullable=True),
            sa.Column("target_gold_year", sa.Integer(), nullable=True),
            sa.Column("is_nojv_material_excluded", sa.Boolean(), nullable=True),
            sa.Column("exclusion_reason", sa.Text(), nullable=True),
            sa.Column("is_member_reported_nojv", sa.Boolean(), nullable=True),
            sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, "ogmp_reporting_entities", "ix_ogmp_reporting_entities_facility_id", ["facility_id"])
    _create_index_if_missing(bind, "ogmp_reporting_entities", "ix_ogmp_reporting_entities_tenant_id", ["tenant_id"])

    if not has_table(bind, "ogmp_targets"):
        op.create_table(
            "ogmp_targets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("reporting_entity_id", sa.Integer(), nullable=False),
            sa.Column("target_year", sa.Integer(), nullable=False),
            sa.Column("metric_type", sa.String(length=50), nullable=True),
            sa.Column("upstream_target_pct", sa.Float(), nullable=True),
            sa.Column("midstream_target_pct", sa.Float(), nullable=True),
            sa.Column("reduction_target_pct", sa.Float(), nullable=True),
            sa.Column("base_year", sa.Integer(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["reporting_entity_id"], ["ogmp_reporting_entities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, "ogmp_targets", "ix_ogmp_targets_reporting_entity_id", ["reporting_entity_id"])
    _create_index_if_missing(bind, "ogmp_targets", "ix_ogmp_targets_tenant_id", ["tenant_id"])

    if not has_table(bind, "ogmp_assets"):
        op.create_table(
            "ogmp_assets",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("reporting_entity_id", sa.Integer(), nullable=False),
            sa.Column("facility_id", sa.Integer(), nullable=False),
            sa.Column("asset_code", sa.String(length=64), nullable=True),
            sa.Column("asset_name", sa.String(length=160), nullable=False),
            sa.Column("asset_type", sa.String(length=80), nullable=True),
            sa.Column("segment", sa.String(length=50), nullable=True),
            sa.Column("operator_status", sa.String(length=20), nullable=True),
            sa.Column("equity_share_pct", sa.Float(), nullable=True),
            sa.Column("is_nojv", sa.Boolean(), nullable=True),
            sa.Column("is_excluded_below_5pct", sa.Boolean(), nullable=True),
            sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["reporting_entity_id"], ["ogmp_reporting_entities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, "ogmp_assets", "ix_ogmp_assets_reporting_entity_id", ["reporting_entity_id"])
    _create_index_if_missing(bind, "ogmp_assets", "ix_ogmp_assets_facility_id", ["facility_id"])
    _create_index_if_missing(bind, "ogmp_assets", "ix_ogmp_assets_tenant_id", ["tenant_id"])

    if not has_table(bind, "ogmp_annual_reports"):
        op.create_table(
            "ogmp_annual_reports",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("facility_id", sa.Integer(), nullable=False),
            sa.Column("reporting_entity_id", sa.Integer(), nullable=True),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("reporting_level", sa.Integer(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=True),
            sa.Column("total_bottom_up_tch4", sa.Float(), nullable=True),
            sa.Column("total_top_down_tch4", sa.Float(), nullable=True),
            sa.Column("bu_uncertainty_pct", sa.Float(), nullable=True),
            sa.Column("bu_ci_low_tch4", sa.Float(), nullable=True),
            sa.Column("bu_ci_high_tch4", sa.Float(), nullable=True),
            sa.Column("td_uncertainty_pct", sa.Float(), nullable=True),
            sa.Column("td_ci_low_tch4", sa.Float(), nullable=True),
            sa.Column("td_ci_high_tch4", sa.Float(), nullable=True),
            sa.Column("ci_overlaps", sa.Boolean(), nullable=True),
            sa.Column("variance_pct", sa.Float(), nullable=True),
            sa.Column("variance_flag", sa.Boolean(), nullable=True),
            sa.Column("reconciliation_status", sa.String(length=50), nullable=True),
            sa.Column("l4_materiality_pct", sa.Float(), nullable=True),
            sa.Column("l4_justification", sa.Text(), nullable=True),
            sa.Column("pathway_code", sa.String(length=10), nullable=True),
            sa.Column("measurement_mode", sa.String(length=30), nullable=True),
            sa.Column("option_mode", sa.String(length=20), nullable=True),
            sa.Column("gas_production_m3", sa.Float(), nullable=True),
            sa.Column("ch4_intensity_pct", sa.Float(), nullable=True),
            sa.Column("equity_ch4_tch4", sa.Float(), nullable=True),
            sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reporting_entity_id"], ["ogmp_reporting_entities.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, "ogmp_annual_reports", "ix_ogmp_annual_reports_facility_id", ["facility_id"])
    _create_index_if_missing(bind, "ogmp_annual_reports", "ix_ogmp_annual_reports_reporting_entity_id", ["reporting_entity_id"])
    _create_index_if_missing(bind, "ogmp_annual_reports", "ix_ogmp_annual_reports_year", ["year"])
    _create_index_if_missing(bind, "ogmp_annual_reports", "ix_ogmp_annual_reports_tenant_id", ["tenant_id"])
    _create_index_if_missing(bind, "ogmp_annual_reports", "ix_ogmp_annual_fac_yr", ["facility_id", "year"])
    _create_index_if_missing(bind, "ogmp_annual_reports", "ix_ogmp_annual_tenant_yr", ["tenant_id", "year"])

    if not has_table(bind, "ogmp_asset_reports"):
        op.create_table(
            "ogmp_asset_reports",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("annual_report_id", sa.Integer(), nullable=False),
            sa.Column("facility_id", sa.Integer(), nullable=False),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("ogmp_level", sa.Integer(), nullable=True),
            sa.Column("bottom_up_tch4", sa.Float(), nullable=True),
            sa.Column("top_down_tch4", sa.Float(), nullable=True),
            sa.Column("bu_ci_low_tch4", sa.Float(), nullable=True),
            sa.Column("bu_ci_high_tch4", sa.Float(), nullable=True),
            sa.Column("td_ci_low_tch4", sa.Float(), nullable=True),
            sa.Column("td_ci_high_tch4", sa.Float(), nullable=True),
            sa.Column("variance_pct", sa.Float(), nullable=True),
            sa.Column("reconciliation_status", sa.String(length=50), nullable=True),
            sa.Column("l4_coverage_pct", sa.Float(), nullable=True),
            sa.Column("gas_throughput_m3", sa.Float(), nullable=True),
            sa.Column("ch4_intensity_pct", sa.Float(), nullable=True),
            sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["annual_report_id"], ["ogmp_annual_reports.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, "ogmp_asset_reports", "ix_ogmp_asset_reports_annual_report_id", ["annual_report_id"])
    _create_index_if_missing(bind, "ogmp_asset_reports", "ix_ogmp_asset_reports_facility_id", ["facility_id"])
    _create_index_if_missing(bind, "ogmp_asset_reports", "ix_ogmp_asset_reports_year", ["year"])
    _create_index_if_missing(bind, "ogmp_asset_reports", "ix_ogmp_asset_reports_tenant_id", ["tenant_id"])

    if not has_table(bind, "ogmp_emission_sources"):
        op.create_table(
            "ogmp_emission_sources",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("facility_id", sa.Integer(), nullable=False),
            sa.Column("annual_report_id", sa.Integer(), nullable=True),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("segment", sa.String(length=50), nullable=False),
            sa.Column("source_code", sa.String(length=64), nullable=False),
            sa.Column("source_name", sa.String(length=160), nullable=False),
            sa.Column("source_category", sa.String(length=80), nullable=True),
            sa.Column("ogmp_level", sa.Integer(), nullable=True),
            sa.Column("status_flag", sa.String(length=20), nullable=True),
            sa.Column("ch4_tonnes", sa.Float(), nullable=True),
            sa.Column("uncertainty_pct", sa.Float(), nullable=True),
            sa.Column("emission_factor_ref", sa.String(length=160), nullable=True),
            sa.Column("quantification_method", sa.String(length=160), nullable=True),
            sa.Column("pathway_code", sa.String(length=10), nullable=True),
            sa.Column("yoy_change_pct", sa.Float(), nullable=True),
            sa.Column("yoy_explanation", sa.Text(), nullable=True),
            sa.Column("zero_emission_explanation", sa.Text(), nullable=True),
            sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["annual_report_id"], ["ogmp_annual_reports.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, "ogmp_emission_sources", "ix_ogmp_emission_sources_facility_id", ["facility_id"])
    _create_index_if_missing(bind, "ogmp_emission_sources", "ix_ogmp_emission_sources_annual_report_id", ["annual_report_id"])
    _create_index_if_missing(bind, "ogmp_emission_sources", "ix_ogmp_emission_sources_year", ["year"])
    _create_index_if_missing(bind, "ogmp_emission_sources", "ix_ogmp_emission_sources_tenant_id", ["tenant_id"])
    _create_index_if_missing(bind, "ogmp_emission_sources", "ix_ogmp_sources_fac_yr", ["facility_id", "year"])

    if not has_table(bind, "ogmp_site_measurements"):
        op.create_table(
            "ogmp_site_measurements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("facility_id", sa.Integer(), nullable=False),
            sa.Column("annual_report_id", sa.Integer(), nullable=True),
            sa.Column("year", sa.Integer(), nullable=False),
            sa.Column("campaign_date", sa.String(length=20), nullable=False),
            sa.Column("survey_type", sa.String(length=80), nullable=False),
            sa.Column("instrument_vendor", sa.String(length=120), nullable=True),
            sa.Column("measurement_mode", sa.String(length=30), nullable=True),
            sa.Column("option_mode", sa.String(length=20), nullable=True),
            sa.Column("measured_rate_kg_hr", sa.Float(), nullable=False),
            sa.Column("operating_hours_year", sa.Float(), nullable=True),
            sa.Column("annualized_tch4", sa.Float(), nullable=True),
            sa.Column("uncertainty_pct", sa.Float(), nullable=True),
            sa.Column("ci_low_tch4", sa.Float(), nullable=True),
            sa.Column("ci_high_tch4", sa.Float(), nullable=True),
            sa.Column("detection_threshold_kg_hr", sa.Float(), nullable=True),
            sa.Column("meteorological_notes", sa.Text(), nullable=True),
            sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["annual_report_id"], ["ogmp_annual_reports.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, "ogmp_site_measurements", "ix_ogmp_site_measurements_facility_id", ["facility_id"])
    _create_index_if_missing(bind, "ogmp_site_measurements", "ix_ogmp_site_measurements_annual_report_id", ["annual_report_id"])
    _create_index_if_missing(bind, "ogmp_site_measurements", "ix_ogmp_site_measurements_year", ["year"])
    _create_index_if_missing(bind, "ogmp_site_measurements", "ix_ogmp_site_measurements_tenant_id", ["tenant_id"])
    _create_index_if_missing(bind, "ogmp_site_measurements", "ix_ogmp_meas_fac_yr", ["facility_id", "year"])

    if not has_table(bind, "ogmp_implementation_plans"):
        op.create_table(
            "ogmp_implementation_plans",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("facility_id", sa.Integer(), nullable=False),
            sa.Column("reporting_entity_id", sa.Integer(), nullable=True),
            sa.Column("asset_name", sa.String(length=160), nullable=True),
            sa.Column("operator_status", sa.String(length=20), nullable=True),
            sa.Column("base_year", sa.Integer(), nullable=False),
            sa.Column("milestone_horizon", sa.String(length=10), nullable=False),
            sa.Column("planned_year", sa.Integer(), nullable=False),
            sa.Column("target_level", sa.Integer(), nullable=False),
            sa.Column("actual_level", sa.Integer(), nullable=True),
            sa.Column("source_scope", sa.String(length=160), nullable=True),
            sa.Column("methodology_upgrade", sa.String(length=200), nullable=True),
            sa.Column("milestone_status", sa.String(length=40), nullable=True),
            sa.Column("justification", sa.Text(), nullable=True),
            sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["reporting_entity_id"], ["ogmp_reporting_entities.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, "ogmp_implementation_plans", "ix_ogmp_implementation_plans_facility_id", ["facility_id"])
    _create_index_if_missing(bind, "ogmp_implementation_plans", "ix_ogmp_implementation_plans_reporting_entity_id", ["reporting_entity_id"])
    _create_index_if_missing(bind, "ogmp_implementation_plans", "ix_ogmp_implementation_plans_tenant_id", ["tenant_id"])
    _create_index_if_missing(bind, "ogmp_implementation_plans", "ix_ogmp_plan_fac_yr", ["facility_id", "planned_year"])

    if not has_table(bind, "ogmp_audit_trails"):
        op.create_table(
            "ogmp_audit_trails",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("facility_id", sa.Integer(), nullable=True),
            sa.Column("annual_report_id", sa.Integer(), nullable=True),
            sa.Column("entity_type", sa.String(length=64), nullable=False),
            sa.Column("entity_id", sa.String(length=64), nullable=False),
            sa.Column("action", sa.String(length=40), nullable=False),
            sa.Column("actor_id", sa.Integer(), nullable=True),
            sa.Column("actor_name", sa.String(length=160), nullable=True),
            sa.Column("summary", sa.Text(), nullable=False),
            sa.Column("before_json", sa.Text(), nullable=True),
            sa.Column("after_json", sa.Text(), nullable=True),
            sa.Column("tenant_id", sa.String(length=64), server_default="default", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["annual_report_id"], ["ogmp_annual_reports.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
        )
    _create_index_if_missing(bind, "ogmp_audit_trails", "ix_ogmp_audit_trails_facility_id", ["facility_id"])
    _create_index_if_missing(bind, "ogmp_audit_trails", "ix_ogmp_audit_trails_annual_report_id", ["annual_report_id"])
    _create_index_if_missing(bind, "ogmp_audit_trails", "ix_ogmp_audit_trails_tenant_id", ["tenant_id"])
    _create_index_if_missing(bind, "ogmp_audit_trails", "ix_ogmp_audit_fac_created", ["facility_id", "created_at"])

    _create_index_if_missing(
        bind,
        "emissions",
        "ix_emissions_intensity_cov",
        [
            "status",
            "is_test",
            "facility_id",
            "year",
            "process_type",
            "ogmp_level",
            "factor_source",
            "calc_method",
            "qa_flag",
            "co2e_total",
            "co2_emissions",
            "ch4_emissions",
            "n2o_emissions",
        ],
    )

    if bind.dialect.name == "sqlite":
        op.execute(sa.text("ANALYZE"))


def downgrade():
    from schema_sync import has_index, has_table

    bind = op.get_bind()
    if has_table(bind, "emissions") and has_index(bind, "emissions", "ix_emissions_intensity_cov"):
        op.drop_index("ix_emissions_intensity_cov", table_name="emissions")
    for tbl in _NEW_TABLES:
        if has_table(bind, tbl):
            op.drop_table(tbl)
