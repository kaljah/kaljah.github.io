import os
import time
import threading
import uuid
import csv
import re
import traceback
from openpyxl import load_workbook

from services.scope1_template import DATE_HELP, is_example_value
from calculations.anomaly import plausibility_check


# Job tracker. The running worker keeps the full job in memory; a snapshot is written to a JSON
# file so that another worker process (Gunicorn), or the same server after a restart, can answer
# status and error-file requests.
# Structure: { job_id: { 'status', 'progress', 'processed', 'total', 'skipped': [{row, reason, ...}], 'error_csv_path', 'created_at' } }
upload_jobs = {}
upload_jobs_lock = threading.Lock()

UPLOAD_JOB_DIR = os.environ.get("UPLOAD_JOB_DIR") or os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "upload_jobs"
)
os.makedirs(UPLOAD_JOB_DIR, exist_ok=True)
STALE_JOB_SECONDS = 600  # a job whose worker stopped writing for this long was interrupted
_last_persist = {}


def _job_file(job_id):
    import re

    if not re.fullmatch(r"[A-Za-z0-9-]{1,64}", str(job_id or "")):
        return None
    return os.path.join(UPLOAD_JOB_DIR, f"{job_id}.json")


def _skip_groups(job):
    """Grouped, actionable skip reasons over every skipped row (cached until the list grows)."""
    from services.import_feedback import group_skips

    skipped = job.get("skipped", [])
    cached = job.get("_groups_cache")
    if cached and cached[0] == len(skipped):
        return cached[1]
    groups = group_skips(skipped)
    job["_groups_cache"] = (len(skipped), groups)
    return groups


def _snapshot(job):
    skipped = job.get("skipped", [])
    anomalies = job.get("anomalies", [])
    return {
        "skipped_groups": _skip_groups(job),
        "dry_run": bool(job.get("dry_run")),
        "preview": job.get("preview"),
        "started_at": job.get("created_at"),
        "status": job.get("status", "unknown"),
        "progress": job.get("progress", 0),
        "processed": job.get("processed", 0),
        "total": job.get("total", 0),
        "errors": list(job.get("errors", [])),
        "skipped_count": len(skipped),
        "skipped_preview": list(skipped[:100]),
        "error_csv_path": job.get("error_csv_path"),
        "anomaly_count": len(anomalies),
        "anomalies": list(anomalies[:50]),
        "owner_id": job.get("owner_id"),
        "created_at": job.get("created_at"),
        "heartbeat": time.time(),
    }


def _persist_job(job_id, force=False):
    """Write the job snapshot (at most once a second while running; always when forced)."""
    import json

    now = time.time()
    if not force and now - _last_persist.get(job_id, 0) < 1.0:
        return
    path = _job_file(job_id)
    if not path:
        return
    with upload_jobs_lock:
        job = upload_jobs.get(job_id)
        if job is None:
            return
        snap = _snapshot(job)
    try:
        os.makedirs(UPLOAD_JOB_DIR, exist_ok=True)
        tmp = f"{path}.{os.getpid()}.{threading.get_ident()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(snap, fh, default=str)
        os.replace(tmp, path)
        _last_persist[job_id] = now
    except OSError:
        pass  # the in-memory job still answers for this worker


def _load_job(job_id):
    import json

    path = _job_file(job_id)
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            snap = json.load(fh)
    except (OSError, ValueError):
        return None
    if snap.get("status") == "processing" and time.time() - float(snap.get("heartbeat") or 0) > STALE_JOB_SECONDS:
        snap["status"] = "error"
        snap["errors"] = list(snap.get("errors") or []) + [
            "The import was interrupted (the server stopped while it was running); upload the file again. "
            "Rows are saved together at the end of an import, so none of this job's rows were saved."]
    return snap


def _update_job(job_id, **kwargs):
    with upload_jobs_lock:
        if job_id in upload_jobs:
            upload_jobs[job_id].update(kwargs)
    # progress ticks are throttled; status, results and file paths are written at once
    _persist_job(job_id, force=bool(set(kwargs) - {"processed", "progress", "total"}))


def _append_job_list(job_id, list_key, item):
    with upload_jobs_lock:
        if job_id in upload_jobs:
            upload_jobs[job_id].setdefault(list_key, []).append(item)
    _persist_job(job_id)


def _clean_float(val, default=0.0):
    """
    Robustly parses numbers with currency signs, trailing engineering units,
    thousands separators, European comma decimals, scientific notation,
    zero-width spaces, or adversarial nulls/NaNs.
    Guarantees no NaN or Infinite values leak to calculation engines.
    """
    import math
    import re

    if val is None:
        return default
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return default
        return float(val)

    s = str(val).strip()
    # Strip invisible formatting artifacts
    s = s.replace("\u200b", "").replace("\ufeff", "").replace("\u00a0", " ").strip()
    if not s:
        return default

    # Check for adversarial null representations
    s_lower = s.lower()
    if s_lower in ["-", "n/a", "null", "none", "nan", "nil", "n/d", "na", "#n/a", "--"]:
        return default

    # Remove currency symbols
    s = re.sub(r"[\$\€\£\¥]", "", s).strip()

    # Extract numeric portion if concatenated with units (e.g. "120 kW", "50 m3", "100.5tCO2e")
    unit_match = re.match(r"^([-+]?[0-9.,\s]+(?:[eE][-+]?[0-9]+)?)\s*[a-zA-Z%_/³^0-9]*$", s)
    if unit_match:
        s = unit_match.group(1).strip()

    # Clean internal whitespace
    s = s.replace(" ", "")
    if not s or s in ["-", "+"]:
        return default

    # Handle both comma and dot present
    if "," in s and "." in s:
        if s.rfind(".") > s.rfind(","):
            # e.g. 1,250.50 -> 1250.50
            s = s.replace(",", "")
        else:
            # e.g. 1.250,50 -> 1250.50
            s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        # Check if comma is thousands separator (e.g. 1,000 or 1,234,567)
        if re.match(r"^-?\d{1,3}(,\d{3})+$", s):
            s = s.replace(",", "")
        else:
            # European decimal format: 1234,56 -> 1234.56
            s = s.replace(",", ".")

    try:
        res = float(s)
        if math.isnan(res) or math.isinf(res):
            return default
        return res
    except (ValueError, TypeError):
        return default


from process_categories import NON_COMBUSTION_PROCESSES


_THOUSANDS_NUMBER = re.compile(r"^[-+]?\d{1,3}(,\d{3})+(\.\d+)?([eE][-+]?\d+)?$")
# Decimal format of an import file, chosen per file in the import wizard (pilot check 2026-10-09, F6).
# The old guess read "1,000" as 1000 and "1.000" as 1: a silent 1000x error for a French user either
# way. A number-like text cell is rewritten to point notation by the chosen format; one that does not
# fit it keeps its text plus a reason, so the field is reported as unreadable instead of guessed.
DECIMAL_MARKS = ("comma", "point")
_NUMBER_LIKE = re.compile(r"^[-+]?[\d.,'\s\u00a0\u202f]*\d[\d.,'\s\u00a0\u202f]*$")
_SPACE_GROUPS = re.compile(r"[\s\u00a0\u202f']")
# Without a chosen format a dot is a decimal point (API clients, "14.696" psia); only a comma followed by
# exactly three digits ("1,000": 1000 in English, 1 in French) is refused as ambiguous.
_AMBIGUOUS_NUMBER = re.compile(r"[1-9]\d{0,2},\d{3}")
# identifiers and labels that may look like numbers ("1.2", "001") are never rewritten
_TEXT_COLUMN = re.compile(r"equipment|source|meter|group|facility|date|ref|name|code|region|basin|id$")


def normalize_number_cell(text, decimal_mark=None):
    """Point notation of a number-like cell under the file's decimal format ("comma", "point" or None
    when the uploader did not say). Text that is not number-like is returned unchanged."""
    stripped = text.strip()
    if not _NUMBER_LIKE.match(stripped):
        return text
    sign = stripped[0] if stripped[0] in "+-" else ""
    body = _SPACE_GROUPS.sub("", stripped[len(sign):])
    if decimal_mark == "comma":
        if re.fullmatch(r"\d+", body):
            return sign + body
        if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", body):
            return sign + body.replace(".", "")
        m = re.fullmatch(r"(\d{1,3}(?:\.\d{3})+|\d+),(\d+)", body)
        if m:
            return sign + m.group(1).replace(".", "") + "." + m.group(2)
        return f"{stripped} [not a decimal-comma number: write 1 234,5]"
    if decimal_mark == "point":
        if re.fullmatch(r"\d+(?:\.\d+)?", body):
            return sign + body
        m = re.fullmatch(r"(\d{1,3}(?:,\d{3})+)(\.\d+)?", body)
        if m:
            return sign + m.group(1).replace(",", "") + (m.group(2) or "")
        return f"{stripped} [not a decimal-point number: write 1,234.5]"
    if _AMBIGUOUS_NUMBER.fullmatch(body):
        return f"{stripped} [ambiguous: decimal or thousands separator? Choose the file's decimal format]"
    return text


def _xl_values(ws):
    """Row values of a worksheet, a percent-formatted number as the text Excel shows ("5%" for
    0.05). The value alone is the fraction, which a percentage column (user_unc_co2, trans_loss,
    meter_uncertainty_pct) read as 0.05 %; the text is parsed like a typed percent sign."""
    for row in ws.iter_rows():
        out = []
        for cell in row:
            v = getattr(cell, "value", None)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and "%" in str(getattr(cell, "number_format", "") or ""):
                v = f"{v * 100:.12g}%"
            out.append(v)
        yield tuple(out)


_PERCENT_TEXT = re.compile(r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)\s*%\s*$")


def _percent_field(name):
    """Scope 1 fields entered as a percentage number (2.5 = 2.5 %)."""
    n = str(name).lower()
    return n.endswith("_pct") or n.startswith("user_unc") or "_pct_" in n


# Scope 1 fields that are fractions only (0-1), never percentages
_FRACTION_FIELDS = {"agr_ch4_slip", "ch4_slip", "carbon_content", "ch4_wt_fraction"}


def _percent_text_to_number(name, value):
    """"2.5%" in a Scope 1 input column as the number that column expects (it used to reach the
    calculators as text, and '2.5%' failed with a conversion error).

    Percentage columns (`*_pct`, `user_unc_*`) take X; fraction-only columns X / 100. The other
    columns (contents, compositions, efficiencies) are read as percentages by some calculators
    (activity factors, vent and combustion methods: 0-100) and as fraction-or-percent by the others
    (a value above 1 is a percentage): X above 1 suits both, and X up to 1 is sent as the fraction
    X / 100 (0.5 % must not become the fraction 0.5 = 50 %)."""
    if not isinstance(value, str):
        return value
    m = _PERCENT_TEXT.match(value)
    if not m:
        return value
    x = float(m.group(1))
    n = str(name).lower()
    if _percent_field(n):
        return x
    if n in _FRACTION_FIELDS:
        return x / 100.0
    return x if x > 1.0 else x / 100.0


_TON_ERROR = ("'{v}' is ambiguous in a file: write 'tonne' (metric, 1,000 kg) or 'short_ton' (2,000 lb). "
              "On the forms 'ton' is the short ton, which is 9 % less than a tonne.")


def _is_bare_ton(unit):
    """A unit that says 'ton' / 'tons' without saying which: 'ton', 'tons', 'kg/ton', 't CO2/tons'.
    'short ton', 'long ton', 'metric ton', 'tonne' and 'ton-km' are explicit."""
    u = str(unit or "").strip().lower()
    for explicit in ("short ton", "long ton", "metric ton", "us ton"):
        u = u.replace(explicit, explicit.replace(" ", "_"))
    return any(tok in ("ton", "tons") for tok in re.split(r"[/\s]+", u) if tok)


def _bare_ton_error(row):
    """Row error for a bare 'ton' in any unit column of an uploaded row, else None."""
    for k, v in (row or {}).items():
        key = str(k).lower()
        if isinstance(v, str) and (key == "unit" or key.endswith("unit") or key.endswith("_unit")) and _is_bare_ton(v):
            return _TON_ERROR.format(v=v.strip())
    return None


def _prune_old_jobs(max_age_seconds=86400):
    """Prunes job entries older than max_age_seconds (default 24h), their snapshot files and error CSV files."""
    import json

    now = time.time()
    to_delete = []
    with upload_jobs_lock:
        for jid, job in list(upload_jobs.items()):
            created_at = job.get("created_at", 0)
            if now - created_at > max_age_seconds:
                to_delete.append((jid, job.get("error_csv_path")))
        for jid, _ in to_delete:
            upload_jobs.pop(jid, None)
    try:
        for name in os.listdir(UPLOAD_JOB_DIR):
            path = os.path.join(UPLOAD_JOB_DIR, name)
            if name.endswith(".json") and now - os.path.getmtime(path) > max_age_seconds:
                try:
                    with open(path, encoding="utf-8") as fh:
                        to_delete.append((None, json.load(fh).get("error_csv_path")))
                except (OSError, ValueError):
                    pass
                to_delete.append((None, path))
    except OSError:
        pass
    for jid, csv_path in to_delete:
        for f in (csv_path, _job_file(jid) if jid else None):
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


# -- File layout helpers ---------------------------------------------------------

def _clean_sheet_name(name):
    """Sheet name without the template's emoji / symbol prefix ("📊 Data Entry" -> "data entry")."""
    import re

    return re.sub(r"^[^A-Za-z0-9]+", "", str(name or "")).strip().lower()


def _data_sheet(wb):
    """The data-entry sheet of a workbook: the one named "Data Entry" (with or without the
    template's icon), otherwise the first sheet that is not a reference or Tier 3 sheet."""
    names = {_clean_sheet_name(n): n for n in wb.sheetnames}
    for wanted in ("data entry", "data"):
        if wanted in names:
            return wb[names[wanted]]
    skip = ("facilities", "facility", "instructions", "readme", "gas composition", "tier 3 calculations", "lists")
    for n in wb.sheetnames:
        if _clean_sheet_name(n) not in skip and not n.startswith("⚙"):
            return wb[n]
    return wb.active


def _find_header_row(rows_iterator, max_scan=20):
    """Skip title rows: the header is the first row with at least two filled cells.
    Returns (header_values, header_row_number)."""
    first = None
    for i, row in enumerate(rows_iterator, start=1):
        if first is None:
            first = (row, i)
        if sum(1 for c in row if c not in (None, "") and str(c).strip()) >= 2:
            return row, i
        if i >= max_scan:
            break
    return first if first else ((), 0)


def _is_template_note_row(row_dict):
    """The CSV template's second row describes each column; instruction rows start with [INSTRUCTION]."""
    vals = [str(v).strip() for v in row_dict.values() if v is not None]
    if any(v.upper().startswith("[INSTRUCTION]") for v in vals):
        return True
    return any(v.startswith("Date as YYYY-MM") or v.startswith(DATE_HELP[:40]) for v in vals)


