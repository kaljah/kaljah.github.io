"""base_year per tenant

Revision ID: k6b1d4e72a90
Revises: j5f0c2d41b23
Create Date: 2026-11-16 12:00:00.000000

The model gave base_year a tenant_id and replaced the singleton CHECK (id = 1) with one row per
tenant (uq_base_year_tenant). Databases created before that keep the old table: every BaseYear query
then fails on the missing column, and a second tenant's row is refused by the CHECK. Existing rows
belong to the default tenant.
"""

import sqlalchemy as sa
from alembic import op

revision = "k6b1d4e72a90"
down_revision = "j5f0c2d41b23"
branch_labels = None
depends_on = None


def _rebuild_sqlite(with_tenant):
    """SQLite cannot drop a CHECK constraint in place: copy the rows into a rebuilt table."""
    if with_tenant:
        ddl = (
            "CREATE TABLE base_year_new (id INTEGER NOT NULL, year INTEGER NOT NULL, locked INTEGER, "
            "tenant_id VARCHAR(64) DEFAULT 'default' NOT NULL, created_at DATETIME, PRIMARY KEY (id), "
            "CONSTRAINT uq_base_year_tenant UNIQUE (tenant_id))"
        )
        copy = (
            "INSERT INTO base_year_new (id, year, locked, tenant_id, created_at) "
            "SELECT id, year, locked, 'default', created_at FROM base_year"
        )
    else:
        ddl = (
            "CREATE TABLE base_year_new (id INTEGER NOT NULL, year INTEGER NOT NULL, locked INTEGER, "
            "created_at DATETIME, PRIMARY KEY (id), CONSTRAINT base_year_singleton CHECK (id = 1))"
        )
        copy = "INSERT INTO base_year_new (id, year, locked, created_at) SELECT id, year, locked, created_at FROM base_year"
    op.execute(sa.text(ddl))
    op.execute(sa.text(copy))
    op.execute(sa.text("DROP TABLE base_year"))
    op.execute(sa.text("ALTER TABLE base_year_new RENAME TO base_year"))
    if with_tenant:
        op.execute(sa.text("CREATE INDEX ix_base_year_tenant_id ON base_year (tenant_id)"))


def upgrade():
    from schema_sync import has_column, has_table

    bind = op.get_bind()
    if not has_table(bind, "base_year") or has_column(bind, "base_year", "tenant_id"):
        return
    if bind.dialect.name == "sqlite":
        _rebuild_sqlite(with_tenant=True)
        return
    op.add_column(
        "base_year",
        sa.Column("tenant_id", sa.String(length=64), nullable=False, server_default="default"),
    )
    op.create_index("ix_base_year_tenant_id", "base_year", ["tenant_id"])
    op.execute(sa.text("ALTER TABLE base_year DROP CONSTRAINT IF EXISTS base_year_singleton"))
    op.create_unique_constraint("uq_base_year_tenant", "base_year", ["tenant_id"])


def downgrade():
    from schema_sync import has_column, has_table

    bind = op.get_bind()
    if not has_table(bind, "base_year") or not has_column(bind, "base_year", "tenant_id"):
        return
    rows = bind.execute(sa.text("SELECT COUNT(*) FROM base_year WHERE id <> 1 OR tenant_id <> 'default'")).scalar()
    if rows:
        raise RuntimeError(
            "base_year holds rows of other tenants: the singleton table cannot keep them. "
            "Export or delete them before downgrading."
        )
    if bind.dialect.name == "sqlite":
        _rebuild_sqlite(with_tenant=False)
        return
    op.drop_constraint("uq_base_year_tenant", "base_year", type_="unique")
    op.drop_index("ix_base_year_tenant_id", table_name="base_year")
    op.drop_column("base_year", "tenant_id")
    op.create_check_constraint("base_year_singleton", "base_year", "id = 1")
