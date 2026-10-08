"""Add import_mappings (saved column mappings of the import wizard).

Revision ID: c3f9a2d18e47
Revises: b7e2d4c91a05
Create Date: 2026-10-08
"""
import sqlalchemy as sa
from alembic import op

revision = "c3f9a2d18e47"
down_revision = "b7e2d4c91a05"
branch_labels = None
depends_on = None


def upgrade():
    from schema_sync import has_table

    bind = op.get_bind()
    if has_table(bind, "import_mappings"):
        return
    op.create_table(
        "import_mappings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False, server_default="1"),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("headers", sa.Text(), nullable=False),
        sa.Column("mapping", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("user_id", "scope", "name", name="uq_import_mapping_user_scope_name"),
    )
    op.create_index("ix_import_mappings_user_id", "import_mappings", ["user_id"])


def downgrade():
    op.drop_index("ix_import_mappings_user_id", table_name="import_mappings")
    op.drop_table("import_mappings")
