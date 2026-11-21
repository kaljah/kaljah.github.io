"""
Executive Master Report & Intelligence Studio Endpoints
=====================================================
Provides publication-grade reporting endpoints:
1. POST /api/reports/master-report (enqueues background PDF generation job -> 202)
2. GET  /api/reports/master-report/jobs/<job_id> (polls generation job status)
3. GET  /api/reports/master-report/jobs/<job_id>/download (streams completed PDF)
4. GET  /api/reports/master-report/regions (available regions and assets)
5. POST /api/reports/master-report/benchmark-excel (executive cross-basin benchmark workbook)
"""

import hashlib
import io
import json
import logging
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import openpyxl
from flask import current_app, jsonify, request, send_file
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from extensions import db
from models import Facility
from routes.auth import login_required
from routes.reports import _safe_excel_value, reports_bp
from services.audit_chain import record_report_fingerprint
from services.master_report_data import aggregate_master_report_data
from services.master_report_engine import generate_master_publication_pdf
from services.regional_profiles import get_regional_profile, list_available_regions
from services.tenant_config import get_tenant_config
from utils import get_allowed_facility_ids, get_current_tenant_id, get_current_user, tenant_matches

logger = logging.getLogger(__name__)

_MASTER_JOBS_LOCK = threading.Lock()
_MASTER_JOBS: Dict[str, Dict[str, Any]] = {}
_MASTER_JOB_SEMAPHORE = threading.Semaphore(2)
_MAX_JOB_HISTORY = 100

_SAFE_JOB_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SAFE_FILENAME_CHAR_RE = re.compile(r"[^A-Za-z0-9 ._()-]+")
_VALID_MODES = ("regional", "national", "comparison")
_VALID_GWP_STANDARDS = ("AR4", "AR5", "AR6")
_VALID_LANGUAGES = ("en", "fr")
_MIN_REPORT_YEAR = 1990
_MAX_REPORT_YEAR = 2100
_MAX_YEAR_SPAN = 30


class _MasterReportValidationError(ValueError):
    """Validation error raised when explicit Master Report parameters are invalid."""

    def __init__(self, message: str, field: str):
        super().__init__(message)
        self.message = message
        self.field = field


def _sanitize_filename_part(raw: Any, fallback: str = "Report") -> str:
    """Strips control chars, path separators, and unsafe tokens while preserving safe punctuation."""
    text = re.sub(r"[\x00-\x1f\x7f]+", "", str(raw or ""))
    text = text.replace("/", "_").replace("\\", "_")
    text = re.sub(r"\.\.+", "_", text)
    cleaned = _SAFE_FILENAME_CHAR_RE.sub("_", text)
    cleaned = re.sub(r"\s+", " ", cleaned).lstrip(" ._").rstrip(" _")
    if not cleaned or not cleaned.strip(" ._"):
        return fallback
    return cleaned[:80]


def _parse_int_year(raw: Any, default: int, field: str) -> int:
    """Parses an explicit integer reporting year or returns default when omitted."""
    if raw is None:
        return default
    if isinstance(raw, bool):
        raise _MasterReportValidationError(f"{field} must be an integer year", field)
    if isinstance(raw, int):
        year = raw
    elif isinstance(raw, str) and re.fullmatch(r"[+-]?\d+", raw.strip()):
        year = int(raw.strip())
    else:
        raise _MasterReportValidationError(f"{field} must be an integer year", field)
    if year < _MIN_REPORT_YEAR or year > _MAX_REPORT_YEAR:
        raise _MasterReportValidationError(
            f"{field} must be between {_MIN_REPORT_YEAR} and {_MAX_REPORT_YEAR}",
            field,
        )
    return year


def _parse_str_choice(raw: Any, default: str, allowed: tuple[str, ...], field: str, *, upper: bool = False) -> str:
    """Parses an enumerated string parameter or returns default when omitted."""
    if raw is None:
        return default
    if not isinstance(raw, str):
        raise _MasterReportValidationError(f"{field} must be one of {', '.join(allowed)}", field)
    val = raw.strip().upper() if upper else raw.strip().lower()
    if val not in allowed:
        raise _MasterReportValidationError(f"{field} must be one of {', '.join(allowed)}", field)
    return val


