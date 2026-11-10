"""add_dashboard_compound_indexes

Revision ID: i4e9b1c30a12
Revises: h3d8e2a19f04
Create Date: 2026-11-10 17:40:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "i4e9b1c30a12"
down_revision = "h3d8e2a19f04"
branch_labels = None
depends_on = None


_INDEX_SPECS = (
    (
        "emissions",
        "ix_emissions_dash_status_test_yr_proc_fac",
        ["status", "is_test", "year", "process_type", "facility_id"],
    ),
    (
        "emissions",
        "ix_emissions_fac_yr_status_test",
        ["facility_id", "year", "status", "is_test"],
    ),
    (
        "scope2_emissions",
        "ix_scope2_dash_status_yr_fac",
        ["status", "year", "facility_id"],
    ),
    (
        "scope3_emissions",
        "ix_scope3_dash_status_yr_fac_cat",
        ["status", "year", "facility_id", "category"],
    ),
    (
        "production_data",
        "ix_prod_dash_test_yr_fac",
        ["is_test", "year", "facility_id"],
    ),
    (
        "facilities",
        "ix_facilities_dash_tenant_test_filters",
        ["tenant_id", "is_test", "activity", "division", "segment"],
    ),
    (
        "ogmp_surveys",
        "ix_ogmp_surveys_fac_yr",
        ["facility_id", "year"],
    ),
    (
        "flaring_details",
        "ix_flaring_details_status_yr_fac",
        ["status", "year", "facility_id"],
    ),
    (
        "mitigation_projects",
        "ix_mitigation_projects_test_yr_fac",
        ["is_test", "year", "facility_id"],
    ),
)


def upgrade():
    from schema_sync import has_column, has_index, has_table

    bind = op.get_bind()
    for table, idx_name, cols in _INDEX_SPECS:
        if not has_table(bind, table):
            continue
        if not all(has_column(bind, table, col) for col in cols):
            continue
        if not has_index(bind, table, idx_name):
            op.create_index(idx_name, table, list(cols), unique=False)

    if bind.dialect.name == "sqlite":
        op.execute(sa.text("ANALYZE"))


def downgrade():
    from schema_sync import has_index, has_table

    bind = op.get_bind()
    for table, idx_name, _cols in reversed(_INDEX_SPECS):
        if has_table(bind, table) and has_index(bind, table, idx_name):
            op.drop_index(idx_name, table_name=table)
