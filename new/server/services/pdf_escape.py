"""XML-safe escaping helper for ReportLab Paragraph inputs.

Always strips illegal XML 1.0 control characters and truncates *before*
escaping XML special characters so truncation never splits an entity like
``&lt;`` into ``&l``.
"""

import re
from typing import Any
from xml.sax.saxutils import escape as _xml_escape

_ILLEGAL_XML_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def safe_pdf_text(value: Any, max_len: int | None = None) -> str:
    """Truncate ``value`` first (if ``max_len`` is set) and escape XML markup."""
    if value is None:
        return ""
    text = _ILLEGAL_XML_CHARS_RE.sub("", str(value))
    if max_len is not None and max_len >= 0:
        text = text[:max_len]
    return _xml_escape(text, {'"': "&quot;", "'": "&apos;"})
