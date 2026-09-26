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


def scope3_category_number(value):
    """Return the GHG Protocol category number (1-15) for any accepted spelling, else None."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and math.isfinite(value) and value == int(value):
        number = int(value)
        return number if 1 <= number <= 15 else None
    text = str(value).strip()
    m = _CATEGORY_NUMBER.match(text)
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
