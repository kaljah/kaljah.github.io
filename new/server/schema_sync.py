"""
Idempotent schema helpers shared by Alembic revisions and app startup.

The schema is created by ``db.create_all()`` at import time, which creates missing
tables but never adds columns to existing ones. These helpers make migrations safe
to run against any database (fresh, created by create_all, or upgraded by the old
ad-hoc scripts) by applying only what is actually missing.
"""
import logging

import sqlalchemy as sa

log = logging.getLogger(__name__)


def _inspector(bind):
    return sa.inspect(bind)


def has_table(bind, table):
    return _inspector(bind).has_table(table)


def has_column(bind, table, column):
    if not has_table(bind, table):
        return False
    return column in {c["name"] for c in _inspector(bind).get_columns(table)}


def has_index(bind, table, index):
    if not has_table(bind, table):
        return False
    return index in {i["name"] for i in _inspector(bind).get_indexes(table)}


def _column_ddl(bind, column):
    """Render `name TYPE [DEFAULT ...]` for ALTER TABLE ADD COLUMN (nullable only)."""
    col_type = column.type.compile(dialect=bind.dialect)
    ddl = f'"{column.name}" {col_type}'
    default = column.server_default
    if default is not None and hasattr(default, "arg"):
        arg = default.arg
        value = arg.text if hasattr(arg, "text") else repr(arg)
        ddl += f" DEFAULT {value}"
    return ddl


def add_missing_columns(bind, metadata):
    """Add every model column that is missing from an existing table.

    Only nullable columns (or columns with a server default) are added; a NOT NULL
    column without a default cannot be added to a populated table and is logged instead.
    Returns the list of "table.column" strings that were added.
    """
    added = []
    insp = _inspector(bind)
    existing_tables = set(insp.get_table_names())
    for table in metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        present = {c["name"] for c in insp.get_columns(table.name)}
        for column in table.columns:
            if column.name in present:
                continue
            if not column.nullable and column.server_default is None:
                log.warning("Cannot auto-add NOT NULL column %s.%s without a default", table.name, column.name)
                continue
            bind.execute(sa.text(f'ALTER TABLE "{table.name}" ADD COLUMN {_column_ddl(bind, column)}'))
            added.append(f"{table.name}.{column.name}")
    return added


def create_missing_indexes(bind, metadata):
    """Create model-declared indexes that do not exist yet."""
    created = []
    insp = _inspector(bind)
    existing_tables = set(insp.get_table_names())
    for table in metadata.sorted_tables:
        if table.name not in existing_tables:
            continue
        present = {i["name"] for i in insp.get_indexes(table.name)}
        columns = {c["name"] for c in insp.get_columns(table.name)}
        for index in table.indexes:
            if index.name in present:
                continue
            if not all(c.name in columns for c in index.columns):
                continue
            index.create(bind=bind, checkfirst=True)
            created.append(index.name)
    return created
