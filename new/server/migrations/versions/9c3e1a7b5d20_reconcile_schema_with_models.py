"""Reconcile any database with the current models (idempotent).

Adds every nullable model column and model-declared index that is missing from an
existing table. Safe on fresh databases (created by db.create_all()), on databases
upgraded by the old ad-hoc scripts, and on databases stamped at any earlier revision.

Revision ID: 9c3e1a7b5d20
Revises: 52c620a620d2
Create Date: 2026-09-26

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "9c3e1a7b5d20"
down_revision = "52c620a620d2"
branch_labels = None
depends_on = None


def upgrade():
    from extensions import db
    import models  # noqa: F401  (registers every table on db.metadata)
    from schema_sync import add_missing_columns, create_missing_indexes

    bind = op.get_bind()
    db.metadata.create_all(bind=bind, checkfirst=True)
    add_missing_columns(bind, db.metadata)
    create_missing_indexes(bind, db.metadata)


def downgrade():
    # Reconciliation only adds columns/indexes that the models already declare;
    # there is nothing meaningful to remove.
    pass