def _canonical_header(header):
    """Field name carried by a header: template tags and unit notes are dropped
    ("[T3-Tank] tank_gor" -> "tank_gor", "Bleed Rate (scf/hr)" -> "bleed_rate")."""
    import re

    h = re.sub(r"^\s*(\[[^\]]*\]\s*)+", "", str(header or ""))
    h = re.sub(r"\([^)]*\)", " ", h)
    h = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", h)  # CamelCase: UnloadDepth -> Unload_Depth
    return re.sub(r"[^a-z0-9]+", "_", h.lower()).strip("_")


# -- Bulk-import integrity helpers (audit RC-13) --------------------------------

_PERIOD_FORMATS = ("%Y-%m", "%Y-%m-%d", "%m/%Y", "%Y/%m")


def _parse_row_period(row):
    """BUG-085 / BUG-111: explicit period parsing with range checks; never a default year.

    Accepts a `date` cell (YYYY-MM, YYYY-MM-DD, MM/YYYY, YYYY/MM) or `year` + `month` columns.
    Returns (year, month, error).
    """
    import datetime as _dt
    from input_validation import ValidationError, parse_month, parse_year

    raw = row.get("date")
    date_str = "" if raw is None else str(raw).strip()
    if isinstance(raw, (_dt.date, _dt.datetime)):
        date_str = raw.strftime("%Y-%m-%d")
    elif date_str.endswith(" 00:00:00"):
        date_str = date_str[:-9]
    try:
        if date_str and date_str.lower() != "none":
            for fmt in _PERIOD_FORMATS:
                try:
                    d = _dt.datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
                return parse_year(d.year), parse_month(d.month, required=True), None
            return None, None, f"Invalid date '{date_str}': use YYYY-MM, YYYY-MM-DD or MM/YYYY"
        year = parse_year(row.get("year"))
        month = parse_month(row.get("month"), required=True)
        return year, month, None
    except ValidationError as err:
        return None, None, err.message


class _InFile(int):
    """Id of a row created earlier in this same file and already flushed (not yet committed): an
    in-file repeat is still "earlier in this file", not a record of the platform."""


# On PostgreSQL, rows of a Scope 1/2/3 import are flushed (not committed) in batches of this size and released
# from the session: the file is still saved in one transaction, but memory no longer grows with the file
# (a 100k-row file held every row object until the end: 1.1 GB peak, 346 MB with batches).
FLUSH_EVERY = 2000
# SQLite has one writer: a flush opens the write transaction and holds the database lock until the commit, so
# every other save would wait (30 s busy timeout) for the whole import. On SQLite the rows stay staged until
# the commit, as before; PostgreSQL locks only the new rows. Tests switch this on to exercise the flush path.
FLUSH_ON_SQLITE = False


def _flush_enabled(session):
    try:
        return FLUSH_ON_SQLITE or session.get_bind().dialect.name != "sqlite"
    except Exception:
        return False


def _flush_pending(session, chunk, maps):
    session.add_all(chunk)
    session.flush()
    ids = {id(o): o.id for o in chunk}
    for m in maps:
        for k, v in m.items():
            if not isinstance(v, int) and id(v) in ids:
                m[k] = _InFile(ids[id(v)])
    for o in chunk:
        session.expunge(o)
    chunk.clear()


def _preview_count(pv, row_dict, mapping):
    def cell(key):
        h = mapping.get(key)
        return row_dict.get(h) if h else None

    if is_example_value(cell("date")):
        pv["examples"] = pv.get("examples", 0) + 1   # template example rows: reported, never imported
        return
    y, m, err = _parse_row_period({"date": cell("date"), "year": cell("year"), "month": cell("month")})
    if err or not y:
        pv["bad_dates"] += 1
    else:
        k = f"{int(y):04d}-{int(m or 1):02d}"
        pv["dates"][k] = pv["dates"].get(k, 0) + 1
    fac = str(cell("facility_name") or "").strip()
    pv["facilities"][fac] = pv["facilities"].get(fac, 0) + 1
    proc = str(cell("process") or "").strip()
    pv["processes"][proc] = pv["processes"].get(proc, 0) + 1


def _preview_summary(pv, rows, skipped_in_sample, headers, mapping, fac_name_map, fac_id_map):
    from services.scope1_calc import SCOPE2_PROCESS_TYPES, normalize_process_type

    def scope2(name):
        n = name.strip().lower()
        return bool(n) and (n in SCOPE2_PROCESS_TYPES or normalize_process_type(n) in SCOPE2_PROCESS_TYPES)

    checked = pv["checked"]
    ok = max(0, checked - skipped_in_sample)
    ratio = (ok / checked) if checked else 0.0
    dates = sorted(pv["dates"])

    def known_fac(name):
        k = name.strip().lower()
        return bool(k) and (k in fac_name_map or k in fac_id_map)

    facilities = [{"name": n or "(blank)", "rows": c, "known": known_fac(n)}
                  for n, c in sorted(pv["facilities"].items(), key=lambda x: -x[1])]
    processes = [{"name": n or "(blank)", "rows": c, "scope2": scope2(n),
                  "known": bool(n) and bool(normalize_process_type(n)) and not scope2(n)}
                 for n, c in sorted(pv["processes"].items(), key=lambda x: -x[1])]
    matched = [h for h in headers if h and h in set(mapping.values())]
    return {
        "rows": rows,
        "checked": checked,
        "checked_ok": ok,
        "checked_skipped": skipped_in_sample,
        "estimated_ok": int(round(rows * ratio)) if checked < rows else ok,
        "estimated_skipped": rows - (int(round(rows * ratio)) if checked < rows else ok),
        "is_estimate": checked < rows,
        "period": {"from": dates[0] if dates else None, "to": dates[-1] if dates else None,
                   "months": len(dates), "unreadable_rows": pv["bad_dates"]},
        "facilities": facilities[:50],
        "unknown_facility_rows": sum(f["rows"] for f in facilities if not f["known"]),
        "processes": processes[:50],
        "unknown_process_rows": sum(p["rows"] for p in processes if not p["known"] and not p["scope2"]),
        "scope2_rows": sum(p["rows"] for p in processes if p["scope2"]),
        "example_rows": pv.get("examples", 0),
        "columns": {"total": len([h for h in headers if h]), "headers": [h for h in headers if h], "matched": matched,
                    "by_name": [h for h in headers if h and h not in matched]},
    }


def _dedupe(batch_keys, key, overwrite, describe):
    """BUG-057: returns ("new", None), ("error", message) or ("update", existing_object_or_id).

    batch_keys maps natural key -> existing DB id, or -> the pending object created earlier in
    this same file, so an in-file repeat updates that row instead of inserting a copy.
    """
    if batch_keys is None or key not in batch_keys:
        return "new", None
    if not overwrite:
        existing = batch_keys[key]
        where = "earlier in this file" if (not isinstance(existing, int) or isinstance(existing, _InFile)) else "in the platform"
        return "error", (f"Duplicate record: {describe} already exists {where}. Enable 'Overwrite Duplicates' to "
                         "replace it, or give each source its own Equipment ID / source reference to keep both.")
    return "update", batch_keys[key]


def _resolve_existing(model, existing):
    from extensions import db

    if existing is None:
        return None
    if isinstance(existing, int):
        obj = db.session.get(model, int(existing))
        if obj is not None and isinstance(existing, _InFile):
            obj._bulk_in_file = True  # flushed earlier in this file: an overwrite is not of a saved record
        return obj
    return existing  # pending object from this file


def _bulk_overwrite(obj, values, user_id, label):
    """BUG-058: overwrite through the maker-checker: back to Pending, approval cleared,
    last maker recorded, old/new values captured in the audit trail."""
    from extensions import db
    from models import User
    from utils import log_activity_and_notify

    old = {k: getattr(obj, k, None) for k in values}
    for k, v in values.items():
        setattr(obj, k, v)
    was_saved = getattr(obj, "id", None) is not None and not getattr(obj, "_bulk_in_file", False)
    obj.status = "Pending"
    obj.approved_by = None
    obj.approved_at = None
    if hasattr(obj, "approved_by_name"):
        obj.approved_by_name = None
    if hasattr(obj, "updated_by"):
        obj.updated_by = user_id
    if was_saved:
        log_activity_and_notify(
            action="BULK_OVERWRITE",
            record_id=str(obj.id),
            details=f"{label} record {obj.id} overwritten by bulk import",
            user=db.session.get(User, user_id),
            entity=type(obj).__name__,
            entity_id=obj.id,
            facility_id=getattr(obj, "facility_id", None),
            old_values=old,
            new_values=values,
        )


def _scope2_key(facility_id, year, month, source_type, grid_region, meter):
    return (facility_id, year, month, (source_type or "electricity").strip().lower(),
            (grid_region or "").strip().lower(), (meter or "").strip().lower())


def _scope3_key(facility_id, year, month, category, sub_category, unit):
    return (facility_id, year, month, (category or "").strip().lower(),
            (sub_category or "").strip().lower(), (unit or "").strip().lower())


def _scope1_key(facility_id, year, month, process_type, fuel, equipment_id, source_ref):
    proc = (process_type or "").strip().lower()
    fuel_k = "" if proc in NON_COMBUSTION_PROCESSES else (fuel or "").strip().lower()
    return (facility_id, year, month, proc, fuel_k, (equipment_id or "").strip().lower(),
            (source_ref or "").strip().lower())



def active_job_count(user_id):
    """Jobs of this user still processing in this worker (audit A-09: per-user upload cap)."""
    with upload_jobs_lock:
        return sum(1 for j in upload_jobs.values()
                   if j.get("owner_id") == user_id and j.get("status") == "processing")


def start_background_upload(
    app,
    file_path,
    original_filename,
    user_id,
    global_factor_type,
    provided_mapping=None,
    scope=1,
    overwrite_duplicates=False,
    decimal_mark=None,
):
    _prune_old_jobs()
    job_id = str(uuid.uuid4())
    with upload_jobs_lock:
        upload_jobs[job_id] = {
            "status": "processing",
            "progress": 0,
            "processed": 0,
            "total": 0,
            "errors": [],  # fatal/global errors
            "skipped": [],  # per-row skip reasons [{row, reason, date, facility, ...}]
            "error_csv_path": None,
            "anomalies": [],  # anomaly-flagged rows
            "created_at": time.time(),
            "owner_id": user_id,  # BUG-076: only the uploader (or an admin) may read the job
        }

    _persist_job(job_id, force=True)

    # Spawn the background thread
    thread = threading.Thread(
        target=_process_file_thread,
        args=(
            app,
            job_id,
            file_path,
            original_filename,
            user_id,
            global_factor_type,
            provided_mapping,
            scope,
            overwrite_duplicates,
        ),
        kwargs={"decimal_mark": decimal_mark},
    )
    thread.daemon = True
    thread.start()

    return job_id


def run_file_check(app, file_path, original_filename, user_id, global_factor_type, provided_mapping=None,
                   scope="1", overwrite_duplicates=False, sample_rows=2000, decimal_mark=None):
    """The "Check file" step: the import in dry-run mode (sample calculated, whole file counted, nothing
    saved), run to completion on its own thread and session. Returns the job status with the preview."""
    job_id = "check-" + str(uuid.uuid4())
    with upload_jobs_lock:
        upload_jobs[job_id] = {"status": "processing", "progress": 0, "processed": 0, "total": 0, "errors": [],
                               "skipped": [], "error_csv_path": None, "anomalies": [], "created_at": time.time(),
                               "owner_id": user_id, "dry_run": True}
    t = threading.Thread(target=_process_file_thread, args=(app, job_id, file_path, original_filename, user_id,
                                                            global_factor_type, provided_mapping, scope,
                                                            overwrite_duplicates),
                         kwargs={"dry_run": True, "sample_rows": sample_rows, "decimal_mark": decimal_mark})
    t.start()
    t.join()
    status = get_job_status(job_id)
    with upload_jobs_lock:
        upload_jobs.pop(job_id, None)
    path = _job_file(job_id)
    if path and os.path.exists(path):
        try:
            os.remove(path)
        except OSError:
            pass
    return status


def _job_view(job_id):
    """The job as this worker knows it, else its snapshot file (another worker or before a restart)."""
    with upload_jobs_lock:
        job = upload_jobs.get(job_id)
        if job is not None:
            return _snapshot(job)
    return _load_job(job_id)


def get_job_owner(job_id):
    job = _job_view(job_id)
    return job.get("owner_id") if job else None


def get_job_error_csv_path(job_id):
    job = _job_view(job_id)
    path = job.get("error_csv_path") if job else None
    return path if path and os.path.exists(path) else None


def get_job_status(job_id):
    job = _job_view(job_id)
    if not job:
        return None
    return {
        "status": job.get("status", "unknown"),
        "progress": job.get("progress", 0),
        "processed": job.get("processed", 0),
        "total": job.get("total", 0),
        "errors": list(job.get("errors", [])),
        "skipped_count": job.get("skipped_count", 0),
        "skipped_preview": job.get("skipped_preview", []),  # first 100 for inline display
        "has_error_csv": bool(job.get("error_csv_path")),  # BUG-076: no server path disclosure
        "anomaly_count": job.get("anomaly_count", 0),
        "anomalies": job.get("anomalies", []),  # first 50 anomalies for review
        "skipped_groups": job.get("skipped_groups", []),  # every skipped row, grouped by cause, with the fix
        "started_at": job.get("started_at") or job.get("created_at"),
        "dry_run": bool(job.get("dry_run")),
        "preview": job.get("preview"),
    }


