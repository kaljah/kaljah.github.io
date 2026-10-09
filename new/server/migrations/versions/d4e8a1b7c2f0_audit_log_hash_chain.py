"""Tamper-evident audit log: hash chain columns, seal existing rows, append-only on PostgreSQL.

Pilot check 2026-10-09 (F12). Existing rows are sealed in id order when this migration runs: the chain
attests to the log from that moment on, not to edits made before it. On PostgreSQL a trigger refuses
UPDATE, DELETE and TRUNCATE on activity_log, except clearing user_id (user deletion keeps the stored
user name). A later migration that must rewrite audit rows drops and recreates the trigger.

Revision ID: d4e8a1b7c2f0
Revises: c3f9a2d18e47
Create Date: 2026-10-09
"""
from types import SimpleNamespace

import sqlalchemy as sa
from alembic import op

revision = "d4e8a1b7c2f0"
down_revision = "c3f9a2d18e47"
branch_labels = None
depends_on = None

_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION activity_log_append_only() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'UPDATE' AND NEW.user_id IS NULL AND OLD.user_id IS NOT NULL
       AND (to_jsonb(NEW) - 'user_id') = (to_jsonb(OLD) - 'user_id') THEN
        RETURN NEW;  -- user deletion: the entry keeps its user_name, only the link goes
    END IF;
    RAISE EXCEPTION 'activity_log is append-only (% refused)', TG_OP;
END;
$$ LANGUAGE plpgsql;
"""


def upgrade():
    from schema_sync import has_column
    from services.audit_chain import GENESIS_HASH, compute_entry_hash

    bind = op.get_bind()
    if not has_column(bind, "activity_log", "entry_hash"):
        op.add_column("activity_log", sa.Column("prev_hash", sa.String(64), nullable=True))
        op.add_column("activity_log", sa.Column("entry_hash", sa.String(64), nullable=True))

    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS activity_log_append_only ON activity_log")
        op.execute("DROP TRIGGER IF EXISTS activity_log_no_truncate ON activity_log")

    # seal the rows written before this migration, oldest first
    rows = bind.execute(sa.text(
        "SELECT id, action, record_id, user_name, details, old_values, new_values, ip_address, entity, "
        "entity_id, facility_id, metadata, timestamp FROM activity_log ORDER BY id"
    )).mappings().all()
    prev = GENESIS_HASH
    for r in rows:
        log = SimpleNamespace(**dict(r))
        log.metadata_json = r["metadata"]
        entry = compute_entry_hash(log, prev)
        bind.execute(sa.text("UPDATE activity_log SET prev_hash = :p, entry_hash = :h WHERE id = :i"),
                     {"p": prev, "h": entry, "i": r["id"]})
        prev = entry

    if bind.dialect.name == "postgresql":
        op.execute(_TRIGGER_FUNCTION)
        op.execute("CREATE TRIGGER activity_log_append_only BEFORE UPDATE OR DELETE ON activity_log "
                   "FOR EACH ROW EXECUTE FUNCTION activity_log_append_only()")
        op.execute("CREATE TRIGGER activity_log_no_truncate BEFORE TRUNCATE ON activity_log "
                   "FOR EACH STATEMENT EXECUTE FUNCTION activity_log_append_only()")


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS activity_log_append_only ON activity_log")
        op.execute("DROP TRIGGER IF EXISTS activity_log_no_truncate ON activity_log")
        op.execute("DROP FUNCTION IF EXISTS activity_log_append_only()")
    op.drop_column("activity_log", "entry_hash")
    op.drop_column("activity_log", "prev_hash")
