"""Audit RC-14 foundations: columns later fixes depend on (additive, idempotent).

- users.session_version                       (BUG-114 session revocation)
- emissions.custom_factor_id FK               (BUG-056 factor linkage)
- created_by_name / approved_by_name          (BUG-069 maker-checker evidence survives user deletion)
- scope2/scope3/cap updated_by(_at)           (BUG-067 last-maker segregation)
- cap approved_by / approved_at               (BUG-053 CAP maker-checker)
- custom_factors.is_archived                  (BUG-056 soft archive, ids never reused)
- activity_log.facility_id                    (BUG-038 audit-trail scoping)
- sbti_targets.scope_coverage                 (BUG-019)
- emissions uncertainty components            (BUG-008 / BUG-037)

Existing rows are not rewritten (data policy: block new bad data only).

Revision ID: a1c4e7f20b31
Revises: 9c3e1a7b5d20
Create Date: 2026-09-26
"""
import sqlalchemy as sa
from alembic import op

revision = "a1c4e7f20b31"
down_revision = "9c3e1a7b5d20"
branch_labels = None
depends_on = None


def _bind():
    return op.get_bind()


def _add(table, column):
    from schema_sync import has_column, has_table

    if has_table(_bind(), table) and not has_column(_bind(), table, column.name):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(column)


def _has_fk(table, column, referred):
    insp = sa.inspect(_bind())
    return any(
        fk.get("referred_table") == referred and column in (fk.get("constrained_columns") or [])
        for fk in insp.get_foreign_keys(table)
    )


def upgrade():
    _add("users", sa.Column("session_version", sa.Integer(), nullable=False, server_default="0"))

    for table in ("emissions", "scope2_emissions", "scope3_emissions", "cap_emissions"):
        _add(table, sa.Column("created_by_name", sa.String(255), nullable=True))
        _add(table, sa.Column("approved_by_name", sa.String(255), nullable=True))
    for table in ("scope2_emissions", "scope3_emissions", "cap_emissions"):
        _add(table, sa.Column("updated_by", sa.Integer(), nullable=True))
        _add(table, sa.Column("updated_at", sa.DateTime(), nullable=True))
    _add("cap_emissions", sa.Column("approved_by", sa.Integer(), nullable=True))
    _add("cap_emissions", sa.Column("approved_at", sa.DateTime(), nullable=True))

    for name in ("uncertainty_ad", "uncertainty_ef_co2", "uncertainty_ef_ch4", "uncertainty_ef_n2o"):
        _add("emissions", sa.Column(name, sa.Float(), nullable=True))
    _add("emissions", sa.Column("ef_key", sa.String(200), nullable=True))

    _add("custom_factors", sa.Column("is_archived", sa.Boolean(), nullable=False, server_default="0"))
    _add("activity_log", sa.Column("facility_id", sa.Integer(), nullable=True))
    _add("sbti_targets", sa.Column("scope_coverage", sa.String(10), nullable=False, server_default="S1S2S3"))

    _add("emissions", sa.Column("custom_factor_id", sa.Integer(), nullable=True))
    if not _has_fk("emissions", "custom_factor_id", "custom_factors"):
        with op.batch_alter_table("emissions", schema=None, recreate="auto") as batch_op:
            batch_op.create_foreign_key("fk_emissions_custom_factor_id", "custom_factors", ["custom_factor_id"], ["id"])

    from schema_sync import has_index

    if not has_index(_bind(), "emissions", "ix_emissions_custom_factor_id"):
        op.create_index("ix_emissions_custom_factor_id", "emissions", ["custom_factor_id"])
    if not has_index(_bind(), "activity_log", "ix_activity_log_facility_id"):
        op.create_index("ix_activity_log_facility_id", "activity_log", ["facility_id"])


def downgrade():
    # Additive audit columns; dropping them would destroy maker-checker evidence.
    pass