def _process_file_thread(
    app,
    job_id,
    file_path,
    original_filename,
    user_id,
    global_factor_type,
    provided_mapping,
    scope=1,
    overwrite_duplicates=False,
    dry_run=False,
    sample_rows=None,
    decimal_mark=None,
):
    """Import a file. dry_run: calculate the first `sample_rows` rows, read every row for the file
    statistics (rows, period, facilities, processes) and save nothing (the "Check file" step)."""
    wb = None
    f = None
    with app.app_context():
        try:
            is_excel = str(original_filename or "").lower().endswith(".xlsx")

            headers = []
            rows_iterator = None
            csv_source = False  # CSV cells are positional by delimiter: an extra one shifts the row
            if decimal_mark not in DECIMAL_MARKS:
                decimal_mark = None  # not chosen: unambiguous numbers only (see normalize_number_cell)

            # 1. Open File & Extract Headers
            tier3_data_map = {}
            if is_excel:
                wb = load_workbook(file_path, read_only=True, data_only=True)

                # Tier 3 / gas composition sheets: parameters per equipment ID (and month), with
                # the same header mapping as the data sheet so the values reach the calculators
                for sheet_name in wb.sheetnames:
                    if _clean_sheet_name(sheet_name) in ("gas composition", "tier 3 calculations") or sheet_name.startswith("⚙"):
                        t3_iter = _xl_values(wb[sheet_name])
                        t3_headers = []
                        for row in t3_iter:
                            str_row = [str(c).strip() if c is not None else "" for c in row]
                            if "equipment id" in [c.lower() for c in str_row]:
                                t3_headers = str_row
                                break
                        if not t3_headers:
                            continue
                        t3_map = _build_mapping(t3_headers, scope=scope)
                        for t3_row in t3_iter:
                            if not any(c not in (None, "") for c in t3_row):
                                continue
                            raw = dict(zip(t3_headers, t3_row))
                            eq_id = str(next((v for k, v in raw.items() if k.lower() == "equipment id"), "") or "").strip()
                            if not eq_id:
                                continue
                            params = {}
                            skip = ("equipment", "equipment_id", "date", "process")
                            raw = {h: (normalize_number_cell(v, decimal_mark) if isinstance(v, str)
                                       and not _TEXT_COLUMN.search(_canonical_header(h) or str(h).lower()) else v)
                                   for h, v in raw.items()}
                            for h, val in raw.items():  # unmapped columns by their field name
                                ck = _canonical_header(h)
                                if ck and ck not in skip and h not in t3_map.values() and val not in (None, "", "-"):
                                    params[ck] = val
                            for sys_key, header_name in t3_map.items():
                                val = raw.get(header_name)
                                if sys_key not in skip and val not in (None, "", "-"):
                                    params[sys_key] = val
                            y, m, _ = _parse_row_period({"date": raw.get(t3_map.get("date"))}) if t3_map.get("date") else (None, None, None)
                            tier3_data_map.setdefault((eq_id, y, m), {}).update(params)

                ws = _data_sheet(wb)
                rows_iterator = _xl_values(ws)
                headers_tuple, header_row_no = _find_header_row(rows_iterator)
                headers = [
                    str(h).strip() if h is not None else "" for h in headers_tuple
                ]

                total_rows = max(0, (ws.max_row or 0) - header_row_no)
            else:
                # Read file bytes with multi-encoding fallback (UTF-8-BOM, UTF-8, Windows-1252, ISO-8859-1)
                with open(file_path, "rb") as raw_f:
                    raw_bytes = raw_f.read()
                decoded_text = None
                for enc in ["utf-8-sig", "utf-8", "windows-1252", "iso-8859-1"]:
                    try:
                        decoded_text = raw_bytes.decode(enc)
                        break
                    except (UnicodeDecodeError, LookupError):
                        continue
                if decoded_text is None:
                    decoded_text = raw_bytes.decode("utf-8", errors="replace")

                # Universal newline normalization (CRLF, legacy CR -> \n)
                decoded_text = decoded_text.replace("\r\n", "\n").replace("\r", "\n")

                import io
                # Delimiter (comma, semicolon, tab, pipe) from the header line only: data rows and
                # the template's description row contain free text ("a | b", "1,5")
                first_line = decoded_text.lstrip("\n").split("\n", 1)[0]
                counts = {d: first_line.count(d) for d in (",", ";", "\t", "|")}
                delimiter = max(counts, key=counts.get) if max(counts.values()) > 0 else ","
                # Excel writes ";"-separated CSV where "," is the decimal separator: there "1,500"
                # is 1.5, not 1500 (audit 2026-09-30). An explicit choice in the wizard wins.
                if decimal_mark is None and delimiter == ";":
                    decimal_mark = "comma"

                f = io.StringIO(decoded_text)
                reader = csv.reader(f, delimiter=delimiter)
                headers = next(reader, [])
                headers = [h.strip() for h in headers]
                header_row_no = 1
                rows_iterator = reader
                csv_source = True
                total_rows = max(0, sum(1 for ln in decoded_text.split("\n") if ln.strip()) - 1)

            if csv_source:
                # rows counted with the CSV reader (quoted cells may span lines) for the progress bar.
                # There is no row limit: the whole file is still saved in one transaction (all or nothing).
                total_rows = sum(1 for _ in csv.reader(io.StringIO(decoded_text), delimiter=delimiter)) - 1
            _update_job(job_id, total=total_rows)

            # Resolve mapping: the automatic mapping, overridden by the columns the user chose in
            # the wizard (the wizard lists only some fields; the others still map automatically)
            mapping = _build_mapping(headers, scope=scope)
            if isinstance(provided_mapping, dict):
                mapping.update({str(k): v for k, v in provided_mapping.items() if isinstance(v, str) and v in headers})

            # 3. Setup context variables for calculation
            from models import (
                Facility,
                CustomFactor,
                User,
            )
            from extensions import db
            from calculations import compute_emissions
            from calculations.constants import get_active_gwp
            from emission_factors import API_FACTORS
            from electricity_factors import GRID_FACTORS
            import json

            user_obj = db.session.get(User, user_id)
            # Invariant Zero (Decision D-09): Active GWP is strictly org-wide; user preference is display-only
            try:
                from routes.auth import _app_settings, load_settings_from_db

                load_settings_from_db()
                gwp_std = str(
                    _app_settings.get("gwp_standard") or "AR5"
                ).upper().strip()
            except Exception:
                gwp_std = "AR5"

            if gwp_std not in ["AR4", "AR5", "AR6"]:
                gwp_std = "AR5"
            gwp_dict = get_active_gwp(standard=gwp_std)
            from utils import get_allowed_facility_ids

            allowed_fac_ids = get_allowed_facility_ids(user_obj)

            if allowed_fac_ids is None:
                all_facilities = Facility.query.all()
            else:
                all_facilities = Facility.query.filter(
                    Facility.id.in_(allowed_fac_ids)
                ).all()

            from utils import build_name_map

            fac_name_map = build_name_map(all_facilities)
            for fac in all_facilities:
                # region names are a convenience alias only when no facility carries that name
                fac_name_map.add(fac.region, fac, overwrite=False)
            fac_id_map = {str(fac.id): fac for fac in all_facilities}

            custom_factors = CustomFactor.query.filter(CustomFactor.is_archived.is_(False)).all()
            cf_name_map = build_name_map(custom_factors)

            processed = 0
            chunk = []
            skipped_rows = []  # Store raw row data for error CSV
            anomaly_rows = []  # Store anomaly-flagged rows for reviewer warning
            batch_prod_map = {}  # In-batch duplicate tracking for production upserts
            batch_cf_names = set()  # BUG-065: in-file duplicate custom factor names
            batch_facilities = {}  # in-file facility names / codes
            batch_sources = set()  # in-file emission sources
            batch_scope1_map = {}
            batch_scope2_map = {}
            batch_scope3_map = {}

            from models import Emission, Scope2Emission, Scope3Emission

            # BUG-081: natural keys include the sub-identifiers real inventories need, and
            # Rejected / Draft rows are not treated as existing records.
            live = ("Pending", "Verified", "Pending Approval")
            if str(scope) == "1":
                for e in Emission.query.filter(Emission.status.in_(live)).with_entities(
                    Emission.id, Emission.facility_id, Emission.year, Emission.month, Emission.process_type,
                    Emission.fuel_type, Emission.equipment_id, Emission.data_source_ref,
                ).all():
                    k = _scope1_key(e.facility_id, e.year, e.month, e.process_type, e.fuel_type, e.equipment_id, e.data_source_ref)
                    batch_scope1_map[k] = e.id

            elif str(scope) == "2":
                for e in Scope2Emission.query.filter(Scope2Emission.status.in_(live)).with_entities(
                    Scope2Emission.id, Scope2Emission.facility_id, Scope2Emission.year, Scope2Emission.month,
                    Scope2Emission.source_type, Scope2Emission.grid_region, Scope2Emission.location,
                ).all():
                    meter = e.location if (e.location or "") != (e.grid_region or "") else ""
                    batch_scope2_map[_scope2_key(e.facility_id, e.year, e.month, e.source_type, e.grid_region, meter)] = e.id

            elif str(scope) in ["3", "3_eeio"]:
                from input_validation import scope3_category_number

                for e in Scope3Emission.query.filter(Scope3Emission.status.in_(live)).with_entities(
                    Scope3Emission.id, Scope3Emission.facility_id, Scope3Emission.year, Scope3Emission.month,
                    Scope3Emission.category, Scope3Emission.sub_category, Scope3Emission.unit,
                ).all():
                    n = scope3_category_number(e.category)
                    cat = f"Category {n}" if n else (e.category or "")
                    batch_scope3_map[_scope3_key(e.facility_id, e.year, e.month, cat, e.sub_category, e.unit)] = e.id

            flush_enabled = _flush_enabled(db.session) and not dry_run
            # dry run: whole-file statistics (cheap) next to the calculated sample
            pv = {"dates": {}, "bad_dates": 0, "facilities": {}, "processes": {}, "checked": 0}
            import math as _math

            sample_step = max(1, _math.ceil((total_rows or 0) / sample_rows)) if (dry_run and sample_rows) else 1

            # Initialize anomaly detector
            from calculations.anomaly import BatchAnomalyDetector, scope1_source
            anomaly_detector = BatchAnomalyDetector()  # history read once per series

            # Headers for error CSV
            error_headers = ["Error Reason"] + headers

            # All or nothing: the rows are saved in one commit at the end of the file, so a fatal
            # error or a server restart never leaves half an import behind. Queries during the
            # import must not flush the staged rows (that would open the write transaction early).
            db.session.autoflush = False

            text_columns = {i for i, h in enumerate(headers) if _TEXT_COLUMN.search(_canonical_header(h) or str(h).lower())}
            for line_no, raw_row in enumerate(rows_iterator, start=header_row_no + 1):
                # Stop if empty row (Excel read_only sometimes yields empty trailing rows, or CSV whitespace-only rows)
                if not any(str(c).strip() for c in raw_row if c is not None):
                    continue

                # Zip headers with row values safely; the templates write "-" for a blank cell
                row_dict = {}
                for i, h in enumerate(headers):
                    v = raw_row[i] if i < len(raw_row) else None
                    if isinstance(v, str) and v.strip() in ("", "-", "--"):
                        v = None
                    elif isinstance(v, str) and i not in text_columns:
                        v = normalize_number_cell(v, decimal_mark)
                    row_dict[h] = v

                if _is_template_note_row(row_dict):
                    continue  # the template's description / instruction row
                processed += 1
                if dry_run:
                    _preview_count(pv, row_dict, mapping)
                    # the sample is spread over the whole file (every k-th row): files are often sorted by
                    # process or source, and the first rows alone misjudged a 100k file (47 % vs 16 % skipped)
                    if sample_rows and sample_step > 1 and (processed - 1) % sample_step:
                        continue  # not in the sample: statistics only
                    pv["checked"] += 1

                # Extract mapped values, preserving raw entries as case/spacing-insensitive fallbacks
                mapped_data = {
                    str(k).lower().replace("_", "").replace(" ", ""): v
                    for k, v in row_dict.items()
                    if k is not None
                }
                mapped_data.update(row_dict)
                # the header's field name ("[T3-Tank] tank_gor" -> tank_gor, "Unit\n(bbl)" -> unit)
                for h, v in row_dict.items():
                    ck = _canonical_header(h)
                    if ck and v is not None and mapped_data.get(ck) in (None, ""):
                        mapped_data[ck] = v
                for sys_key, header_name in mapping.items():
                    if header_name:
                        val = row_dict.get(header_name)
                        if val is not None and str(val).strip() != "":
                            mapped_data[sys_key] = val


                # Merge Tier 3 / Gas Composition if present
                # (keyed by equipment ID and month; a Tier 3 row without a date applies to every month)
                if tier3_data_map:
                    y, m, _ = _parse_row_period(mapped_data)
                    for eq in {str(mapped_data.get(k) or "").strip() for k in ("equipment_id", "equipment")} - {""}:
                        params = tier3_data_map.get((eq, y, m)) or tier3_data_map.get((eq, None, None))
                        if params:
                            for k, v in params.items():
                                if mapped_data.get(k) in (None, ""):
                                    mapped_data[k] = v
                            break

                # a CSV row with more values than the header (an extra delimiter) is shifted: every value
                # after the extra one sits under the wrong column. It was read silently (deep-dive audit).
                overflow = csv_source and any(
                    c is not None and str(c).strip() for c in raw_row[len(headers):])

                # Process Row based on scope
                if overflow:
                    emission_obj = None
                    row_errors = [f"Row {line_no} has {len(raw_row)} values but the header has {len(headers)} "
                                  "columns: check for an extra comma / delimiter (values would shift columns)"]
                elif is_example_value(mapped_data.get("date")):
                    # a template example row left in the file: never a record
                    emission_obj = None
                    row_errors = ["Example row from the template (dated EXAMPLE): not imported"]
                elif str(scope) == "2":
                    emission_obj, row_errors = _process_row_scope2(
                        mapped_data,
                        user_id,
                        fac_name_map,
                        fac_id_map,
                        GRID_FACTORS,
                        job_id,
                        line_no,
                        batch_keys=batch_scope2_map,
                        overwrite_duplicates=overwrite_duplicates,
                    )
                elif str(scope) == "3_eeio":
                    emission_obj, row_errors = _process_row_scope3_eeio(
                        mapped_data,
                        user_id,
                        fac_name_map,
                        fac_id_map,
                        job_id,
                        line_no,
                        batch_keys=batch_scope3_map,
                        overwrite_duplicates=overwrite_duplicates,
                    )
                elif str(scope) == "3":
                    emission_obj, row_errors = _process_row_scope3(
                        mapped_data,
                        user_id,
                        fac_name_map,
                        fac_id_map,
                        job_id,
                        line_no,
                        batch_keys=batch_scope3_map,
                        overwrite_duplicates=overwrite_duplicates,
                    )
                elif str(scope) == "sources":
                    emission_obj, row_errors = _process_row_sources(
                        mapped_data, user_id, fac_name_map, fac_id_map, batch_sources
                    )
                elif str(scope) == "production":
                    emission_obj, row_errors = _process_row_production(
                        mapped_data, user_id, fac_name_map, fac_id_map, batch_prod_map
                    )
                elif str(scope) == "mitigation":
                    emission_obj, row_errors = _process_row_mitigation(
                        mapped_data, user_id, fac_name_map, fac_id_map
                    )
                elif str(scope) == "custom_factors":
                    emission_obj, row_errors = _process_row_custom_factors(
                        mapped_data, user_id, batch_cf_names)
                elif str(scope) == "facilities":
                    emission_obj, row_errors = _process_row_facilities(
                        mapped_data, user_id, overwrite_duplicates, batch_facilities
                    )
                elif str(scope) == "1":
                    emission_obj, row_errors = _process_row(
                        mapped_data,
                        user_id,
                        fac_name_map,
                        fac_id_map,
                        cf_name_map,
                        compute_emissions,
                        API_FACTORS,
                        global_factor_type,
                        gwp_dict=gwp_dict,
                        gwp_std=gwp_std,
                        job_id=job_id,
                        row_idx=line_no,
                        batch_keys=batch_scope1_map,
                        overwrite_duplicates=overwrite_duplicates,
                    )
                else:
                    emission_obj = None
                    row_errors = [
                        f"Unknown scope identifier: '{scope}'. Cannot process row."
                    ]

                if row_errors:
                    skip_entry = {
                        "row": line_no,  # line of the file (header and description rows included)
                        "reason": "; ".join(row_errors),
                        "date": mapped_data.get("date", ""),
                        "year": str(mapped_data.get("year") or ""),
                        "month": str(mapped_data.get("month") or ""),
                        "facility": mapped_data.get("facility_name", ""),
                        "process": mapped_data.get("process", ""),
                        "fuel": mapped_data.get("fuel", ""),
                        "quantity": mapped_data.get("quantity", ""),
                    }
                    _append_job_list(job_id, "skipped", skip_entry)
                    # Also keep flat list for CSV
                    skipped_list = ["; ".join(row_errors)]
                    skipped_list.extend(["" if row_dict.get(h) is None else str(row_dict.get(h)) for h in headers])
                    skipped_rows.append(skipped_list)
                elif emission_obj:
                    chunk.append(emission_obj)
                    # --- Anomaly Detection ---
                    if str(scope) in ["1", "2", "3"]:
                        try:
                            fac_id = getattr(emission_obj, 'facility_id', None)
                            yr = getattr(emission_obj, 'year', 0)
                            mo = getattr(emission_obj, 'month', 0)
                            if scope == "1":
                                co2e_val = getattr(emission_obj, 'co2e_total', 0) or 0
                                anomaly = anomaly_detector.check_scope1(
                                    fac_id, getattr(emission_obj, 'process_type', ''), co2e_val, yr, mo,
                                    source=scope1_source(getattr(emission_obj, 'equipment_id', None),
                                                         getattr(emission_obj, 'fuel_type', None)))
                            elif scope == "2":
                                co2e_val = getattr(emission_obj, 'co2e', 0) or 0
                                anomaly = anomaly_detector.check_scope2(fac_id, getattr(emission_obj, 'source_type', ''), co2e_val, yr, mo)
                            else:  # scope 3
                                co2e_val = getattr(emission_obj, 'co2e', 0) or 0
                                anomaly = anomaly_detector.check_scope3(fac_id, getattr(emission_obj, 'category', ''), co2e_val, yr, mo)

                            if anomaly.get('flagged'):
                                flag_msg = anomaly.get('message') or f"Statistical Anomaly: Z-score {anomaly.get('z_score', 0):.2f}"
                                if len(flag_msg) > 255:
                                    flag_msg = flag_msg[:252] + "..."
                                emission_obj.qa_flag = flag_msg
                                anomaly_rows.append({
                                    "row": line_no,
                                    "facility_id": fac_id,
                                    "value": co2e_val,
                                    "z_score": anomaly.get('z_score'),
                                    "expected_range": anomaly.get('expected_range'),
                                    "message": anomaly.get('message'),
                                })
                        except Exception:
                            pass  # Never let anomaly detection crash the upload
                    # after the anomaly flag is set on the row: flush and release a full batch
                    if str(scope) in ("1", "2", "3", "3_eeio") and len(chunk) >= FLUSH_EVERY and flush_enabled:
                        _flush_pending(db.session, chunk, (batch_scope1_map, batch_scope2_map, batch_scope3_map))


                # Update progress every 100 rows
                if processed % 100 == 0:
                    import time
                    time.sleep(0)  # Yield the GIL so the main Flask thread can handle /status polling API calls
                    _update_job(
                        job_id,
                        processed=processed,
                        progress=min(99, int((processed / total_rows) * 100)) if total_rows > 0 else min(95, int(100 * (1.0 - (0.98 ** (processed / 100.0))))),
                    )

            if dry_run:
                db.session.rollback()  # nothing of a check is saved
                with upload_jobs_lock:
                    n_skip = len(upload_jobs.get(job_id, {}).get("skipped", []))
                _update_job(job_id, processed=processed, progress=100, status="completed", dry_run=True,
                            preview=_preview_summary(pv, processed, n_skip, headers, mapping, fac_name_map, fac_id_map))
                return

            # One commit for the whole file. add_all (not bulk_save_objects): pending objects stay tracked, so
            # an in-file duplicate can update them (BUG-057; rows already flushed are reloaded by id), and the
            # dashboard-cache hook sees the new rows (BUG-071)
            if chunk:
                db.session.add_all(chunk)
            # BUG-058: one IMPORT summary entry per job, committed with the data
            from utils import log_activity_and_notify as _log

            with upload_jobs_lock:
                _skipped_n = len(upload_jobs.get(job_id, {}).get("skipped", []))
            _log(
                action="IMPORT",
                record_id=job_id,
                details=f"Bulk import ({scope}) of '{original_filename}': {processed} rows read, {_skipped_n} skipped",
                user=user_obj,
                entity=f"bulk_scope_{scope}",
                entity_id=job_id,
            )
            db.session.commit()
            try:
                from routes.dashboard import clear_dashboard_cache

                clear_dashboard_cache()  # BUG-071
            except Exception:
                pass

            # --- Maker-Checker: Notify reviewers for bulk Scope 1/2/3 uploads ---
            with upload_jobs_lock:
                _n_skipped = len(upload_jobs.get(job_id, {}).get("skipped", []))
            if str(scope) in ["1", "2", "3", "3_eeio"] and processed - _n_skipped > 0:
                try:
                    from models import User, Notification, Facility
                    uploaded_regions = set()
                    for fac in all_facilities:
                        if fac.region:
                            uploaded_regions.add(fac.region)
                        if fac.location:
                            uploaded_regions.add(fac.location)

                    # Build reviewer list: all active admins (Maker-Checker: only admin approves)
                    reviewers = User.query.filter_by(
                        role="admin",
                        status="active"
                    ).all()

                    with upload_jobs_lock:
                        skipped_count = len(upload_jobs.get(job_id, {}).get("skipped", []))
                    success_count = processed - skipped_count
                    scope_label = "Scope 3" if str(scope) == "3_eeio" else f"Scope {scope}"

                    for reviewer in reviewers:
                        Notification.create(
                            user_id=reviewer.id,
                            type="audit",
                            title=f"{scope_label} Bulk Upload Pending Review",
                            message=(
                                f"{success_count:,} {scope_label} emission records were imported or updated "
                                f"by {user_obj.fullName if user_obj else 'a user'} and are "
                                f"awaiting your approval."
                            ),
                        )
                    db.session.commit()
                except Exception as notif_err:
                    db.session.rollback()
                    import traceback as _tb
                    _tb.print_exc()

            # Generate Error CSV if needed
            if skipped_rows:
                error_file = file_path + "_errors.csv"
                try:
                    with open(error_file, "w", newline="", encoding="utf-8") as ef:
                        writer = csv.writer(ef)
                        writer.writerow(error_headers)
                        # the cells echo the uploaded file, which an admin may open in Excel
                        from routes.audit import sanitize_csv_cell
                        writer.writerows([[sanitize_csv_cell(c) for c in row] for row in skipped_rows])
                    _update_job(job_id, error_csv_path=error_file)
                except OSError:
                    traceback.print_exc()  # the import itself is committed; only the download is missing

            # completed only once the error file and the reviewer notices exist: a client polling the
            # status used to see "completed" and get a 404 for the error file it was about to write
            _update_job(
                job_id,
                processed=processed,
                progress=100,
                status="completed",
                anomalies=anomaly_rows,
            )

        except Exception as e:
            traceback.print_exc()
            try:
                from extensions import db
                db.session.rollback()
            except Exception:
                pass
            with upload_jobs_lock:
                if job_id in upload_jobs:
                    upload_jobs[job_id]["status"] = "error"
                    # BUG-087: the exception is logged; the job shows a generic message
                    upload_jobs[job_id]["errors"].append(
                        f"Fatal error: the import stopped unexpectedly (job {job_id}); see the server log. "
                        "No rows were saved.")
            _persist_job(job_id, force=True)

        finally:
            try:
                from extensions import db as _db

                _db.session.autoflush = True
                _db.session.remove()  # the import thread's session ends with the thread
            except Exception:
                pass
            if wb:
                wb.close()
            if f:
                f.close()
            # Clean up the original uploaded file
            try:
                import os

                if os.path.exists(file_path):
                    os.remove(file_path)
            except:
                pass


