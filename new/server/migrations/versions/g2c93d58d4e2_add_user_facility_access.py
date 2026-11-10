"""add_user_facility_access

Revision ID: g2c93d58d4e2
Revises: f1b82d47c3e1
Create Date: 2026-11-09 15:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g2c93d58d4e2'
down_revision = 'f1b82d47c3e1'
branch_labels = None
depends_on = None


def upgrade():
    from schema_sync import has_table
    bind = op.get_bind()
    if not has_table(bind, "user_facility_access"):
        op.create_table(
            "user_facility_access",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("facility_id", sa.Integer(), nullable=False),
            sa.Column("access_level", sa.String(length=32), server_default="operator", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["facility_id"], ["facilities.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "facility_id", name="uq_user_facility_access"),
        )
        op.create_index("ix_user_facility_access_user_id", "user_facility_access", ["user_id"], unique=False)
        op.create_index("ix_user_facility_access_facility_id", "user_facility_access", ["facility_id"], unique=False)


def downgrade():
    from schema_sync import has_table
    bind = op.get_bind()
    if has_table(bind, "user_facility_access"):
        op.drop_table("user_facility_access")
