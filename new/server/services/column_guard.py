"""Length-limited text columns refuse values that PostgreSQL would reject at commit.

Edit routes assign request values straight to model attributes (``record.unit = data["unit"]``).
A value longer than the column, or a list / object, used to fail only at commit on PostgreSQL
(SQLite does not enforce VARCHAR lengths), and the route answered 500 (pilot check 2026-10-09).
The check runs when the attribute is set, so the global ValidationError handler answers 400 and
names the field. Numbers are stored as their text; other values (dates) are kept and length-checked.
"""
from sqlalchemy import String, event

from input_validation import ValidationError


def _guard(column):
    limit = column.type.length

    def check(target, value, oldvalue, initiator):
        if isinstance(value, (dict, list, tuple, set, bytes)):
            raise ValidationError(f"'{column.key}' must be text", column.key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            value = str(value)  # PostgreSQL would write 1e308 out as a 309-digit numeric
        if value is not None and len(value if isinstance(value, str) else str(value)) > limit:
            raise ValidationError(f"'{column.key}' is too long (at most {limit} characters)", column.key)
        return value

    return check


def register(model_base):
    """Attach the check to every length-limited String column of the mapped models."""
    for mapper in model_base.registry.mappers:
        for attr in mapper.column_attrs:
            column = attr.columns[0]
            if isinstance(column.type, String) and column.type.length:
                event.listen(getattr(mapper.class_, attr.key), "set", _guard(column), retval=True)