_MAP_COMMON = [
    ("facility_name", "facility name"),
    ("facility_name", "facility"),
    ("facility_name", "facility id"),
    ("facility_name", "region facility"),
    ("facility_name", "plant"),
    ("facility_name", "site"),
    ("date", "date"),
    ("year", "year"),
    ("month", "month"),
    ("activity", "activity"),
    ("division", "division"),
    ("field", "field"),
    ("unit", "unit"),
    ("notes", "notes"),
]

_MAP_BY_SCOPE = {
    "1": [
        ("facility_name", "region"),
        ("group", "emission source"),
        ("group", "group"),
        ("equipment_id", "equipment id"),
        ("equipment", "equipment"),
        ("process", "process type"),
        ("process", "process"),
        ("fuel", "activity fuel"),
        ("fuel", "fuel"),
        ("factor_type", "factor type"),
        ("factor_type", "factor source"),
        ("factor_type", "tier"),
        ("quantity", "quantity"),
        ("quantity", "amount"),
        ("ch4_content", "ch4 content"),
        ("co2_content", "co2 content"),
        ("combustion_efficiency", "combustion efficiency"),
        ("combustion_efficiency", "combustion eff"),
        ("flare_type", "flare type"),
        ("destruction_efficiency", "destruction efficiency"),
        ("destruction_efficiency", "flare destruction efficiency"),
        ("destruction_efficiency", "destruction eff"),
        ("control_efficiency", "flare control efficiency"),
        ("control_efficiency", "control efficiency"),
        ("control_efficiency", "control eff"),
        ("tank_gor", "tank gor"),
        ("tank_ch4_content", "tank ch4 content"),
        ("tank_control_eff", "tank control eff"),
        ("tank_control_eff", "tank control efficiency"),
        ("gor", "gor"),
        ("pneu_count", "pneumatic count"),
        ("pneu_bleed_rate", "bleed rate"),
        ("pneu_hours", "hours"),
        ("unload_depth", "well depth"),
        ("unload_diam", "diameter"),
        ("unload_press", "pressure"),
        ("unload_freq", "events"),
        ("blowdown_volume", "blowdown volume"),
        ("fugitive_method", "fugitive method"),
        ("fugitive_ppm", "ppm"),
        ("dehy_throughput", "dehydrator throughput"),
        ("dehy_ch4_content", "dehy ch4"),
        ("agr_throughput", "agr throughput"),
        ("agr_co2_in", "co2 in"),
        ("agr_co2_out", "co2 out"),
        ("c1", "c1 mol"),
        ("c2", "c2 mol"),
        ("c3", "c3 mol"),
        ("c4", "c4 mol"),
        ("c5", "c5 mol"),
        ("c1", "c1"),
        ("c2", "c2"),
        ("c3", "c3"),
        ("c4", "c4"),
        ("c5", "c5"),
        ("c6", "c6"),
        ("c7", "c7"),
        ("c8", "c8"),
        ("c9", "c9"),
        ("c10", "c10"),
        ("n2_mol", "n2 mol"),
        ("n2_mol", "n2"),
        ("co2_mol", "co2 mol"),
        ("co2_mol", "co2"),
        ("hhv", "hhv"),
        ("user_unc_co2", "user uncertainty co2"),
        ("user_unc_ch4", "user uncertainty ch4"),
        ("user_unc_n2o", "user uncertainty n2o"),
    ],
    "2": [
        ("grid_region", "grid region"),
        ("grid_region", "region"),
        ("consumption", "consumption"),
        ("consumption", "kwh"),
        ("consumption", "electricity kwh"),
        ("consumption", "electricity"),
        ("consumption", "steam mmbtu"),
        ("consumption", "steam"),
        ("consumption", "amount"),
        ("consumption", "quantity"),
        ("source_type", "source type"),
        ("source_type", "utility type"),
        ("source_type", "factor type"),
        ("factor", "emission factor"),
        ("factor", "factor"),
        ("unit", "heat unit"),
        ("meter", "meter"),
        ("meter", "meter id"),
        ("boiler_eff", "boiler efficiency"),
        ("boiler_eff", "boiler eff"),
        ("trans_loss", "transmission loss"),
        ("trans_loss", "trans loss"),
    ],
    "3": [
        ("facility_name", "region"),
        ("category", "category"),
        ("sub_category", "sub category"),
        ("amount", "activity amount"),
        ("amount", "activity data"),
        ("amount", "amount"),
        ("amount", "quantity"),
        ("emission_factor", "emission factor"),
        ("emission_factor", "ef"),
        ("emission_factor", "factor"),
        ("ef_unit", "ef unit"),
        ("ef_unit", "emission factor unit"),
        ("ef_unit", "factor unit"),
        ("co2e", "co2e"),
    ],
    "3_eeio": [
        ("facility_name", "region"),
        ("naics_code", "naics code"),
        ("naics_code", "naics"),
        ("spend_usd", "spend usd"),
        ("spend_usd", "spend"),
    ],
    "sources": [
        ("facility_name", "region"),
        ("name", "equipment name"),
        ("name", "source name"),
        ("name", "name"),
        ("equipment_id", "equipment id"),
        ("type", "process type"),
        ("type", "type"),
        ("fuel_type", "fuel type"),
        ("design_capacity", "design capacity"),
        ("installation_date", "installation date"),
        ("status", "status"),
        ("description", "description"),
    ],
    "production": [
        ("facility_name", "region"),
        ("oil_volume", "oil volume"),
        ("oil_volume", "oil amount"),
        ("oil_unit", "oil unit"),
        ("gas_volume", "gas volume"),
        ("gas_volume", "gas amount"),
        ("gas_unit", "gas unit"),
    ],
    "mitigation": [
        ("facility_name", "region"),
        ("name", "project name"),
        ("name", "name"),
        ("quantity_tco2e", "quantity tco2e"),
        ("quantity_tco2e", "quantity"),
        ("start_date", "start date"),
        ("end_date", "end date"),
        ("investment_amount", "investment amount"),
        ("investment_amount", "investment"),
        ("project_type", "project type"),
        ("project_type", "type"),
        ("status", "status"),
        ("description", "description"),
    ],
    "custom_factors": [
        ("name", "name"),
        ("co2_factor", "co2 factor"),
        ("ch4_factor", "ch4 factor"),
        ("n2o_factor", "n2o factor"),
        ("co_factor", "co factor"),
        ("hhv_factor", "hhv factor"),
        ("hhv_factor", "hhv"),
        ("usage", "usage"),
        ("parent_fuel", "parent fuel"),
        ("source", "source"),
        ("version", "version"),
        ("uncertainty", "uncertainty"),
        ("co2_uncertainty", "co2 uncertainty"),
        ("ch4_uncertainty", "ch4 uncertainty"),
        ("n2o_uncertainty", "n2o uncertainty"),
    ],
    "facilities": [
        ("name", "region name"),
        ("name", "facility name"),
        ("name", "name"),
        ("region", "region"),
        ("code", "code"),
        ("boundary_type", "consolidation approach"),
        ("equity_share_pct", "equity share"),
        ("equity_share_pct", "equity share pct"),
        ("equity_share_pct", "equity"),
        ("operator_status", "operator status"),
        ("boundary_type", "boundary type"),
        ("boundary_detail", "boundary details"),
        ("boundary_detail", "boundary detail"),
        ("segment", "supply chain segment"),
        ("segment", "segment"),
        ("latitude", "latitude"),
        ("longitude", "longitude"),
        ("location", "wilaya"),
        ("location", "location"),
        ("description", "description"),
    ],
}


