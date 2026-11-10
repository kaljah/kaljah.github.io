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
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

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
from utils import get_allowed_facility_ids, get_current_user

_MASTER_JOBS_LOCK = threading.Lock()
_MASTER_JOBS: Dict[str, Dict[str, Any]] = {}
_MASTER_JOB_SEMAPHORE = threading.Semaphore(2)
_MAX_JOB_HISTORY = 100


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
    """Clears tracked jobs and staged PDF files. Used by sandbox reset and tests."""
    removed = 0
    with _MASTER_JOBS_LOCK:
        _MASTER_JOBS.clear()
    jobs_dir = get_master_jobs_dir()
    for pdf_file in jobs_dir.glob("*.pdf"):
        try:
            pdf_file.unlink()
            removed += 1
        except OSError:
            pass
    return removed


def _prune_old_jobs_locked() -> None:
    if len(_MASTER_JOBS) <= _MAX_JOB_HISTORY:
        return
    ordered = sorted(_MASTER_JOBS.items(), key=lambda kv: kv[1].get("created_at", ""))
    for job_id, meta in ordered[: len(_MASTER_JOBS) - _MAX_JOB_HISTORY]:
        if meta.get("status") in ("completed", "failed"):
            pdf_path = meta.get("file_path")
            if pdf_path and os.path.exists(pdf_path):
                try:
                    os.unlink(pdf_path)
                except OSError:
                    pass
            _MASTER_JOBS.pop(job_id, None)


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
) -> None:
    with _MASTER_JOB_SEMAPHORE:
        with _MASTER_JOBS_LOCK:
            if job_id not in _MASTER_JOBS:
                return
            _MASTER_JOBS[job_id]["status"] = "running"

        try:
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
                    )
                    pdf_bytes = pdf_buffer.getvalue()
                    report_sha256 = getattr(pdf_buffer, "report_hash", None) or hashlib.sha256(pdf_bytes).hexdigest()
                finally:
                    db.session.remove()

            jobs_dir = get_master_jobs_dir()
            pdf_path = jobs_dir / f"{job_id}.pdf"
            tmp_path = jobs_dir / f".tmp_{job_id}.pdf"
            tmp_path.write_bytes(pdf_bytes)
            os.replace(tmp_path, pdf_path)

            with _MASTER_JOBS_LOCK:
                if job_id in _MASTER_JOBS:
                    _MASTER_JOBS[job_id].update({
                        "status": "completed",
                        "file_path": str(pdf_path),
                        "sha256": report_sha256,
                        "size_bytes": len(pdf_bytes),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                    })
                    _prune_old_jobs_locked()
        except Exception as exc:
            try:
                flask_app.logger.error(f"Error generating Master Report job {job_id}: {exc}", exc_info=True)
            except Exception:
                pass
            with _MASTER_JOBS_LOCK:
                if job_id in _MASTER_JOBS:
                    _MASTER_JOBS[job_id].update({
                        "status": "failed",
                        "error": f"Failed to generate Master Publication Report: {str(exc)}",
                    })


@reports_bp.route("/master-report/regions", methods=["GET"])
@login_required
def get_master_report_regions():
    """Returns available regions strictly present in the software database."""
    user = get_current_user()
    allowed_ids = get_allowed_facility_ids(user)
    all_profiles = list_available_regions()

    # Query facilities in scope
    fac_query = Facility.query
    if allowed_ids is not None:
        fac_query = fac_query.filter(Facility.id.in_(allowed_ids))
    facilities = fac_query.all()

    # If database has no facilities yet, return the default regional registry
    if not facilities:
        fallback_regions = []
        for r in all_profiles:
            rc = dict(r)
            rc["facility_count"] = 0
            fallback_regions.append(rc)
        return jsonify({"status": "success", "regions": fallback_regions})

    present_regions = []
    matched_fac_ids = set()

    # 1. Match known regional profiles that have monitored facilities in the software
    for r in all_profiles:
        rk = r["key"].lower()
        if rk == "national":
            continue
        p = get_regional_profile(rk)
        aliases = [a.lower() for a in p.get("aliases", [])]
        matched_facs = [
            f for f in facilities
            if rk in (f.region or "").lower() or rk in (f.name or "").lower()
            or any(alias in (f.region or "").lower() or alias in (f.name or "").lower() for alias in aliases)
        ]
        if matched_facs:
            r_copy = dict(r)
            r_copy["facility_count"] = len(matched_facs)
            r_copy["facility_names"] = [f.name for f in matched_facs]
            present_regions.append(r_copy)
            for f in matched_facs:
                matched_fac_ids.add(f.id)

    # 2. Dynamically include any custom facility regions present in the software
    unmatched_facs = [f for f in facilities if f.id not in matched_fac_ids]
    custom_map: Dict[str, List[Facility]] = {}
    for f in unmatched_facs:
        reg_name = f.region or f.location or f.name
        if not reg_name or reg_name.lower() in ("algeria", "global", "south", "none"):
            continue
        custom_map.setdefault(reg_name, []).append(f)

    for reg_name, fac_list in custom_map.items():
        clean_key = reg_name.lower().replace(" ", "_").replace("/", "_")
        present_regions.append({
            "key": clean_key,
            "name": f"{reg_name} Production Area",
            "segment": fac_list[0].segment or "Upstream",
            "facility_count": len(fac_list),
            "facility_names": [f.name for f in fac_list],
        })

    # 3. Add National (Consolidated Group) if facilities exist
    if facilities:
        tenant = get_tenant_config()
        nat_name = tenant.get("national_group_name") or f"{tenant.get('organization_name', 'Corporate')} Group (Consolidated National)"
        national_entry = next((r for r in all_profiles if r["key"] == "national"), {
            "key": "national",
            "name": nat_name,
            "segment": "Integrated",
        })
        nat_copy = dict(national_entry)
        if nat_copy.get("name") == "Demo Operator Group (Consolidated National)":
            nat_copy["name"] = nat_name
        nat_copy["facility_count"] = len(facilities)
        present_regions.insert(0, nat_copy)

    return jsonify({"status": "success", "regions": present_regions})