def _parse_report_filters(
    *,
    allow_mode: bool = True,
    default_mode: str = "regional",
) -> Dict[str, Any]:
    """Validates JSON parameters for Master Report PDF and Benchmark Excel endpoints."""
    raw_body = request.get_data(as_text=True) or ""
    raw_payload = request.get_json(silent=True)
    if raw_body.strip() and raw_payload is None:
        raise _MasterReportValidationError("Malformed JSON payload", "payload")
    if raw_payload is None:
        payload: Dict[str, Any] = {}
    elif isinstance(raw_payload, dict):
        payload = raw_payload
    else:
        raise _MasterReportValidationError("JSON body must be an object", "payload")

    mode = (
        _parse_str_choice(payload.get("mode"), default_mode, _VALID_MODES, "mode", upper=False)
        if allow_mode
        else default_mode
    )

    raw_region = payload.get("region")
    if raw_region is not None and not isinstance(raw_region, str):
        raise _MasterReportValidationError("region must be a string", "region")
    region_key = raw_region.strip() if isinstance(raw_region, str) and raw_region.strip() else None
    if mode == "national":
        region_key = "national"

    start_year = _parse_int_year(payload.get("start_year"), 2023, "start_year")
    end_year = _parse_int_year(payload.get("end_year"), 2025, "end_year")
    if start_year > end_year:
        raise _MasterReportValidationError("start_year cannot exceed end_year", "start_year")
    if (end_year - start_year) > _MAX_YEAR_SPAN:
        raise _MasterReportValidationError(
            f"Reporting span cannot exceed {_MAX_YEAR_SPAN} years",
            "end_year",
        )

    from routes.auth import _app_settings

    gwp_standard = _parse_str_choice(
        payload.get("gwp_standard"),
        # the organisation's GWP standard when none is chosen (it was AR5 even on an AR6 system, BA-033)
        str(_app_settings.get("gwp_standard") or "AR5").upper(),
        _VALID_GWP_STANDARDS,
        "gwp_standard",
        upper=True,
    )
    language = _parse_str_choice(
        payload.get("language"),
        "en",
        _VALID_LANGUAGES,
        "language",
        upper=False,
    )

    return {
        "mode": mode,
        "region_key": region_key,
        "start_year": start_year,
        "end_year": end_year,
        "gwp_standard": gwp_standard,
        "language": language,
    }


def _unlink_if_exists(path_str: Any, label: str) -> None:
    """Removes an expired staged artifact if present, logging any OS failure."""
    if not path_str:
        return
    p = Path(path_str)
    if not p.exists():
        return
    try:
        p.unlink()
    except OSError as exc:
        logger.warning("Failed removing %s %s: %s", label, p, exc)


def _job_meta_path(job_id: str) -> Optional[Path]:
    """Returns validated disk snapshot path for a Master Report job ID."""
    if not _SAFE_JOB_ID_RE.fullmatch(str(job_id or "")):
        return None
    return get_master_jobs_dir() / f"{job_id}.json"


def _persist_job_snapshot(job_id: str, snapshot: Dict[str, Any]) -> None:
    """Atomically persists job metadata to disk so any WSGI worker can serve status polling."""
    meta_path = _job_meta_path(job_id)
    if meta_path is None:
        return
    tmp_path = meta_path.parent / f".tmp_{job_id}_{os.getpid()}_{threading.get_ident()}.json"
    try:
        tmp_path.write_text(json.dumps(snapshot, default=str), encoding="utf-8")
        os.replace(tmp_path, meta_path)
    except OSError as exc:
        logger.warning("Failed to persist master report job snapshot %s: %s", job_id, exc)
    finally:
        _unlink_if_exists(tmp_path, "temp job snapshot")


