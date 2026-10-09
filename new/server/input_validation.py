"""
Central input validation (audit root cause RC-1).

- ``ValidationError`` is turned into HTTP 400 ``{"error": ...}`` by the handler registered in app.py,
  so route code can call the parsers without try/except boilerplate.
- ``find_non_finite`` backs a request guard that rejects NaN / ±Infinity anywhere in a JSON body
  (``float("NaN")`` and ``float("1e999")`` both parse, and pass ``value < 0`` checks).
- ``sanitize_non_finite`` keeps responses valid JSON even if legacy rows hold non-finite values.
"""
import datetime
import math
import re

_NUMERIC_STRING = re.compile(r"^\s*[+-]?(nan|inf|infinity|(\d+\.?\d*|\.\d+)(e[+-]?\d+)?)\s*$", re.IGNORECASE)

YEAR_MIN = 1900


class ValidationError(ValueError):
    def __init__(self, message, field=None):
        super().__init__(message)
        self.message = message
        self.field = field


def _is_non_finite_value(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, str) and _NUMERIC_STRING.match(value):
        try:
            return not math.isfinite(float(value))
        except ValueError:
            return False
    return False


def choice(value, allowed, field):
    """`value` when it is one of `allowed`, else a ValidationError (400) naming the field."""
    if value not in allowed:
        raise ValidationError(f"'{field}' must be one of: {', '.join(allowed)}", field)
    return value


def decimal_mark_from(form):
    """Decimal format of an uploaded file, chosen in the import wizard: "comma" (1 234,5), "point"
    (1,234.5) or None when not given (API clients: only unambiguous numbers are read; F6)."""
    mark = (form.get("decimal_mark") or "").strip().lower() or None
    if mark not in (None, "comma", "point"):
        raise ValidationError("decimal_mark must be 'comma' or 'point'", "decimal_mark")
    return mark


def xlsx_signature_error(path):
    """Error text when an uploaded .xlsx file does not start like a zip workbook, else None."""
    try:
        with open(path, "rb") as f:
            return None if f.read(4) == b"PK\x03\x04" else "Invalid or corrupted XLSX file"
    except OSError as e:
        return f"Failed to read uploaded file: {e}"


def find_nul(payload, path=""):
    """Dotted path of the first text value holding a NUL character (PostgreSQL refuses it), else None."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            found = find_nul(value, f"{path}.{key}" if path else str(key))
            if found:
                return found
    elif isinstance(payload, list):
        for i, value in enumerate(payload):
            found = find_nul(value, f"{path}[{i}]")
            if found:
                return found
    elif isinstance(payload, str) and "\x00" in payload:
        return path or "value"
    return None


# Common filter parameters and their valid values (pilot check 2026-10-09, F13: 50 read endpoints
# answered 500 to "year=abc", "facility_id=x" and the like). Empty, "all", the null spellings the
# UI may send and the "baseline" year keyword (the configured base year) are left to the route.
_PASS_THROUGH = {"", "all", "null", "none", "undefined", "baseline"}
_QUERY_INT_RANGES = {"year": (1900, 2100), "month": (1, 12), "facility_id": (1, 2**31 - 1),
                     "facilityId": (1, 2**31 - 1)}


def invalid_query_parameter(args, numbers=True):
    """(name, message) of the first NUL character or, with numbers, malformed common filter parameter."""
    for name, value in args.items(multi=True):
        if "\x00" in name or "\x00" in value:
            return name, f"'{name}' contains an invalid character"
        bounds = _QUERY_INT_RANGES.get(name) if numbers else None
        if bounds is None or value.strip().lower() in _PASS_THROUGH:
            continue
        try:
            number = int(value.strip())
        except ValueError:
            return name, f"'{name}' must be a whole number"
        if not bounds[0] <= number <= bounds[1]:
            return name, f"'{name}' must be between {bounds[0]} and {bounds[1]}"
    return None


def find_non_finite(payload, path=""):
    """Return the dotted path of the first NaN/±Infinity value in a JSON payload, else None."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            found = find_non_finite(value, f"{path}.{key}" if path else str(key))
            if found:
                return found
    elif isinstance(payload, list):
        for i, value in enumerate(payload):
            found = find_non_finite(value, f"{path}[{i}]")
            if found:
                return found
    elif _is_non_finite_value(payload):
        return path or "value"
    return None


def sanitize_non_finite(obj):
    """Replace non-finite floats with None, recursively (for JSON responses)."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: sanitize_non_finite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [sanitize_non_finite(v) for v in obj]
    return obj


def parse_number(value, field, *, required=True, min_value=None, max_value=None, default=None):
    """Parse a finite number. Blank/None -> ``default`` when not required."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if required:
            raise ValidationError(f"'{field}' is required", field)
        return default
    if isinstance(value, bool):
        raise ValidationError(f"'{field}' must be a number", field)
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{field}' must be a number", field)
    if not math.isfinite(number):
        raise ValidationError(f"'{field}' must be a finite number", field)
    if min_value is not None and number < min_value:
        raise ValidationError(f"'{field}' must be >= {min_value}", field)
    if max_value is not None and number > max_value:
        raise ValidationError(f"'{field}' must be <= {max_value}", field)
    return number