@reports_bp.route("/master-report", methods=["POST"])
@login_required
def generate_master_report_endpoint():
    """Enqueues Master Report PDF generation as a background job and returns 202."""
    user = get_current_user()
    allowed_ids = get_allowed_facility_ids(user)
    payload = request.get_json() or {}

    mode = str(payload.get("mode", "regional")).lower()
    if mode not in ("regional", "national", "comparison"):
        mode = "regional"

    region_key = payload.get("region")
    if mode == "national":
        region_key = "national"

    try:
        start_year = int(payload.get("start_year", 2023))
        end_year = int(payload.get("end_year", 2025))
    except (ValueError, TypeError):
        start_year, end_year = 2023, 2025

    if start_year > end_year:
        start_year, end_year = end_year, start_year

    gwp_standard = str(payload.get("gwp_standard", "AR5")).upper()
    if gwp_standard not in ("AR4", "AR5", "AR6"):
        gwp_standard = "AR5"

    language = str(payload.get("language", "en")).lower()
    if language not in ("en", "fr"):
        language = "en"

    tenant = get_tenant_config()
    org_prefix = tenant.get("organization_name", "Operator")
    time_tag = f"{start_year}" if start_year == end_year else f"{start_year}_{end_year}"
    clean_name = (region_key.capitalize() if region_key else "National").replace(" ", "_").replace("/", "_")
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

    with _MASTER_JOBS_LOCK:
        _MASTER_JOBS[job_id] = {
            "job_id": job_id,
            "user_id": user.id,
            "tenant_id": getattr(user, "tenant_id", None) or "default",
            "status": "queued",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "filename": filename,
            "filters": filters,
            "status_url": status_url,
            "download_url": download_url,
            "file_path": None,
            "sha256": None,
            "size_bytes": None,
            "generated_at": None,
            "error": None,
        }

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
    caller_tenant = getattr(user, "tenant_id", None) or "default"

    with _MASTER_JOBS_LOCK:
        job = _MASTER_JOBS.get(job_id)
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
    caller_tenant = getattr(user, "tenant_id", None) or "default"

    with _MASTER_JOBS_LOCK:
        job = _MASTER_JOBS.get(job_id)
        if not job:
            return jsonify({"error": "Report job not found"}), 404
        if job.get("tenant_id") != caller_tenant or job.get("user_id") != user.id:
            return jsonify({"error": "Forbidden"}), 403
        status = job["status"]
        file_path = job.get("file_path")
        filename = job["filename"]
        report_sha256 = job.get("sha256")
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
    allowed_ids = get_allowed_facility_ids(user)
    payload = request.get_json() or {}

    start_year = int(payload.get("start_year", 2023))
    end_year = int(payload.get("end_year", 2025))
    gwp_standard = str(payload.get("gwp_standard", "AR5")).upper()

    data = aggregate_master_report_data("comparison", None, start_year, end_year, gwp_standard, allowed_ids)
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
    tenant = get_tenant_config()
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
            round(b.get("carbon_intensity_kg_boe", 0.0), 2),
            f"{b.get('flaring_intensity_pct', 0.0):.2f}%",
            "COMPLIANT" if b.get("decree_compliant") else "EXCEEDED CAP",
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

    filename = f"{org_name}_Cross_Basin_Benchmark_{start_year}_{end_year}.xlsx"
    resp = send_file(
        buf,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename,
    )
    resp.headers["X-Audit-Timestamp"] = datetime.now(timezone.utc).isoformat()
    resp.headers["X-Report-SHA256"] = hash_val
    return resp
