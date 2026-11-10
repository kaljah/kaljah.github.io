"""add_tenant_id_columns

Revision ID: h3d8e2a19f04
Revises: g2c93d58d4e2
Create Date: 2026-11-10 16:40:00.000000

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "h3d8e2a19f04"
down_revision = "g2c93d58d4e2"
branch_labels = None
depends_on = None


_TENANT_TABLES = (
    "users",
    "facilities",
    "custom_factors",
    "mitigation_records",
    "base_year_recalculations",
    "sbti_targets",
    "jv_partners",
    "period_locks",
    "recalculation_requests",
)


def upgrade():
    from schema_sync import has_column, has_index, has_table

    bind = op.get_bind()
    for table in _TENANT_TABLES:
        if not has_table(bind, table):
            continue
        if not has_column(bind, table, "tenant_id"):
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.add_column(
                    sa.Column(
                        "tenant_id",
                        sa.String(length=64),
                        nullable=False,
                        server_default="default",
                    )
                )
        idx_name = f"ix_{table}_tenant_id"
        if not has_index(bind, table, idx_name):
            op.create_index(idx_name, table, ["tenant_id"], unique=False)


def downgrade():
    from schema_sync import has_column, has_index, has_table

    bind = op.get_bind()
    for table in reversed(_TENANT_TABLES):
        if not has_table(bind, table):
            continue
        idx_name = f"ix_{table}_tenant_id"
        if has_index(bind, table, idx_name):
            op.drop_index(idx_name, table_name=table)
        if has_column(bind, table, "tenant_id"):
            with op.batch_alter_table(table, schema=None) as batch_op:
                batch_op.drop_column("tenant_id")