_EXACT_ONLY_TERMS = {"activity", "division", "field", "region", "notes", "hours", "pressure", "events",
                     "diameter", "gor", "co2", "n2", "ppm", "service",
                     "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10"}


def _scope1_input_names():
    from services.scope1_template import CORE, IDENT, OPTIONAL, TIER2, TIER3, ACTIVITY_TIME

    return {c.key for c in CORE + IDENT + OPTIONAL + TIER2 + TIER3 + ACTIVITY_TIME} - {
        "date", "facility_name", "process_type", "fuel", "quantity", "unit"}


def _build_mapping(headers, scope=1):
    """Header -> field mapping for one import type. Headers are compared without the
    template tags and unit notes; exact names win over partial (word) matches."""
    import re

    scope = str(scope)
    fields = list(_MAP_BY_SCOPE.get(scope, _MAP_BY_SCOPE["1"]))
    if scope == "facilities":
        # a facility import names the facility itself: its "facility" column is the name
        fields += [(k, t) for k, t in _MAP_COMMON if k != "facility_name"] + [("name", "facility")]
    else:
        fields += _MAP_COMMON
    mapping = {}
    normalized_headers = {h: _canonical_header(h).replace("_", " ") for h in headers if str(h or "").strip()}
    # longer (more specific) terms first; within a length, the listed order
    sorted_expected = sorted(fields, key=lambda x: len(x[1]), reverse=True)

    # Pass 1: exact match
    for sys_key, search_term in sorted_expected:
        if sys_key in mapping:
            continue
        for h, h_norm in normalized_headers.items():
            if h_norm == search_term and h not in mapping.values():
                mapping[sys_key] = h
                break

    # Pass 2: whole-word match for the remaining fields. S1K-F12 / F19: a generic single word
    # ("activity", "region", "hours", "pressure", "events", "gor" ...) is also a word of other method
    # columns ("activity_key", "operating_hours", "blowdown_pressure", "comp_gor"); it only matches a
    # header that is exactly that word (activity_key values were stored as the business Activity)
    # a header that is already the name of a Scope 1 input ("agr_control_eff") is that input, never a word
    # match of another one ("control eff" -> control_efficiency)
    own_names = _scope1_input_names() if scope == "1" else set()
    for h, h_norm in normalized_headers.items():
        if h in mapping.values() or h_norm.replace(" ", "_") in own_names:
            continue
        for sys_key, search_term in sorted_expected:
            if search_term in _EXACT_ONLY_TERMS:
                continue
            if sys_key not in mapping and re.search(r"\b" + re.escape(search_term) + r"\b", h_norm):
                mapping[sys_key] = h
                break

    return mapping


def _process_row_scope2(
    row,
    user_id,
    fac_name_map,
    fac_id_map,
    GRID_FACTORS,
    job_id,
    row_idx,
    batch_keys=None,
    overwrite_duplicates=False,
):
    from models import Scope2Emission

    errors = []

    # 1. Parse Date (BUG-085: no default year/month, explicit formats, range-checked)
    year, month, period_error = _parse_row_period(row)
    if period_error:
        return None, [period_error]

    # 2. Resolve Facility
    facility = None
    fac_input = row.get("facility_name") or row.get("facility") or row.get("facility_id")
    if fac_input:
        fac_str = str(fac_input).strip().lower()
        if fac_str in fac_name_map:
            facility = fac_name_map[fac_str]
        elif fac_str in fac_id_map:
            facility = fac_id_map[fac_str]

    if not facility:
        errors.append(f"Facility '{fac_input}' not found")
        return None, errors

    raw_source = str(row.get("source_type") or row.get("factor_type") or "electricity").strip().lower()
    raw_source = re.sub(r"[\s\-/]+", "_", raw_source)
    if raw_source in ["indirect_steam", "steam", "heat", "purchased_steam", "purchased_heat", "steam_heat"]:
        source_type = "indirect_steam"
    elif raw_source in ["cogen_allocation", "cogen", "chp", "cogeneration"]:
        source_type = "cogen_allocation"
    elif raw_source in ["electricity", "purchased_electricity", "power", "grid_electricity", "grid", "market",
                        "location", "location_based", "market_based"]:
        source_type = "electricity"
    else:
        # an unknown source type used to be booked as electricity
        return None, [f"Row {row_idx}: unknown source type '{row.get('source_type') or row.get('factor_type')}': "
                      "use electricity, indirect_steam or cogen_allocation"]

    grid_region = str(row.get("grid_region") or "").strip()
    ef = None
    if source_type == "electricity":
        # BUG-099: same factor policy as the manual Scope 2 form (routes.scope2.resolve_electricity_factor)
        from input_validation import ValidationError
        from routes.scope2 import resolve_electricity_factor

        supplied = row.get("factor") if row.get("factor") not in (None, "") else row.get("emission_factor")
        try:
            ef, grid_region = resolve_electricity_factor(grid_region, supplied)
        except ValidationError as err:
            return None, [f"Row {row_idx}: {err.message}"]

    if source_type == "indirect_steam":
        raw_val = _first(row, "steammmbtu", "steam_mmbtu", "steam", "consumption", "amount", "quantity")
    else:
        raw_val = _first(row, "electricitykwh", "electricity_kwh", "consumption", "amount", "quantity")
    if source_type != "cogen_allocation":
        # the manual form requires a positive consumption; a blank or text cell is never 0 kWh
        val = _clean_float(raw_val, default=None)
        if val is None or val <= 0:
            return None, [f"Row {row_idx}: consumption must be a positive number (got '{raw_val if raw_val is not None else ''}')"]
    else:
        val = 0.0
    unit = str(
        row.get("unit")
        or row.get("heat_unit")
        or ("mmbtu" if source_type == "indirect_steam" else "kWh")
    ).strip()

    if _is_bare_ton(unit):
        return None, [f"Row {row_idx}: " + _TON_ERROR.format(v=unit)]

    kwh = 0.0
    heat_mmbtu = 0.0
    steam_ton = 0.0

    if source_type == "indirect_steam":
        # same calculation as the manual form (routes.scope2._calc_indirect_steam), including the
        # boiler CH4 / N2O; the unit must be one it converts
        from routes.scope2 import _calc_indirect_steam

        u = unit.lower().replace(" ", "")
        u = {"shortton": "short_ton", "shorttons": "short_ton", "metricton": "metric_ton", "tonnes": "tonne"}.get(u, u)
        known_steam_units = {"mmbtu", "mm_btu", "btu", "mj", "megajoule", "gj", "gigajoule", "kwh", "mwh", "ton",
                             "us_ton", "short_ton", "tonne", "metric_ton", "mt", "mlb", "klb", "thousand_lbs", "lb",
                             "lbs", "kg"}
        if u not in known_steam_units:
            errors.append(f"Row {row_idx}: Unknown unit '{unit}' for indirect steam")
            return None, errors
        # boiler efficiency: a fraction (0.85) or a percentage (85) - unambiguous, no boiler runs at 1 %.
        # transmission loss: always a percentage in the file (0.9 = 0.9 %); it used to be read as a
        # fraction at or below 1, so 0.9 % became 90 % and 1 % was rejected
        raw_be = _first(row, "boiler_eff", "boiler_efficiency", "boiler_eff_pct")
        boiler_eff = 0.80 if raw_be in (None, "") else _clean_float(raw_be, default=None)
        if boiler_eff is None:
            return None, [f"Row {row_idx}: boiler efficiency '{raw_be}' is not a number (e.g. 85 or 0.85)"]
        if boiler_eff > 1.0 or "%" in str(raw_be):
            boiler_eff /= 100.0
        raw_tl = _first(row, "trans_loss", "trans_loss_pct", "transmission_loss")
        trans_loss = 0.0 if raw_tl in (None, "") else _clean_float(raw_tl, default=None)
        if trans_loss is None:
            return None, [f"Row {row_idx}: transmission loss '{raw_tl}' is not a number (a percentage, e.g. 5)"]
        trans_loss /= 100.0
        if not 0 < boiler_eff <= 1.0:
            return None, [f"Row {row_idx}: boiler efficiency must be above 0 and at most 100 % (got {raw_be})"]
        if not 0 <= trans_loss < 1.0:
            return None, [f"Row {row_idx}: transmission loss is a percentage from 0 to below 100 (got {raw_tl})"]
        ci = {"trans_loss": trans_loss}
        boiler_ef = _first(row, "ef_co2", "factor", "emission_factor")
        if boiler_ef is not None:
            ef_val = _clean_float(boiler_ef, default=None)
            if ef_val is None or ef_val <= 0:
                return None, [f"Row {row_idx}: boiler emission factor must be a positive number (kg CO2 / MMBtu)"]
            ci["ef_co2"] = ef_val
        try:
            co2e, heat_mmbtu, ef = _calc_indirect_steam(
                {"amount": val, "unit": u, "boiler_efficiency": boiler_eff, "calc_inputs": {"indirect_steam": ci}})
        except ValueError as err:
            return None, [f"Row {row_idx}: {err}"]
        if u in ("ton", "tonne", "mt", "us_ton", "short_ton", "metric_ton"):
            steam_ton = val
    elif source_type in ["cogen_allocation", "cogen"]:
        # BUG-099 pattern: never book a client-supplied co2e; allocate on the server
        from routes.scope2 import _calc_cogen_allocation

        source_type = "cogen_allocation"
        cogen_in = {
            "total_emissions": row.get("total_emissions"),
            "fuel_consumed_mmbtu": row.get("fuel_consumed_mmbtu"),
            "heat_output_mmbtu": row.get("heat_output_mmbtu"),
            "power_output_mwh": row.get("power_output_mwh"),
            "allocation_method": row.get("allocation_method") or "wri_efficiency",
            "heat_efficiency": row.get("heat_efficiency"),
            "power_efficiency": row.get("power_efficiency"),
        }
        if not _clean_float(cogen_in["heat_output_mmbtu"], default=0.0) or not (
            _clean_float(cogen_in["total_emissions"], default=0.0) or _clean_float(cogen_in["fuel_consumed_mmbtu"], default=0.0)
        ):
            return None, [f"Row {row_idx}: CHP rows need heat_output_mmbtu and total_emissions or fuel_consumed_mmbtu"]
        co2e = _calc_cogen_allocation({k: v for k, v in cogen_in.items() if v not in (None, "")})
        heat_mmbtu = _clean_float(cogen_in["heat_output_mmbtu"], default=0.0)
        ef = None
    else:
        source_type = "electricity"
        u = unit.lower().replace(" ", "")
        if u in ["kwh", "kw-hr", "kilowatthour"]:
            kwh = val
        elif u in ["mwh", "mw-hr", "megawatthour"]:
            kwh = val * 1000.0
        elif u in ["gwh", "gw-hr", "gigawatthour"]:
            kwh = val * 1_000_000.0
        else:
            errors.append(f"Row {row_idx}: Unknown unit '{unit}' for electricity. Must be kWh, MWh, or GWh.")
            return None, errors
        co2e = (kwh * ef) / 1000.0

    if co2e is None or co2e < 0:
        return None, [f"Row {row_idx}: consumption and emissions must be non-negative"]

    # uncertainty: the value given, else the manual form's default for Scope 2
    from routes.scope2 import default_scope2_uncertainty

    if row.get("uncertainty") not in (None, ""):
        unc = _file_uncertainty(row.get("uncertainty"))
        if unc is None:
            return None, [f"Row {row_idx}: uncertainty must be a fraction (0-2) or a percentage"]
    else:
        unc = default_scope2_uncertainty(co2e)
    meter = str(row.get("meter") or row.get("meter_id") or "").strip()
    key = _scope2_key(facility.id, year, month, source_type, grid_region, meter)
    action, existing = _dedupe(
        batch_keys, key, overwrite_duplicates,
        f"Scope 2 emission for '{facility.name}' ({year}-{month:02d}, source '{source_type}', grid '{grid_region}'{', meter ' + meter if meter else ''})",
    )
    if action == "error":
        return None, [existing]
    mkt_inst = str(row.get("market_instrument_type") or row.get("market_instrument") or "").strip() or None
    mkt_ef_val = None
    raw_mkt_ef = row.get("market_emission_factor") or row.get("supplier_emission_factor") or row.get("supplier_factor")
    if raw_mkt_ef not in (None, ""):
        mkt_ef_val = _clean_float(raw_mkt_ef, default=None)
    elif mkt_inst and mkt_inst.lower() in ("rec", "ppa_zero", "go_zero", "renewable_ppa", "green_tariff_zero"):
        mkt_ef_val = 0.0
    else:
        mkt_ef_val = ef
    co2e_mkt = (kwh * mkt_ef_val) / 1000.0 if source_type == "electricity" else co2e

    values = {
        "source_type": source_type, "electricity_kwh": kwh, "heat_mmbtu": heat_mmbtu, "steam_ton": steam_ton,
        "emission_factor": ef, "co2e": co2e, "co2e_location_based": co2e, "co2e_market_based": co2e_mkt,
        "market_instrument_type": mkt_inst, "market_emission_factor": mkt_ef_val,
        "uncertainty": unc, "grid_region": grid_region or None,
        "location": meter or grid_region or None,
    }
    verdict, qa_msg = plausibility_check(co2e)  # the Scope 1 hard bound (1e300 kWh was stored)
    if verdict == "reject":
        return None, [f"Row {row_idx}: {qa_msg}"]
    if action == "update":
        obj = _resolve_existing(Scope2Emission, existing)
        if obj is not None:
            _bulk_overwrite(obj, values, user_id, "Scope 2")
            return None, []

    emission = Scope2Emission(
        facility_id=facility.id,
        year=year,
        month=month,
        source_type=source_type,
        electricity_kwh=kwh,
        heat_mmbtu=heat_mmbtu,
        steam_ton=steam_ton,
        emission_factor=ef,
        co2e=co2e,
        co2e_location_based=co2e,
        co2e_market_based=co2e_mkt,
        market_instrument_type=mkt_inst,
        market_emission_factor=mkt_ef_val,
        uncertainty=unc,
        grid_region=grid_region or None,
        location=meter or grid_region or None,
        activity=row.get("activity") or facility.activity,
        division=row.get("division") or facility.division,
        field=row.get("field") or facility.field,
        created_by=user_id,
        status="Pending",  # Maker-Checker: awaits reviewer approval
    )
    
    # QA/QC Anomaly Detection
    amount = max(kwh, heat_mmbtu)
    if amount > 10000000:
        emission.qa_flag = f"Outlier detected: usage {amount} exceeds 10,000,000 threshold"
        _append_job_list(job_id, "anomalies", {
            "row": row_idx,
            "reason": emission.qa_flag,
            "amount": amount
        })

    if batch_keys is not None:
        batch_keys[key] = emission  # BUG-057: later in-file repeats update this row
    return emission, errors