def parse_year(value, field="year", *, required=True):
    """Reporting year: integer in [1900, current year + 1]."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if required:
            raise ValidationError(f"'{field}' is required", field)
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{field}' must be a year", field)
    if not math.isfinite(number) or number != int(number):
        raise ValidationError(f"'{field}' must be a whole year", field)
    year = int(number)
    max_year = datetime.date.today().year + 1
    if not YEAR_MIN <= year <= max_year:
        raise ValidationError(f"'{field}' must be between {YEAR_MIN} and {max_year}", field)
    return year


def parse_month(value, field="month", *, required=False):
    if value is None or (isinstance(value, str) and value.strip() == ""):
        if required:
            raise ValidationError(f"'{field}' is required", field)
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValidationError(f"'{field}' must be a month number", field)
    if not math.isfinite(number) or number != int(number) or not 1 <= int(number) <= 12:
        raise ValidationError(f"'{field}' must be between 1 and 12", field)
    return int(number)


def require_text(value, field):
    text = str(value or "").strip()
    if not text:
        raise ValidationError(f"'{field}' is required", field)
    return text


# GHG Protocol Scope 3 categories (canonical storage form: "Category N").
SCOPE3_CATEGORY_NAMES = {
    1: "purchased goods and services",
    2: "capital goods",
    3: "fuel- and energy-related activities",
    4: "upstream transportation and distribution",
    5: "waste generated in operations",
    6: "business travel",
    7: "employee commuting",
    8: "upstream leased assets",
    9: "downstream transportation and distribution",
    10: "processing of sold products",
    11: "use of sold products",
    12: "end-of-life treatment of sold products",
    13: "downstream leased assets",
    14: "franchises",
    15: "investments",
}
_CATEGORY_NUMBER = re.compile(r"^\s*(?:cat(?:egory)?\.?\s*)?(\d{1,2})\s*$", re.IGNORECASE)
# "Category 1: Purchased goods", "Cat 6 - Business travel"
_CATEGORY_PREFIX = re.compile(r"^\s*cat(?:egory)?\.?\s*(\d{1,2})\s*[-:–.)]\s*\S", re.IGNORECASE)


def scope3_category_number(value):
    """Return the GHG Protocol category number (1-15) for any accepted spelling, else None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(value) and value == int(value):
        number = int(value)
        return number if 1 <= number <= 15 else None
    text = str(value).strip()
    m = _CATEGORY_NUMBER.match(text) or _CATEGORY_PREFIX.match(text)
    if m:
        number = int(m.group(1))
        return number if 1 <= number <= 15 else None
    key = re.sub(r"\s+", " ", text.lower().replace("&", "and")).strip()
    key = re.sub(r"^category\s*\d+\s*[-:–]\s*", "", key)
    for number, name in SCOPE3_CATEGORY_NAMES.items():
        if key == name or key.replace("-", " ") == name.replace("-", " "):
            return number
    return None


def normalize_scope3_category(value, field="category"):
    """Canonical "Category N" (BUG-089: UI stored "6", bulk stored "Category 6")."""
    number = scope3_category_number(value)
    if number is None:
        raise ValidationError(f"'{field}' must be a GHG Protocol Scope 3 category (1-15)", field)
    return f"Category {number}"


def merge_inputs(stored, edit):
    """Merge a ``calc_inputs`` block from an edit over the stored one, process by process.

    An edit may carry only some inputs of a process (the Reports edit modal sends just
    amount/unit/fuel). Replacing the stored block would drop the process-specific inputs
    (e.g. ``agr_co2_in``) and the recalculation would fail. Anything that is not a dict
    of dicts is taken from the edit unchanged.
    """
    if not isinstance(stored, dict) or not isinstance(edit, dict):
        return edit
    merged = dict(stored)
    for proc, vals in edit.items():
        old = merged.get(proc)
        merged[proc] = {**old, **vals} if isinstance(old, dict) and isinstance(vals, dict) else vals
    return merged


def require_plausible_co2e(*values, field="co2e"):
    """Refuse a record whose tCO2e is above the hard plausibility bound (the Scope 1 rule, BUG-007):
    1e300 kWh or bbl of Scope 2 / 3 activity was stored as a 1e296 t record."""
    from calculations.anomaly import plausibility_check

    for value in values:
        verdict, message = plausibility_check(value)
        if verdict == "reject":
            raise ValidationError(message, field)
