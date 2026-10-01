"""Widen emissions.fuel_type to 255 characters.

The column stores the catalog fuel name or the activity-factor label; both exceed 50 characters
("Well Completion - Oil Well with Hydraulic Fracturing (Uncontrolled Venting)", 75). SQLite ignores
VARCHAR lengths, but PostgreSQL refused the INSERT and the whole bulk-import batch failed.

Revision ID: b7e2d4c91a05
Revises: a1c4e7f20b31
Create Date: 2026-10-01
"""
import sqlalchemy as sa
from alembic import op

revision = "b7e2d4c91a05"
down_revision = "a1c4e7f20b31"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return  # SQLite does not enforce VARCHAR lengths
    from schema_sync import has_table

    if has_table(bind, "emissions"):
        op.alter_column("emissions", "fuel_type", existing_type=sa.String(50), type_=sa.String(255),
                        existing_nullable=True)


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        return
    op.alter_column("emissions", "fuel_type", existing_type=sa.String(255), type_=sa.String(50),
                    existing_nullable=True)