def _file_uncertainty(raw):
    """An uncertainty cell as a fraction: "5 %" / "2%" are percentages, a bare number above 2 is a
    percentage, a bare number up to 2 a fraction. None when it is not a number in range.
    ("2%" used to become the fraction 2.0 = 200 %: the sign was dropped before the magnitude test.)"""
    unc = _clean_float(raw, default=None)
    if unc is None:
        return None
    if "%" in str(raw) or unc > 2:
        unc /= 100.0
    return unc if 0 <= unc <= 2 else None


def _scope3_uncertainty(row, co2e, row_idx):
    """(value, error): the file's uncertainty (fraction 0-2 or a percentage), else the form default."""
    from routes.scope3 import default_scope3_uncertainty

    if row.get("uncertainty") in (None, ""):
        return default_scope3_uncertainty(co2e), None
    unc = _file_uncertainty(row.get("uncertainty"))
    if unc is None:
        return None, f"Row {row_idx}: uncertainty must be a fraction (0-2) or a percentage"
    return unc, None

def _process_row_scope3_eeio(
    row,
    user_id,
    fac_name_map,
    fac_id_map,
    job_id,
    row_idx,
    batch_keys=None,
    overwrite_duplicates=False,
):
    from models import Scope3Emission
    from emission_factors.eeio_factors import get_eeio_factor

    errors = []

    # 1. Parse Date (BUG-085: no default year/month, explicit formats, range-checked)
    year, month, period_error = _parse_row_period(row)
    if period_error:
        return None, [period_error]


    # 2. Resolve Facility
    fac_raw = str(row.get("facility_name") or row.get("facility_id") or "").strip()
    facility = fac_id_map.get(fac_raw) or fac_name_map.get(fac_raw.lower())
    if not facility:
        return None, [f"Facility '{fac_raw}' not found"]

    # 3. Resolve NAICS and Spend
    naics = str(row.get("naics_code") or "").strip()
    if naics.endswith(".0") and naics[:-2].isdigit():
        naics = naics[:-2]  # an Excel number cell (331110.0)
    spend_usd = _clean_float(row.get("spend_usd"), default=-1.0)
    if spend_usd <= 0:
        return None, [f"Spend amount must be a number greater than zero (got '{row.get('spend_usd') or ''}')"]

    # 4. Calculate (EPA supply chain factors; an unknown code is a row error, not a default factor)
    try:
        factor_data = get_eeio_factor(naics)
    except LookupError as exc:
        return None, [str(exc)]
    spend_k = spend_usd / 1000.0
    kg_co2e = spend_k * factor_data["kg_co2e_per_1000_usd"]
    tonnes_co2e = kg_co2e / 1000.0

    sub_cat = f"Spend-based: {factor_data['name']} (NAICS {naics})"
    key = _scope3_key(facility.id, year, month, "Category 1", sub_cat, "USD")
    action, existing = _dedupe(batch_keys, key, overwrite_duplicates,
                               f"Scope 3 emission for facility '{facility.name}' ({year}-{month:02d}, Category 1, NAICS {naics})")
    if action == "error":
        return None, [existing]
    unc, unc_err = _scope3_uncertainty(row, tonnes_co2e, row_idx)
    if unc_err:
        return None, [unc_err]
    values = {
        "sub_category": sub_cat, "activity_data": spend_usd, "unit": "USD",
        "emission_factor": factor_data["kg_co2e_per_usd"], "co2e": tonnes_co2e,
        "notes": row.get("notes", "Bulk Imported via EEIO"), "uncertainty": unc,
    }
    verdict, qa_msg = plausibility_check(tonnes_co2e)  # the Scope 1 hard bound (1e300 kWh was stored)
    if verdict == "reject":
        return None, [f"Row {row_idx}: {qa_msg}"]
    if action == "update":
        obj = _resolve_existing(Scope3Emission, existing)
        if obj is not None:
            _bulk_overwrite(obj, values, user_id, "Scope 3")
            return None, []

    emission = Scope3Emission(
        facility_id=facility.id,
        year=year,
        month=month,
        category="Category 1",
        sub_category=f"Spend-based: {factor_data['name']} (NAICS {naics})",
        activity_data=spend_usd,
        unit="USD",
        emission_factor=factor_data["kg_co2e_per_usd"],  # kg CO2e per USD, like the manual form
        co2e=tonnes_co2e,
        uncertainty=unc,
        calculation_method="Spend-based (EEIO)",
        data_quality="Average-data method",
        notes=row.get("notes", "Bulk Imported via EEIO"),
        created_by=user_id,
        status="Pending",
    )
    
    # QA/QC Anomaly Detection
    if spend_usd > 10000000:
        emission.qa_flag = f"Outlier detected: activity data {spend_usd} exceeds 10,000,000 threshold"
        _append_job_list(job_id, "anomalies", {
            "row": row_idx,
            "reason": emission.qa_flag,
            "amount": spend_usd
        })

    if batch_keys is not None:
        batch_keys[key] = emission  # BUG-057
    return emission, errors

def _process_row_scope3(
    row,
    user_id,
    fac_name_map,
    fac_id_map,
    job_id,
    row_idx,
    batch_keys=None,
    overwrite_duplicates=False,
):
    from models import Scope3Emission

    errors = []

    # 1. Parse Date (BUG-085: no default year/month, explicit formats, range-checked)
    year, month, period_error = _parse_row_period(row)
    if period_error:
        return None, [period_error]

    # 2. Resolve Facility
    facility = None
    fac_input = row.get("facility_name") or row.get("facility") or row.get("facility_id")
    if fac_input:
        fac_str = str(fac_input).strip().lower()
        if fac_str in fac_name_map:
            facility = fac_name_map[fac_str]
        elif fac_str in fac_id_map:
            facility = fac_id_map[fac_str]

    if not facility:
        errors.append(f"Facility '{fac_input}' not found")
        return None, errors

    # BUG-085 / BUG-089: category is required and stored in the canonical "Category N" form
    from input_validation import ValidationError, normalize_scope3_category

    try:
        cat_str = normalize_scope3_category(row.get("category"))
    except ValidationError:
        return None, [f"Invalid or missing Scope 3 category '{row.get('category') or ''}': use a GHG Protocol category 1-15"]
    sub_cat = row.get("sub_category")

    raw_amt = _first(row, "amount", "activityamount", "activity_amount", "activitydata", "quantity")
    raw_ef = _first(row, "emission_factor", "emissionfactor", "factor", "ef")
    amt = _clean_float(raw_amt, default=None) if raw_amt is not None else 0.0
    ef = _clean_float(raw_ef, default=None) if raw_ef is not None else 0.0
    if amt is None:
        return None, [f"Activity amount '{raw_amt}' is not a number"]
    if ef is None:
        return None, [f"Emission factor '{raw_ef}' is not a number"]
    ef_unit = str(
        row.get("ef_unit")
        or row.get("efunit")
        or row.get("factor_unit")
        or "kg"
    ).strip()
    calc_method = str(row.get("calculation_method") or "")

    from calculations.units import compute_scope3_co2e

    if amt < 0 or ef < 0:
        return None, ["Activity amount and emission factor must be non-negative"]
    supplier_total = row.get("co2e") not in (None, "")
    if amt > 0 and raw_ef is None and not supplier_total:
        # no factor in the file: the factor of the same activity in the Scope 3 form (kg CO2e / unit)
        from emission_factors.scope3_activity_factors import scope3_activity_factor
        from input_validation import scope3_category_number

        ef_found, why = scope3_activity_factor(scope3_category_number(cat_str), sub_cat, row.get("unit"))
        if ef_found is None:
            return None, [why]
        ef, ef_unit = ef_found, "kg"
    if amt > 0 and ef > 0:
        try:
            co2e = compute_scope3_co2e(amt, ef, ef_unit, calc_method)
        except ValidationError as err:
            return None, [err.message]
    elif supplier_total:
        # supplier-specific total (GHG Protocol supplier-specific method): the same roles as the
        # manual form may enter it
        from extensions import db as _db
        from models import User

        uploader = _db.session.get(User, user_id)
        if uploader is None or uploader.role not in ("admin", "superuser"):
            return None, ["Only admins and superusers may import a supplier-reported co2e total; give the activity and factor"]
        co2e = _clean_float(row.get("co2e"), default=-1.0)
        if co2e < 0:
            return None, ["co2e must be a non-negative number"]
    else:
        # never book a missing calculation as 0 tCO2e
        return None, ["Provide activity amount and emission factor (or a supplier-specific co2e)"]

    if amt > 0 and ef > 0:
        # stored as kg CO2e per activity unit, the unit the tables and edits read
        from calculations.units import scope3_ef_kg_per_unit
        ef = scope3_ef_kg_per_unit(amt, co2e, ef)
    key = _scope3_key(facility.id, year, month, cat_str, sub_cat, row.get("unit"))
    action, existing = _dedupe(batch_keys, key, overwrite_duplicates,
                               f"Scope 3 emission for facility '{facility.name}' ({year}-{month:02d}, {cat_str}, '{sub_cat or ''}')")
    if action == "error":
        return None, [existing]
    unc, unc_err = _scope3_uncertainty(row, co2e, row_idx)
    if unc_err:
        return None, [unc_err]
    values = {
        "category": cat_str, "sub_category": sub_cat, "activity_data": amt, "unit": row.get("unit"),
        "emission_factor": ef, "co2e": co2e, "notes": row.get("notes"), "uncertainty": unc,
    }
    verdict, qa_msg = plausibility_check(co2e)  # the Scope 1 hard bound (1e300 kWh was stored)
    if verdict == "reject":
        return None, [f"Row {row_idx}: {qa_msg}"]
    if action == "update":
        obj = _resolve_existing(Scope3Emission, existing)
        if obj is not None:
            _bulk_overwrite(obj, values, user_id, "Scope 3")
            return None, []

    emission = Scope3Emission(
        facility_id=facility.id,
        year=year,
        month=month,
        category=cat_str,
        sub_category=sub_cat,
        activity_data=amt,
        unit=row.get("unit"),
        emission_factor=ef,
        co2e=co2e,
        uncertainty=unc,
        notes=row.get("notes", "Bulk Imported"),
        created_by=user_id,
        status="Pending",  # Maker-Checker: awaits reviewer approval
    )

    # QA/QC Anomaly Detection
    if amt > 10000000:
        emission.qa_flag = f"Outlier detected: activity data {amt} exceeds 10,000,000 threshold"
        _append_job_list(job_id, "anomalies", {
            "row": row_idx,
            "reason": emission.qa_flag,
            "amount": amt
        })

    if batch_keys is not None:
        batch_keys[key] = emission  # BUG-057
    return emission, errors


def _process_row_sources(row, user_id, fac_name_map, fac_id_map, batch=None):
    from extensions import db
    from models import EmissionSource

    errors = []

    # Validate required name field
    name = str(row.get("name") or "").strip()
    if not name:
        errors.append("Equipment Name is required for emission source")
        return None, errors

    facility = None
    fac_input = row.get("facility_name") or row.get("facility") or row.get("facility_id")
    if fac_input:
        fac_str = str(fac_input).strip().lower()
        if fac_str in fac_name_map:
            facility = fac_name_map[fac_str]
        elif fac_str in fac_id_map:
            facility = fac_id_map[fac_str]

    if not facility:
        errors.append(f"Facility '{fac_input}' not found")
        return None, errors

    # the same source (facility, name, equipment ID) is registered once
    equipment_id = str(row.get("equipment_id") or "").strip() or None
    key = (facility.id, name.lower(), (equipment_id or "").lower())
    if batch is not None and key in batch:
        return None, [f"Source '{name}' ({equipment_id or 'no equipment ID'}) appears more than once in the file"]
    dup = EmissionSource.query.filter(
        EmissionSource.facility_id == facility.id, db.func.lower(EmissionSource.name) == name.lower(),
        db.func.coalesce(EmissionSource.equipment_id, "") == (equipment_id or ""),
    ).first()
    if dup is not None:
        return None, [f"Source '{name}' ({equipment_id or 'no equipment ID'}) already exists for '{facility.name}'"]
    inst = row.get("installation_date")
    if inst not in (None, ""):
        import datetime as _dt

        if isinstance(inst, (_dt.date, _dt.datetime)):
            inst = inst.strftime("%Y-%m-%d")
        else:
            inst = str(inst).strip()
            try:
                _dt.datetime.strptime(inst[:10], "%Y-%m-%d")
                inst = inst[:10]
            except ValueError:
                return None, [f"Invalid installation date '{inst}': use YYYY-MM-DD"]
    if batch is not None:
        batch.add(key)

    source = EmissionSource(
        facility_id=facility.id,
        name=name,
        equipment_id=equipment_id,
        type=row.get("type") or row.get("process_type"),
        fuel_type=row.get("fuel_type") or row.get("fuel"),
        design_capacity=row.get("design_capacity"),
        installation_date=inst or None,
        status=row.get("status", "Active"),
        description=row.get("description"),
        activity=row.get("activity") or facility.activity,
        division=row.get("division") or facility.division,
        field=row.get("field") or facility.field,
        created_by=user_id,
    )
    return source, errors


