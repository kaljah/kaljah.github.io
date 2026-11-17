"""CBAM export activity level

Revision ID: m8d3f6a94c25
Revises: l7c2e5f83b14
Create Date: 2026-11-17 18:00:00.000000

EU 2023/1773 Annex III: the specific embedded emissions of an export are the facility's attributed emissions of
the year divided by its activity level (the tonnes of the good produced in the year). The activity level was not
stored, so a calculated value could not be checked or recalculated later. Added only when missing; existing rows
keep NULL.
"""

import sqlalchemy as sa
from alembic import op

revision = "m8d3f6a94c25"
down_revision = "l7c2e5f83b14"
branch_labels = None
depends_on = None


def upgrade():
    from schema_sync import has_column, has_table

    bind = op.get_bind()
    if has_table(bind, "cbam_product_exports") and not has_column(bind, "cbam_product_exports", "activity_level_tonnes"):
        with op.batch_alter_table("cbam_product_exports", schema=None) as batch_op:
            batch_op.add_column(sa.Column("activity_level_tonnes", sa.Float(), nullable=True))


def downgrade():
    from schema_sync import has_column, has_table

    bind = op.get_bind()
    if has_table(bind, "cbam_product_exports") and has_column(bind, "cbam_product_exports", "activity_level_tonnes"):
        with op.batch_alter_table("cbam_product_exports", schema=None) as batch_op:
            batch_op.drop_column("activity_level_tonnes")