def _get_job_snapshot(job_id: str) -> Optional[Dict[str, Any]]:
    """Loads a Master Report job from RAM cache or cross-worker disk snapshot."""
    if not _SAFE_JOB_ID_RE.fullmatch(str(job_id or "")):
        return None
    with _MASTER_JOBS_LOCK:
        job = _MASTER_JOBS.get(job_id)
        if job is not None:
            return dict(job)

    meta_path = _job_meta_path(job_id)
    if meta_path is None or not meta_path.exists():
        return None
    try:
        loaded = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read master report job snapshot %s: %s", job_id, exc)
        return None
    if not isinstance(loaded, dict):
        return None
    with _MASTER_JOBS_LOCK:
        _MASTER_JOBS.setdefault(job_id, loaded)
        return dict(_MASTER_JOBS[job_id])


def get_master_jobs_dir() -> Path:
    """Returns directory used to stage generated Master Report PDFs."""
    custom = os.environ.get("MASTER_REPORT_JOBS_DIR", "").strip()
    if custom:
        jobs_dir = Path(custom)
    else:
        server_dir = Path(__file__).resolve().parent.parent
        jobs_dir = server_dir / "instance" / "master_report_jobs"
    jobs_dir.mkdir(parents=True, exist_ok=True)
    return jobs_dir


def clear_master_report_jobs() -> int:
    """Clears tracked jobs and staged PDF/metadata files. Used by sandbox reset and tests."""
    removed = 0
    with _MASTER_JOBS_LOCK:
        _MASTER_JOBS.clear()
    jobs_dir = get_master_jobs_dir()
    for pattern in ("*.pdf", "*.json"):
        for artifact in jobs_dir.glob(pattern):
            try:
                artifact.unlink()
                if pattern == "*.pdf":
                    removed += 1
            except OSError as exc:
                logger.warning("Failed removing staged report artifact %s: %s", artifact, exc)
    return removed


def _prune_old_jobs_locked() -> None:
    if len(_MASTER_JOBS) <= _MAX_JOB_HISTORY:
        return
    ordered = sorted(_MASTER_JOBS.items(), key=lambda kv: kv[1].get("created_at", ""))
    for job_id, meta in ordered[: len(_MASTER_JOBS) - _MAX_JOB_HISTORY]:
        if meta.get("status") not in ("completed", "failed"):
            continue
        _unlink_if_exists(meta.get("file_path"), "expired report PDF")
        _unlink_if_exists(_job_meta_path(job_id), "expired report metadata")
        _MASTER_JOBS.pop(job_id, None)


def _record_job_failure(flask_app, job_id: str, exc: Exception) -> None:
    """Logs job exception internally and stores a sanitized client-safe failure state."""
    logger.exception("Error generating Master Report job %s: %s", job_id, exc)
    try:
        flask_app.logger.error("Error generating Master Report job %s: %s", job_id, exc, exc_info=True)
    except Exception as log_exc:
        logger.warning("Flask logger failed recording Master Report job %s error: %s", job_id, log_exc)

    failed_snapshot: Optional[Dict[str, Any]] = None
    with _MASTER_JOBS_LOCK:
        if job_id in _MASTER_JOBS:
            _MASTER_JOBS[job_id].update({
                "status": "failed",
                "error": f"Failed to generate Master Publication Report (ref: {job_id[:8]}).",
            })
            failed_snapshot = dict(_MASTER_JOBS[job_id])
    if failed_snapshot is not None:
        _persist_job_snapshot(job_id, failed_snapshot)