def _process_row_production(row, user_id, fac_name_map, fac_id_map, batch_prod_map=None):
    from models import ProductionData
    from extensions import db

    errors = []

    facility = None
    fac_input = row.get("facility_name") or row.get("facility") or row.get("facility_id")
    if fac_input:
        fac_str = str(fac_input).strip().lower()
        if fac_str in fac_name_map:
            facility = fac_name_map[fac_str]
        elif fac_str in fac_id_map:
            facility = fac_id_map[fac_str]

    if not facility:
        errors.append(f"Facility '{fac_input}' not found")
        return None, errors

    # same period rules as the emission imports (range-checked year and month)
    year, month, period_error = _parse_row_period(row)
    if period_error:
        return None, [period_error]

    volumes = {}
    for name, keys in (("oil", ("production_volume", "oil_volume", "oil_amount")),
                       ("gas", ("energy_consumption", "gas_volume", "gas_amount"))):
        raw = _first(row, *keys)
        v = _clean_float(raw, default=None) if raw is not None else 0.0
        if v is None or v < 0:
            return None, [f"{name.title()} production '{raw}' must be a non-negative number"]
        volumes[name] = v
    oil_vol, gas_vol = volumes["oil"], volumes["gas"]

    oil_unit = str(row.get("production_unit") or row.get("oil_unit") or "bbl").strip()
    if _is_bare_ton(oil_unit):
        return None, [_TON_ERROR.format(v=oil_unit)]
    gas_unit = str(row.get("energy_unit") or row.get("gas_unit") or "mscf").strip()
    # units the intensity KPIs can convert (services.dashboard_filters); an unknown unit would
    # silently drop the row from every production-based indicator
    from calculations.units import UnitError, unit_dimension
    from services.dashboard_filters import gas_volume_m3

    try:
        if unit_dimension(oil_unit)[0] not in ("volume", "mass"):
            raise UnitError(oil_unit)
    except UnitError:
        return None, [f"Unknown oil unit '{oil_unit}': use bbl, m3, gal, L or tonne"]
    if gas_volume_m3(1.0, gas_unit) is None:
        return None, [f"Unknown gas unit '{gas_unit}': use scf, Mscf, MMscf, m3 or Sm3"]
    activity = row.get("activity") or facility.activity
    division = row.get("division") or facility.division
    field = row.get("field") or facility.field

    # Upsert: respect the (facility_id, month, year) UniqueConstraint
    # In-batch duplicate tracking prevents bulk_save_objects collision
    key = (facility.id, year, month)
    existing = None
    if batch_prod_map is not None and key in batch_prod_map:
        existing = batch_prod_map[key]
    else:
        existing = ProductionData.query.filter_by(
            facility_id=facility.id,
            year=year,
            month=month,
        ).first()
        if existing and batch_prod_map is not None:
            batch_prod_map[key] = existing

    if existing:
        existing.oil_amount = oil_vol
        existing.gas_amount = gas_vol
        existing.oil_unit = oil_unit
        existing.gas_unit = gas_unit
        if activity:
            existing.activity = activity
        if division:
            existing.division = division
        if field:
            existing.field = field
        # Return None — session already tracks existing; no need to bulk_save_objects it
        return None, errors

    prod = ProductionData(
        facility_id=facility.id,
        year=year,
        month=month,
        oil_amount=oil_vol,
        oil_unit=oil_unit,
        gas_amount=gas_vol,
        gas_unit=gas_unit,
        activity=activity,
        division=division,
        field=field,
        created_by=user_id,
    )
    if batch_prod_map is not None:
        batch_prod_map[key] = prod
    return prod, errors


def _process_row_mitigation(row, user_id, fac_name_map, fac_id_map):
    from models import MitigationProject
    from datetime import datetime

    errors = []

    # Validate required project name
    project_name = str(row.get("name") or "").strip()
    if not project_name:
        errors.append("Project Name is required for mitigation project")
        return None, errors

    facility = None
    fac_input = row.get("facility_name") or row.get("facility") or row.get("facility_id")
    if fac_input:
        fac_str = str(fac_input).strip().lower()
        if fac_str in fac_name_map:
            facility = fac_name_map[fac_str]
        elif fac_str in fac_id_map:
            facility = fac_id_map[fac_str]

    if not facility:
        errors.append(f"Facility '{fac_input}' not found")
        return None, errors

    # a project year is required (never an assumed year) and range-checked
    from input_validation import ValidationError, parse_year

    try:
        year = parse_year(row.get("year"))
    except ValidationError as err:
        return None, [err.message]

    raw_qty = _first(row, "quantity_tco2e", "quantity")
    qty = _clean_float(raw_qty, default=None)
    if qty is None or qty < 0:
        return None, [f"Quantity (tCO2e) '{raw_qty if raw_qty is not None else ''}' must be a non-negative number"]

    def _date(field):
        v = row.get(field)
        if v in (None, ""):
            return None, None
        if hasattr(v, "date"):
            return v.date(), None  # Excel date cell
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(str(v).strip(), fmt).date(), None
            except ValueError:
                continue
        return None, f"Invalid {field.replace('_', ' ')} '{v}': use YYYY-MM-DD"

    start_date, err1 = _date("start_date")
    end_date, err2 = _date("end_date")
    if err1 or err2:
        return None, [e for e in (err1, err2) if e]
    if start_date and end_date and end_date < start_date:
        return None, ["End date is before the start date"]

    investment = None
    raw_inv = _first(row, "investment_amount", "investment")
    if raw_inv is not None:
        investment = _clean_float(raw_inv, default=None)
        if investment is None or investment < 0:
            return None, [f"Investment '{raw_inv}' must be a non-negative number"]

    proj = MitigationProject(
        facility_id=facility.id,
        name=project_name,
        project_type=row.get("project_type") or row.get("type"),
        year=year,
        quantity_tco2e=qty,
        status=row.get("status", "Active"),
        start_date=start_date,
        end_date=end_date,
        investment_amount=investment,
        description=row.get("description"),
        created_by=user_id,
    )
    return proj, errors


def _process_row_custom_factors(row, user_id, batch_names=None):
    from models import CustomFactor

    errors = []

    if not row.get("name"):
        errors.append("Name is required for custom factor")
        return None, errors

    # BUG-001: defence in depth - the job endpoint already rejects other roles.
    from extensions import db
    from models import User

    uploader = db.session.get(User, user_id)
    if uploader is None or uploader.role not in ("admin", "superuser"):
        errors.append("Not authorised to import custom factors")
        return None, errors

    # BUG-065 / BUG-112 / BUG-083: same rules as POST /api/custom-factors
    from routes.custom_factors import _name_taken, _parse_non_negative_float, _require_some_factor

    name = str(row.get("name")).strip()
    if _name_taken(name) or (batch_names is not None and name.lower() in batch_names):
        return None, [f"A custom factor named '{name}' already exists"]
    from routes.custom_factors import _canonical_factor_unit

    if _is_bare_ton(row.get("unit")):
        return None, [_TON_ERROR.format(v=str(row.get("unit")).strip())]
    try:
        row = dict(row, unit=_canonical_factor_unit(row.get("unit")))  # BUG-063
    except ValueError as err:
        return None, [str(err)]
    # uncertainties are percentages (as on the form): "5%" or an Excel percent cell is 5
    for k in ("uncertainty", "co2_uncertainty", "ch4_uncertainty", "n2o_uncertainty"):
        v = row.get(k)
        if isinstance(v, str) and _PERCENT_TEXT.match(v):
            row = dict(row, **{k: _PERCENT_TEXT.match(v).group(1)})
    try:
        vals = {k: _parse_non_negative_float(row.get(k), k) for k in (
            "co2_factor", "ch4_factor", "n2o_factor", "co_factor", "hhv_factor",
            "uncertainty", "co2_uncertainty", "ch4_uncertainty", "n2o_uncertainty")}
        _require_some_factor(vals["co2_factor"], vals["ch4_factor"], vals["n2o_factor"])
        from routes.custom_factors import _canonical_parent_fuel

        parent_fuel = _canonical_parent_fuel(row.get("parent_fuel"))
    except ValueError as err:
        return None, [str(err)]
    row = dict(row, name=name, parent_fuel=parent_fuel, **vals)
    if batch_names is not None:
        batch_names.add(name.lower())

    factor = CustomFactor(
        name=row.get("name"),
        co2_factor=float(row.get("co2_factor") or 0),
        ch4_factor=float(row.get("ch4_factor") or 0),
        n2o_factor=float(row.get("n2o_factor") or 0),
        co_factor=float(row.get("co_factor") or 0),
        unit=row.get("unit"),
        hhv_factor=float(row.get("hhv_factor") or 0),
        usage=row.get("usage"),
        parent_fuel=row.get("parent_fuel"),
        source=row.get("source"),
        version=row.get("version"),
        uncertainty=float(row.get("uncertainty") or 0),
        co2_uncertainty=float(row.get("co2_uncertainty") or 0),
        ch4_uncertainty=float(row.get("ch4_uncertainty") or 0),
        n2o_uncertainty=float(row.get("n2o_uncertainty") or 0),
        created_by=user_id,
    )
    return factor, errors


def _process_row_facilities(row, user_id, overwrite_duplicates, batch=None):
    from extensions import db
    from models import Facility

    errors = []

    name = str(row.get("name") or "").strip()
    if not name:
        errors.append("Facility Name is required")
        return None, errors

    # coordinates: blank = not set, otherwise a number in range (same rule as the manual form)
    from input_validation import ValidationError, parse_number

    coords = {}
    try:
        for fld, lim in (("latitude", 90), ("longitude", 180)):
            coords[fld] = parse_number(row.get(fld), fld, required=False, min_value=-lim, max_value=lim)
        # equity share (%) for equity-share consolidation, as on the manual form
        raw_equity = row.get("equity_share_pct")
        if isinstance(raw_equity, str) and _PERCENT_TEXT.match(raw_equity):  # "50%" / an Excel percent cell
            raw_equity = _PERCENT_TEXT.match(raw_equity).group(1)
        equity = parse_number(raw_equity, "equity_share_pct", required=False, min_value=0, max_value=100)
    except ValidationError as err:
        return None, [err.message]
    operator = str(row.get("operator_status") or "").strip().lower().replace("-", "_").replace(" ", "_") or None
    if operator and operator not in ("operated", "non_operated", "joint_venture"):
        return None, [f"Unknown operator status '{row.get('operator_status')}': use operated or non-operated"]

    batch = batch if batch is not None else {}
    if name.lower() in batch.setdefault("names", set()):
        return None, [f"Facility '{name}' appears more than once in the file"]
    code = str(row.get("code") or "").strip()
    if code:
        if code.lower() in batch.setdefault("codes", set()):
            return None, [f"Facility code '{code}' appears more than once in the file"]
        holder = Facility.query.filter_by(code=code).first()
        if holder is not None and holder.name.strip().lower() != name.lower():
            return None, [f"Facility code '{code}' is already used by '{holder.name}'"]

    existing = Facility.query.filter(db.func.lower(Facility.name) == name.lower()).first()

    # BUG-001: region-restricted superusers may only create/overwrite facilities in their
    # own region (same rule as POST /api/facilities/import).
    from extensions import db
    from models import User

    from utils import facility_in_user_scope, facility_change_allowed

    uploader = db.session.get(User, user_id)
    if uploader is None or uploader.role not in ("admin", "superuser"):
        errors.append("Not authorised to import facilities")
        return None, errors

    def _new(field, current):
        v = row.get(field)
        return v if v is not None and str(v).strip() != "" else current

    if existing is not None and not facility_in_user_scope(uploader, existing.region, existing.location, existing.name):
        errors.append(f"Superusers can only import facilities in their assigned region: {uploader.location}")
        return None, errors
    # The facility must also stay in scope after the row is applied (no re-regioning out of scope).
    cur = existing or Facility()
    if not facility_change_allowed(uploader, existing, _new("region", cur.region), _new("location", cur.location), name):
        errors.append(f"Superusers can only import facilities in their assigned region: {uploader.location}")
        return None, errors

    if existing:
        if not overwrite_duplicates:
            errors.append(f"Region '{name}' already exists. Choose 'Overwrite' to update it.")
            return None, errors
        
        # Overwrite mode - only overwrite fields that are present and non-empty in row
        facility_fields = [
            "location",
            "description",
            "boundary_notes",
            "boundary_type",
            "boundary_detail",
            "activity",
            "division",
            "region",
            "field",
            "code",
            "external_id",
            "segment",
        ]
        for fld in facility_fields:
            if fld in row and row[fld] is not None and str(row[fld]).strip() != "":
                setattr(existing, fld, row[fld])

        if equity is not None:
            existing.equity_share_pct = equity
        if operator:
            existing.operator_status = operator
        if coords["latitude"] is not None:
            existing.latitude = coords["latitude"]
        if coords["longitude"] is not None:
            existing.longitude = coords["longitude"]
        batch["names"].add(name.lower())
        if code:
            batch["codes"].add(code.lower())
        # Return None — session already tracks existing; no need to bulk_save_objects it
        return None, errors
    else:
        lat, lon = coords["latitude"], coords["longitude"]
        batch["names"].add(name.lower())
        if code:
            batch["codes"].add(code.lower())

        facility = Facility(
            name=name,
            location=row.get("location"),
            description=row.get("description"),
            boundary_notes=row.get("boundary_notes"),
            boundary_type=row.get("boundary_type"),
            boundary_detail=row.get("boundary_detail"),
            activity=row.get("activity"),
            division=row.get("division"),
            region=row.get("region"),
            field=row.get("field"),
            code=row.get("code"),
            external_id=row.get("external_id"),
            segment=row.get("segment"),
            latitude=lat,
            longitude=lon,
            equity_share_pct=100.0 if equity is None else equity,
            operator_status=operator or "operated",
            created_by=user_id,
        )
        return facility, errors


_UNIT_SPELLING = {u.lower(): u for u in (
    "MMBtu", "GJ", "MJ", "kWh", "MWh", "therm", "scf", "Mscf", "MMscf", "m3", "Sm3", "Nm3", "gal", "bbl", "L",
    "kg", "tonne", "lb", "short ton", "days", "devices", "components", "events", "wells")}

_S1_TIER = {
    "specific": "specific", "site_specific": "specific", "site-specific": "specific", "engineering": "specific",
    "tier3": "specific", "tier_3": "specific", "tier 3": "specific", "t3": "specific", "3": "specific", "cems": "specific",
    "custom": "custom", "regional": "custom", "tier2": "custom", "tier_2": "custom", "tier 2": "custom", "t2": "custom",
    "2": "custom",
    "default": "default", "tier1": "default", "tier_1": "default", "tier 1": "default", "t1": "default", "1": "default",
    "api": "default", "catalog": "default", "": "default",
}

