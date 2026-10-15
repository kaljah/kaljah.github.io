"""Query parameters shared by the report exports: one strict reading of year / facility / status.

Bug hunt 2026-10-15 #22, #35, #36: the national inventory and CBAM reports took every record whatever
its status (Pending, Rejected and Draft rows in an official submission), and a malformed year or
facility silently meant "all years / all facilities".
"""
from input_validation import ValidationError

RECORD_STATUSES = ("Verified", "Pending", "Draft", "Rejected")


def report_statuses(raw):
    """Statuses a report covers: `?status=Verified,Pending` (any of RECORD_STATUSES, or "all").
    Default: Verified only."""
    if raw is None or not str(raw).strip():
        return ("Verified",)
    names = [v.strip().capitalize() for v in str(raw).split(",") if v.strip()]
    if names == ["All"]:
        return RECORD_STATUSES
    bad = [v for v in names if v not in RECORD_STATUSES]
    if bad or not names:
        raise ValidationError(f"Unknown record status '{', '.join(bad) or raw}' (use {', '.join(RECORD_STATUSES)} or all)",
                              "status")
    return tuple(dict.fromkeys(names))


def optional_int(value, name, low, high):
    """A whole-number filter: blank or "all" -> None; anything else malformed is refused."""
    if value is None or str(value).strip().lower() in ("", "all"):
        return None
    text = str(value).strip()
    if not text.isdigit() or not low <= int(text) <= high:
        raise ValidationError(f"Invalid {name} filter: '{value}'", name)
    return int(text)


def report_year(value):
    return optional_int(value, "year", 1900, 2200)


def report_facility(value):
    return optional_int(value, "facility_id", 1, 2**31 - 1)