def _execute_and_store_job_pdf(
    flask_app,
    job_id: str,
    mode: str,
    region_key: Any,
    start_year: int,
    end_year: int,
    gwp_standard: str,
    allowed_ids: Any,
    language: str,
    tenant_id: str,
) -> None:
    """Generates the Master Report PDF inside app context, stages it atomically, and updates status."""
    with flask_app.app_context():
        try:
            pdf_buffer = generate_master_publication_pdf(
                mode=mode,
                region_key=region_key,
                start_year=start_year,
                end_year=end_year,
                gwp_standard=gwp_standard,
                allowed_facility_ids=allowed_ids,
                language=language,
                tenant_id=tenant_id,
            )
            pdf_bytes = pdf_buffer.getvalue()
            report_sha256 = getattr(pdf_buffer, "report_hash", None) or hashlib.sha256(pdf_bytes).hexdigest()
            dataset_sha256 = getattr(pdf_buffer, "dataset_hash", None)
        finally:
            db.session.remove()

    jobs_dir = get_master_jobs_dir()
    pdf_path = jobs_dir / f"{job_id}.pdf"
    tmp_path = jobs_dir / f".tmp_{job_id}.pdf"
    tmp_path.write_bytes(pdf_bytes)
    os.replace(tmp_path, pdf_path)

    completed_snapshot: Optional[Dict[str, Any]] = None
    with _MASTER_JOBS_LOCK:
        if job_id in _MASTER_JOBS:
            _MASTER_JOBS[job_id].update({
                "status": "completed",
                "file_path": str(pdf_path),
                "sha256": report_sha256,
                "dataset_sha256": dataset_sha256,
                "size_bytes": len(pdf_bytes),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
            completed_snapshot = dict(_MASTER_JOBS[job_id])
            _prune_old_jobs_locked()
    if completed_snapshot is not None:
        _persist_job_snapshot(job_id, completed_snapshot)


def _run_master_report_job(
    flask_app,
    job_id: str,
    mode: str,
    region_key: Any,
    start_year: int,
    end_year: int,
    gwp_standard: str,
    allowed_ids: Any,
    language: str,
    tenant_id: str = "default",
) -> None:
    with _MASTER_JOB_SEMAPHORE:
        running_snapshot: Optional[Dict[str, Any]] = None
        with _MASTER_JOBS_LOCK:
            if job_id not in _MASTER_JOBS:
                return
            _MASTER_JOBS[job_id]["status"] = "running"
            running_snapshot = dict(_MASTER_JOBS[job_id])
        _persist_job_snapshot(job_id, running_snapshot)

        try:
            _execute_and_store_job_pdf(
                flask_app, job_id, mode, region_key, start_year, end_year, gwp_standard, allowed_ids, language, tenant_id
            )
        except Exception as exc:
            _record_job_failure(flask_app, job_id, exc)


@reports_bp.route("/master-report/regions", methods=["GET"])
@login_required
def get_master_report_regions():
    """Returns available regions strictly present for the caller's tenant."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)
    tenant = get_tenant_config(caller_tenant)
    allowed_ids = get_allowed_facility_ids(user)
    all_profiles = list_available_regions(tenant_config=tenant)

    # Query facilities in caller's tenant/facility scope
    fac_query = Facility.query.filter(tenant_matches(Facility.tenant_id, caller_tenant))
    if allowed_ids is not None:
        fac_query = fac_query.filter(Facility.id.in_(allowed_ids or [-1]))
    facilities = fac_query.all()

    if not facilities:
        return jsonify({"status": "success", "regions": []})

    regions_by_key: Dict[str, Dict[str, Any]] = {}
    matched_fac_ids = set()

    # 1. Match known regional profiles that have monitored facilities in this tenant
    for r in all_profiles:
        rk = r["key"].lower()
        if rk == "national":
            continue
        rk_spaced = rk.replace("_", " ").replace("-", " ")
        p = get_regional_profile(rk, tenant_config=tenant)
        aliases = [a.lower() for a in p.get("aliases", [])]
        matched_facs = []
        for f in facilities:
            reg_str = (f.region or "").lower()
            name_str = (f.name or "").lower()
            field_str = (f.field or "").lower()
            loc_str = (f.location or "").lower()
            if (
                rk in reg_str or rk in name_str or rk in field_str or rk in loc_str
                or (rk_spaced and (
                    rk_spaced in reg_str or rk_spaced in name_str
                    or rk_spaced in field_str or rk_spaced in loc_str
                ))
                or any(
                    alias in reg_str or alias in name_str
                    or alias in field_str or alias in loc_str
                    for alias in aliases
                )
            ):
                matched_facs.append(f)
        if matched_facs:
            r_copy = dict(r)
            r_copy["facility_count"] = len(matched_facs)
            r_copy["facility_names"] = [f.name for f in matched_facs]
            regions_by_key[r_copy["key"]] = r_copy
            for f in matched_facs:
                matched_fac_ids.add(f.id)

    # 2. Dynamically include any custom facility regions present for this tenant
    unmatched_facs = [f for f in facilities if f.id not in matched_fac_ids]
    custom_map: Dict[str, List[Facility]] = {}
    for f in unmatched_facs:
        reg_name = f.region or f.location or f.name
        if not reg_name or reg_name.lower() in ("algeria", "global", "south", "none"):
            continue
        custom_map.setdefault(reg_name, []).append(f)

    for reg_name, fac_list in custom_map.items():
        clean_key = reg_name.lower().replace(" ", "_").replace("/", "_")
        if clean_key == "national":
            continue
        existing = regions_by_key.get(clean_key)
        if existing is not None:
            merged_names = list(dict.fromkeys(list(existing.get("facility_names", [])) + [f.name for f in fac_list]))
            existing["facility_names"] = merged_names
            existing["facility_count"] = len(merged_names)
        else:
            regions_by_key[clean_key] = {
                "key": clean_key,
                "name": f"{reg_name} Production Area",
                "segment": fac_list[0].segment or "Upstream",
                "facility_count": len(fac_list),
                "facility_names": [f.name for f in fac_list],
            }

    present_regions = list(regions_by_key.values())

    # 3. Add National (Consolidated Group) if facilities exist in this tenant
    if facilities:
        nat_name = tenant.get("national_group_name") or f"{tenant.get('organization_name', 'Corporate')} Group (Consolidated National)"
        national_entry = next((r for r in all_profiles if r["key"] == "national"), {
            "key": "national",
            "name": nat_name,
            "segment": "Integrated",
        })
        nat_copy = dict(national_entry)
        if nat_copy.get("name") == "Demo Operator Group (Consolidated National)":
            nat_copy["name"] = nat_name
        if "demo operator" in str(nat_copy.get("name") or "").lower():
            # the list is built from the facilities: an unconfigured install offered the demo group's name as a
            # basin (GB RY2022 GB-053)
            nat_copy["name"] = "All facilities (consolidated)"
        nat_copy["facility_count"] = len(facilities)
        present_regions.insert(0, nat_copy)

    return jsonify({"status": "success", "regions": present_regions})


@reports_bp.route("/master-report", methods=["POST"])
@login_required
def generate_master_report_endpoint():
    """Enqueues Master Report PDF generation as a background job and returns 202."""
    user = get_current_user()
    allowed_ids = get_allowed_facility_ids(user)
    try:
        parsed = _parse_report_filters(allow_mode=True, default_mode="regional")
    except _MasterReportValidationError as exc:
        return jsonify({"error": exc.message, "field": exc.field}), 400

    mode = parsed["mode"]
    region_key = parsed["region_key"]
    start_year = parsed["start_year"]
    end_year = parsed["end_year"]
    gwp_standard = parsed["gwp_standard"]
    language = parsed["language"]

    caller_tenant = get_current_tenant_id(user)
    tenant = get_tenant_config(caller_tenant)
    org_prefix = _sanitize_filename_part(tenant.get("organization_name"), "Operator")
    time_tag = f"{start_year}" if start_year == end_year else f"{start_year}_{end_year}"
    clean_name = _sanitize_filename_part(
        region_key.capitalize() if region_key else "National",
        "National",
    ).replace(" ", "_")
    lang_tag = f"_{language.upper()}"
    filename = f"{org_prefix}_{mode.capitalize()}_{clean_name}_Master_Report_{time_tag}{lang_tag}.pdf"

    job_id = uuid.uuid4().hex
    status_url = f"/api/reports/master-report/jobs/{job_id}"
    download_url = f"/api/reports/master-report/jobs/{job_id}/download"
    filters = {
        "mode": mode,
        "region": region_key,
        "start_year": start_year,
        "end_year": end_year,
        "gwp_standard": gwp_standard,
        "language": language,
    }

    initial_snapshot = {
        "job_id": job_id,
        "user_id": user.id,
        "tenant_id": caller_tenant,
        "status": "queued",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "filename": filename,
        "filters": filters,
        "status_url": status_url,
        "download_url": download_url,
        "file_path": None,
        "sha256": None,
        "dataset_sha256": None,
        "size_bytes": None,
        "generated_at": None,
        "error": None,
    }
    with _MASTER_JOBS_LOCK:
        _MASTER_JOBS[job_id] = dict(initial_snapshot)
    _persist_job_snapshot(job_id, initial_snapshot)

    flask_app = current_app._get_current_object()
    worker = threading.Thread(
        target=_run_master_report_job,
        args=(
            flask_app,
            job_id,
            mode,
            region_key,
            start_year,
            end_year,
            gwp_standard,
            list(allowed_ids) if allowed_ids is not None else None,
            language,
            caller_tenant,
        ),
        daemon=True,
        name=f"master-report-{job_id[:8]}",
    )
    worker.start()

    return (
        jsonify({
            "job_id": job_id,
            "status": "queued",
            "status_url": status_url,
            "download_url": download_url,
            "filename": filename,
        }),
        202,
    )


@reports_bp.route("/master-report/jobs/<job_id>", methods=["GET"])
@login_required
def get_master_report_job_status(job_id: str):
    """Returns current status and download metadata for a Master Report job."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)

    job = _get_job_snapshot(job_id)
    if not job:
        return jsonify({"error": "Report job not found"}), 404
    if job.get("tenant_id") != caller_tenant or job.get("user_id") != user.id:
        return jsonify({"error": "Forbidden"}), 403
    snapshot = {
        "job_id": job["job_id"],
        "status": job["status"],
        "status_url": job["status_url"],
        "download_url": job["download_url"] if job["status"] == "completed" else None,
        "filename": job["filename"],
        "sha256": job.get("sha256"),
        "dataset_sha256": job.get("dataset_sha256"),
        "size_bytes": job.get("size_bytes"),
        "generated_at": job.get("generated_at"),
        "error": job.get("error"),
    }
    return jsonify(snapshot), 200


@reports_bp.route("/master-report/jobs/<job_id>/download", methods=["GET"])
@login_required
def download_master_report_job(job_id: str):
    """Downloads a completed Master Report PDF job."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)

    job = _get_job_snapshot(job_id)
    if not job:
        return jsonify({"error": "Report job not found"}), 404
    if job.get("tenant_id") != caller_tenant or job.get("user_id") != user.id:
        return jsonify({"error": "Forbidden"}), 403
    status = job["status"]
    file_path = job.get("file_path")
    filename = job["filename"]
    report_sha256 = job.get("sha256")
    dataset_sha256 = job.get("dataset_sha256")
    filters = dict(job.get("filters") or {})
    error_msg = job.get("error")
    generated_at = job.get("generated_at")

    if status in ("queued", "running"):
        return jsonify({"status": status, "error": "Report generation still in progress"}), 409
    if status == "failed":
        return jsonify({"status": "failed", "error": error_msg or "Report generation failed"}), 500
    if not file_path or not os.path.exists(file_path):
        return jsonify({"error": "Generated PDF file no longer available"}), 404

    with open(file_path, "rb") as fh:
        pdf_bytes = fh.read()
    report_sha256 = report_sha256 or hashlib.sha256(pdf_bytes).hexdigest()

    resp = send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )
    resp.headers["X-Audit-Timestamp"] = generated_at or datetime.now(timezone.utc).isoformat()
    resp.headers["X-Report-SHA256"] = report_sha256
    if dataset_sha256:
        resp.headers["X-Dataset-SHA256"] = dataset_sha256
    mode = filters.get("mode", "regional")
    return record_report_fingerprint(resp, user, f"Master Publication Report ({mode})", filters, 1, report_sha256)


def _style_excel_header(ws, col_count: int, title: str, subtitle: str):
    """Styles the corporate header block for benchmark Excel workbooks."""
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    sub_fill = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
    white_bold = Font(name="Calibri", size=13, bold=True, color="FFFFFF")
    white_sub = Font(name="Calibri", size=10, bold=True, color="FFFFFF")

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=col_count)
    c1 = ws.cell(row=1, column=1, value=_safe_excel_value(title.upper()))
    c1.fill = header_fill
    c1.font = white_bold
    c1.alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=col_count)
    c2 = ws.cell(row=2, column=1, value=_safe_excel_value(subtitle))
    c2.fill = sub_fill
    c2.font = white_sub
    c2.alignment = Alignment(horizontal="center", vertical="center")


@reports_bp.route("/master-report/benchmark-excel", methods=["POST"])
@login_required
def export_benchmark_excel():
    """Generates an executive cross-basin benchmark Excel workbook."""
    user = get_current_user()
    caller_tenant = get_current_tenant_id(user)
    allowed_ids = get_allowed_facility_ids(user)
    try:
        parsed = _parse_report_filters(allow_mode=False, default_mode="comparison")
    except _MasterReportValidationError as exc:
        return jsonify({"error": exc.message, "field": exc.field}), 400

    start_year = parsed["start_year"]
    end_year = parsed["end_year"]
    gwp_standard = parsed["gwp_standard"]

    data = aggregate_master_report_data("comparison", None, start_year, end_year, gwp_standard, allowed_ids, tenant_id=caller_tenant)
    benchmarks = data.get("regional_benchmarks", [])

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cross-Basin Benchmark"

    cols = [
        "Basin / Regional Asset",
        "Operational Segment",
        "Facilities Monitored",
        "Aggregate Deliverability (MMBOE)",
        "Scope 1+2 GHG (tCO2e)",
        "Carbon Intensity (kg CO2e/BOE)",
        "Flaring Intensity (% Gas)",
        "Decree 21-330 Status (<= 1.00%)",
    ]
    tenant = get_tenant_config(caller_tenant)
    org_name = tenant.get("organization_name", "Operator")
    _style_excel_header(ws, len(cols), f"{org_name} // Cross-Basin Benchmark & Intelligence Matrix", f"Period: {start_year} - {end_year} | Standard: ISO 14064-1 & Décret 21-330")

    # Table Header
    th_fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    th_font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    border_thin = Border(
        left=Side(style="thin", color="CBD5E1"),
        right=Side(style="thin", color="CBD5E1"),
        top=Side(style="thin", color="CBD5E1"),
        bottom=Side(style="thin", color="CBD5E1"),
    )

    for col_idx, col_name in enumerate(cols, 1):
        cell = ws.cell(row=4, column=col_idx, value=_safe_excel_value(col_name))
        cell.fill = th_fill
        cell.font = th_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    # Populate rows
    for r_idx, b in enumerate(benchmarks, 5):
        row_vals = [
            b.get("name", ""),
            b.get("segment", "Upstream"),
            b.get("facility_count", 1),
            round(b.get("total_mmboe", 0.0), 3),
            round(b.get("total_co2e_t", 0.0), 1),
            # "n/a" without production: 0.00 % "COMPLIANT" was printed (audit 2026-11 F-GUI2-08)
            round(b["carbon_intensity_kg_boe"], 2) if b.get("carbon_intensity_kg_boe") is not None else "n/a",
            f"{b['flaring_intensity_pct']:.2f}%" if b.get("flaring_intensity_pct") is not None else "n/a",
            {True: "COMPLIANT", False: "EXCEEDED CAP"}.get(b.get("decree_compliant"), "NOT ASSESSABLE"),
        ]
        for c_idx, v in enumerate(row_vals, 1):
            cell = ws.cell(row=r_idx, column=c_idx, value=_safe_excel_value(v))
            cell.border = border_thin
            cell.font = Font(name="Calibri", size=9.5)
            if c_idx == 8:
                cell.font = Font(name="Calibri", size=9.5, bold=True, color="166534" if "COMPLIANT" in str(v) else "991B1B")

    # Auto-fit columns
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    hash_val = hashlib.sha256(buf.getvalue()).hexdigest()

    safe_org = _sanitize_filename_part(org_name, "Operator")
    filename = f"{safe_org}_Cross_Basin_Benchmark_{start_year}_{end_year}.xlsx"
    resp = send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )
    resp.headers["X-Audit-Timestamp"] = datetime.now(timezone.utc).isoformat()
    resp.headers["X-Report-SHA256"] = hash_val
    return resp
