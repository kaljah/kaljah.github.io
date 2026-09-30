"""Never reuse the id of a deleted record on SQLite.

SQLite tables created without AUTOINCREMENT hand out max(id) + 1, so deleting the newest record and
adding another gives the new record the deleted record's id. The audit trail refers to records by id,
so "Ref #98" then pointed at two different records (browser test #17). PostgreSQL sequences never
reuse ids; this guard only acts on SQLite.

A high-water mark per table (table `id_high_water`) is kept on insert. It starts from the larger of
the table's current max id and the highest id the audit log recorded for that entity, so ids that
were already deleted before this guard existed are not reused either.
"""
from sqlalchemy import event, text

from extensions import db

# model -> entity name used in ActivityLog.entity
_GUARDED = {}


def _next_id(connection, table, entity):
    # Both statements are writes: the first takes the database write lock, so concurrent inserts
    # are serialised by SQLite instead of reading the same high-water mark
    connection.execute(text(
        "CREATE TABLE IF NOT EXISTS id_high_water (tbl VARCHAR(64) PRIMARY KEY, last_id INTEGER NOT NULL)"))
    # first use: start above ids the audit log already referenced (possibly deleted since)
    connection.execute(text(
        f"INSERT OR IGNORE INTO id_high_water (tbl, last_id) SELECT :t, MAX("
        f"COALESCE((SELECT MAX(id) FROM {table}), 0), "
        f"COALESCE((SELECT MAX(CAST(record_id AS INTEGER)) FROM activity_log "
        f"WHERE entity = :e AND record_id GLOB '[0-9]*' AND record_id NOT GLOB '*[^0-9]*'), 0))"),
        {"t": table, "e": entity})
    return connection.execute(text(
        f"UPDATE id_high_water SET last_id = MAX(last_id, COALESCE((SELECT MAX(id) FROM {table}), 0)) + 1 "
        "WHERE tbl = :t RETURNING last_id"), {"t": table}).scalar()


def _before_insert(mapper, connection, target):
    if connection.dialect.name != "sqlite" or getattr(target, "id", None) is not None:
        return
    table = mapper.local_table.name
    target.id = _next_id(connection, table, _GUARDED[mapper.class_])


def install():
    from models import CustomFactor, Emission, ProductionData, Scope2Emission, Scope3Emission

    for model, entity in ((Emission, "Emission"), (Scope2Emission, "Scope2Emission"),
                          (Scope3Emission, "Scope3Emission"), (CustomFactor, "CustomFactor"),
                          (ProductionData, "ProductionData")):
        if model not in _GUARDED:
            _GUARDED[model] = entity
            event.listen(model, "before_insert", _before_insert)


__all__ = ["install", "db"]
