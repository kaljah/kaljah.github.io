"""add_uncertainty_ch4_n2o_columns

Revision ID: 61bacaad00dc
Revises: 815d10c5bbe4
Create Date: 2026-07-24 18:14:47.675294

Adds per-GHG uncertainty columns to the emissions table.
- uncertainty_ch4 (Float, nullable) — CH4 relative uncertainty, e.g. 0.20 = ±20%
- uncertainty_n2o (Float, nullable) — N2O relative uncertainty
NULL means "not applicable" (custom or specific-factor emission).
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "61bacaad00dc"
down_revision = "815d10c5bbe4"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("emissions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("uncertainty_ch4", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("uncertainty_n2o", sa.Float(), nullable=True))


def downgrade():
    with op.batch_alter_table("emissions", schema=None) as batch_op:
        batch_op.drop_column("uncertainty_n2o")
        batch_op.drop_column("uncertainty_ch4")