# fields the calculation service writes on a record (services.scope1_calc.apply_result)
_S1_RESULT_FIELDS = (
    "process_type", "fuel_type", "quantity", "unit", "co2_emissions", "ch4_emissions", "n2o_emissions",
    "co_emissions", "co2e_total", "calc_method", "gwp_version", "custom_factor_id", "factor_source",
    "ef_used_co2", "ef_used_ch4", "ef_used_n2o", "source_payload", "uncertainty", "uncertainty_ch4",
    "uncertainty_n2o", "uncertainty_ad", "uncertainty_ef_co2", "uncertainty_ef_ch4", "uncertainty_ef_n2o",
    "ef_key", "qa_flag", "ogmp_level",
)


def _first(row, *keys):
    for k in keys:
        v = row.get(k)
        if v is not None and str(v).strip() != "":
            return v
    return None


def _process_row(
    row,
    user_id,
    fac_name_map,
    fac_id_map,
    cf_name_map,
    compute_emissions_fn,
    API_FACTORS_dict,
    global_factor_type,
    gwp_dict=None,
    gwp_std="AR5",
    job_id=None,
    row_idx=None,
    batch_keys=None,
    overwrite_duplicates=False,
):
    """Validates one Scope 1 row and calculates and stores it exactly as the manual form does
    (services.scope1_calc: same validation, factor resolution, calculation and stored fields).
    Returns (Emission_Object, list_of_errors)."""
    import re
    import uuid

    from calculations.anomaly import plausibility_check
    from calculations.units import calculate_co2e
    from extensions import db
    from input_validation import ValidationError
    from models import Emission, User
    from services.ogmp import ogmp_level_for
    from services.scope1_calc import (
        SCOPE2_PROCESS_TYPES, apply_result, canonicalize, check_factor_usage, normalize_process_type,
        resolve_factor, validate_activity,
    )
    from utils import user_label

    # Skip instructional walkthrough rows
    if str(row.get("date", "")).strip().upper().startswith("[INSTRUCTION]"):
        return None, []

    # 1. Parse Date (BUG-111: same year/month range rules as POST /api/emissions/)
    year, month, period_error = _parse_row_period(row)
    if period_error:
        return None, [period_error]

    # 2. Resolve Facility
    fac_raw = str(_first(row, "facility_name", "facility", "facility_id") or "").strip()
    facility = fac_id_map.get(fac_raw) or fac_name_map.get(fac_raw.lower())
    if not facility:
        from flask import has_app_context
        if has_app_context():
            from models import Facility as _FacCheck
            global_match = _FacCheck.query.filter(_FacCheck.name.ilike(fac_raw)).first()
            if global_match:
                return None, [f"Access denied: Region '{fac_raw}' exists but your account does not have permission to upload data for it."]
        return None, [f"Region '{fac_raw}' not found. Check that the region name matches exactly a region in the system."]

    # 3. Process type: a known Scope 1 process (key or label); never a guessed calculator
    raw_process = str(_first(row, "process", "process_type", "source_type") or "").strip()
    if not raw_process:
        return None, ["Missing process type."]
    if raw_process.lower() in SCOPE2_PROCESS_TYPES or normalize_process_type(raw_process) in SCOPE2_PROCESS_TYPES:  # BUG-068
        return None, [f"'{raw_process}' is a Scope 2 (purchased energy) source; import it with the Scope 2 template"]
    process_type = normalize_process_type(raw_process)
    if not process_type:
        return None, [f"Unknown process type '{raw_process}'. Use a process key such as combustion, flaring, venting, tank_flashing, pneumatic, fugitive"]

    # 4. Tier
    factor_type_raw = str(_first(row, "factor_type", "factor_source", "factorsource", "factortype", "tier") or "").lower().strip()
    if global_factor_type not in (None, "", "auto"):
        factor_source = global_factor_type
    elif factor_type_raw in _S1_TIER:
        factor_source = _S1_TIER[factor_type_raw]
    else:
        return None, [f"Unknown factor type '{factor_type_raw}': use default, custom or specific"]

    ton_err = _bare_ton_error(row)
    if ton_err:
        return None, [ton_err]

    # 5. Quantity: required for catalog / custom factors; engineered (Tier 3) methods may derive it
    raw_qty = _first(row, "quantity", "amount")
    amount = None
    if raw_qty is not None:
        amount = _clean_float(raw_qty, default=None)
        if amount is None or amount < 0:
            return None, [f"Invalid quantity: {raw_qty} (must be a non-negative number)"]
    elif factor_source != "specific":
        return None, ["Missing quantity."]
    unit = str(row.get("unit") or "").strip()
    unit = _UNIT_SPELLING.get(unit.lower(), unit)  # "mmbtu" -> "MMBtu", as the form writes it
    # S1K-F8: a quantity cell that carries its own unit ("928 m3") must agree with the unit column
    # (the trailing text was dropped and the number booked in the unit column's unit)
    if raw_qty is not None and isinstance(raw_qty, str):
        m_tail = re.match(r"^\s*[-+]?[0-9.,\s ]+(?:[eE][-+]?[0-9]+)?\s*(\S.*?)?\s*$", raw_qty)
        tail = (m_tail.group(1) or "").strip() if m_tail else ""
        if tail and tail.lower().replace(" ", "") != unit.lower().replace(" ", ""):
            return None, [f"Quantity '{raw_qty}' carries the unit '{tail}' but the unit column says "
                          f"'{unit or '(empty)'}': put the number in quantity and the unit in unit"]
    if amount is not None and not unit:
        # BUG-111: a blank unit is a row error, never an assumed m3
        return None, ["Missing unit. Provide the activity unit (e.g. MMBtu, scf, gal, tonne)."]

    fuel = str(_first(row, "fuel", "activity_fuel") or "").strip()

    # 6. Payload in the manual form's shape; the other columns are the method inputs
    # (the squashed header aliases the reader adds, e.g. "tankgor", are left out)
    squashed = {str(h).lower().replace("_", "").replace(" ", "") for h in row if isinstance(h, str)
                and str(h).lower().replace("_", "").replace(" ", "") != _canonical_header(h)}
    payload = {}
    for k, v in row.items():
        if isinstance(k, str) and re.fullmatch(r"[a-z][a-z0-9_]*", k) and k not in squashed and v is not None and str(v).strip() != "":
            payload[k] = v
    payload = {k: _percent_text_to_number(k, v) for k, v in payload.items()}
    # S1K-F17: "12,345.6" is accepted in the quantity column; the method columns (vent_volume, hhv,
    # comp_rate ...) refused it. Only the unambiguous thousands-separator form is rewritten.
    payload = {k: (v.replace(",", "") if isinstance(v, str) and _THOUSANDS_NUMBER.match(v.strip()) else v)
               for k, v in payload.items()}
    payload.update({
        "year": year, "month": month, "facility_id": facility.id, "process_type": process_type,
        "source_type": process_type, "factor_source": factor_source, "unit": unit or None,
    })
    for k in ("amount", "quantity", "fuel", "fuel_type", "process", "factor_type"):
        payload.pop(k, None)
    if amount is not None:
        payload["amount"] = amount
    if fuel:
        payload["fuel"] = fuel

    if factor_source == "custom" and fuel and not fuel.isdigit():
        if fuel.lower() in getattr(cf_name_map, "ambiguous", ()):
            return None, [f"Custom factor name '{fuel}' is not unique; rename the duplicates before importing"]
        from routes.emissions import _lookup_api_factor
        cf = cf_name_map.get(fuel.lower())
        site_props = any(str(row.get(k) or "").strip() not in ("", "-", "0") for k in ("hhv", "density", "fuel_density"))
        if not cf and site_props and _lookup_api_factor(fuel):
            # S1K-F18: Tier 2 "catalog factor + site fuel properties" (the form's Tier 2 mode)
            cf = None
        elif not cf:
            # BUG-042: a Tier 2 row never falls back to the catalog (or to zero)
            return None, [f"Custom factor '{fuel}' not found. Save it under Manage Data > Custom Factors first, "
                          "or give the site HHV / density with a catalog fuel."]
        if cf is not None:
            payload["custom_factor_id"] = cf.id

    # Compendium activity rows (Section 6 tables): the activity_key column, or the row's label in
    # the fuel / factor column, selects the row as the form's factor list does
    from calculations.activity_factors import ACTIVITY_FACTORS
    from routes.emissions import _lookup_api_factor

    akey = str(payload.get("activity_key") or "").strip()
    by_label = {v["label"].strip().lower(): k for k, v in ACTIVITY_FACTORS.items()}
    if akey and akey not in ACTIVITY_FACTORS:
        akey = by_label.get(akey.lower(), "")
        if not akey:
            return None, [f"Unknown activity factor '{payload.get('activity_key')}'"]
    if not akey and fuel and factor_source == "default" and fuel.lower() in by_label and not _lookup_api_factor(fuel):
        akey = by_label[fuel.lower()]
    if akey:
        if process_type not in ACTIVITY_FACTORS[akey]["processes"]:
            return None, [f"'{ACTIVITY_FACTORS[akey]['label']}' is not a {process_type} factor"]
        payload["activity_key"] = akey
        if fuel.lower() == ACTIVITY_FACTORS[akey]["label"].strip().lower():
            payload.pop("fuel", None)
            fuel = ""

    # User uncertainty (percent per gas): an input of the calculation, as on the manual form, so the
    # stored value is the propagated 1-sigma result (it used to overwrite that result afterwards)
    user_unc = {}
    for gas, field in (("co2", "user_unc_co2"), ("ch4", "user_unc_ch4"), ("n2o", "user_unc_n2o")):
        payload.pop(field, None)
        if row.get(field) not in (None, ""):
            v = _clean_float(row.get(field), default=None)
            if v is None or v < 0:
                return None, [f"Invalid {field}: {row.get(field)} (a percentage)"]
            user_unc[gas] = v
    if user_unc:
        payload["user_uncertainty"] = user_unc

    try:
        payload = canonicalize(payload)
        validate_activity(payload, require_unit=factor_source in ("default", "custom"))
        factor_data = resolve_factor(payload) or {}
        if factor_source == "default" and fuel:
            if not factor_data:
                return None, [f"'{fuel}' is not in the emission factor catalog. Use the factor name exactly as listed, or a saved custom factor with factor type 'custom'."]
            check_factor_usage(process_type, factor_data, fuel)
        if factor_data.get("hhv") and not payload.get("hhv"):
            payload["hhv"] = factor_data["hhv"]
        em_result, method = compute_emissions_fn(payload, factor_data, gwp_dict=gwp_dict)
    except ValidationError as err:
        return None, [err.message]
    except ValueError as err:
        return None, [str(err)]
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Bulk Scope 1 row %s failed", row_idx)
        return None, ["The row could not be calculated; check its inputs"]  # BUG-087: no raw exception text

    if not em_result.get("totalCo2e"):
        em_result["totalCo2e"] = calculate_co2e(em_result.get("co2", 0), em_result.get("ch4", 0), em_result.get("n2o", 0), gwp_dict=gwp_dict)
    verdict, qa_msg = plausibility_check(em_result["totalCo2e"])  # BUG-007: same bounds as the manual form
    if verdict == "reject":
        return None, [qa_msg]

    source_ref = str(_first(row, "source_ref", "meter_id", "data_source_ref") or "").strip()
    equipment_id = str(_first(row, "equipment_id", "equipment") or "").strip()
    record = Emission(factor_source=factor_source, qa_flag=qa_msg[:255] if qa_msg else None)
    apply_result(record, payload, em_result, method, factor_data, gwp_std)
    record.ogmp_level = ogmp_level_for(record)

    # The key uses the stored (catalog) process and fuel names, as the keys of the existing records
    # do: a fuel written as an alias ("Diesel") must match the stored "Diesel (No. 2 Fuel Oil)".
    key = _scope1_key(facility.id, year, month, record.process_type or process_type,
                      record.fuel_type or fuel, equipment_id, source_ref)
    action, existing = _dedupe(
        batch_keys, key, overwrite_duplicates,
        f"Scope 1 emission for facility '{facility.name}' ({year}-{month:02d}, process '{process_type}', fuel '{fuel}'"
        + (f", source ref '{source_ref}'" if source_ref else "") + ")",
    )
    if action == "error":
        return None, [existing]

    if action == "update":
        obj = _resolve_existing(Emission, existing)
        if obj is not None:
            _bulk_overwrite(obj, {f: getattr(record, f) for f in _S1_RESULT_FIELDS}, user_id, "Scope 1")
            return None, []

    uploader = db.session.get(User, user_id)
    record.record_id = str(uuid.uuid4())
    record.created_by = user_id
    record.created_by_name = user_label(uploader)
    record.facility_id = facility.id
    record.year, record.month = year, month
    record.activity = row.get("activity") or facility.activity
    record.division = row.get("division") or facility.division
    # S1K-F12: for liquids unloading / associated gas venting the "region" column is the basin input
    # of the calculation (Table 6-10 / 6-8), not the organisational region of the record
    basin_column = process_type in ("unloading", "liquids_unloading", "associated_gas_venting")
    record.region = (None if basin_column else row.get("region")) or facility.region or facility.name
    record.field = row.get("field") or facility.field
    record.group_name = row.get("group") or row.get("group_name") or None
    record.equipment_id = equipment_id or None
    record.status = "Pending"  # Maker-Checker: bulk imports await reviewer approval
    record.data_source_ref = source_ref or None
    if batch_keys is not None:
        batch_keys[key] = record  # BUG-057: later in-file repeats update this row
    return record, []


def process_json_records(kind, records, user):
    """Rows of the JSON bulk endpoints (/production/bulk-import, /sources/bulk-import,
    /mitigation/bulk-import) through the same row validation as the file import.
    Adds the new objects to the session (the caller commits) and returns (count, errors)."""
    from extensions import db
    from models import Facility
    from utils import build_name_map, get_allowed_facility_ids

    allowed = get_allowed_facility_ids(user)
    facs = Facility.query.all() if allowed is None else Facility.query.filter(Facility.id.in_(allowed)).all()
    name_map = build_name_map(facs)
    id_map = {str(f.id): f for f in facs}
    batch_prod, batch_src = {}, set()
    count, errors = 0, []
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            errors.append(f"Row {i}: not an object")
            continue
        row = dict(rec)
        f_val = str(row.get("facility_id") or row.get("facility_name") or row.get("facility") or "").strip()
        row["facility_name"] = f_val
        if kind == "production":
            obj, errs = _process_row_production(row, user.id, name_map, id_map, batch_prod)
        elif kind == "sources":
            obj, errs = _process_row_sources(row, user.id, name_map, id_map, batch_src)
        elif kind == "mitigation":
            obj, errs = _process_row_mitigation(row, user.id, name_map, id_map)
        else:
            raise ValueError(kind)
        if errs:
            errors.append(f"Row {i}: " + "; ".join(errs))
            continue
        if obj is not None:
            db.session.add(obj)
        count += 1
    return count, errors
