"""
Forensic & Assurance Regression Suite for Master Publication Reports
====================================================================
Guards all factual, stoichiometric, governance, cryptographic, 2-pass TOC,
Unicode font, and empty-state disclosure fixes across EN & FR reports.
"""

from __future__ import annotations

import hashlib
import io
import logging
import os
from pathlib import Path
import re
import tempfile
import time
import uuid

import matplotlib.pyplot as plt
import pypdfium2
import pytest

from app import app
from extensions import db, limiter
from models import (
    BaseYearRecalculation,
    CbamProductExport,
    ComponentInventory,
    CustomFactor,
    Emission,
    EmissionSource,
    Facility,
    FacilityEquityShare,
    JvPartner,
    MitigationProject,
    OgmpSurvey,
    PeriodLock,
    ProductionData,
    ReportingMetadata,
    SbtiTarget,
    Scope3Emission,
    User,
)
import routes.reports_master as reports_master_route
from routes.reports_master import (
    _MASTER_JOBS,
    _MASTER_JOBS_LOCK,
    _job_meta_path,
    _sanitize_filename_part,
)
from services.master_report_appendices import build_equipment_census_elements
from services.master_report_charts import (
    _MAX_PFD_BASE_CACHE_ENTRIES,
    _PFD_BASE_CACHE,
    _get_pfd_base_template,
    clear_chart_cache,
    generate_cbam_embeddings_chart,
    generate_ogmp_reconciliation_chart,
    generate_scope3_category_chart,
)
from services.master_report_data import aggregate_master_report_data
import services.master_report_engine as master_report_engine
from services.master_report_engine import (
    MasterReportPdfBuffer,
    _build_styles,
    generate_master_publication_pdf,
)

logger = logging.getLogger(__name__)


def _extract_pages(pdf_bytes: bytes) -> list[str]:
    doc = pypdfium2.PdfDocument(pdf_bytes)
    try:
        pages = []
        for idx in range(len(doc)):
            page = doc[idx]
            tp = page.get_textpage()
            try:
                pages.append(" ".join(tp.get_text_range().split()))
            finally:
                tp.close()
                page.close()
        return pages
    finally:
        doc.close()


def _create_isolated_tenant_fixture(*, with_gc: bool = False, extra_emissions=None):
    tag = uuid.uuid4().hex[:8]
    tid = f"for_{tag}"
    with app.app_context():
        user = User(
            email=f"forensic_{tag}@example.org",
            fullName=f"Forensic Admin {tag}",
            orgName=f"Forensic Co {tag}",
            sector="Oil & Gas",
            role="admin",
            status="active",
            tenant_id=tid,
        )
        user.set_password("ForensicTest!123")
        db.session.add(user)
        db.session.flush()

        fac = Facility(
            name=f"Forensic CPF {tag}",
            code=f"FOR-{tag}",
            region="Basin Alpha",
            segment="Upstream",
            country="Algeria",
            description=f"Custom DB facility topology notes {tag}",
            boundary_notes=f"Custom DB boundary perimeter {tag}",
            tenant_id=tid,
        )
        db.session.add(fac)
        db.session.flush()

        src = EmissionSource(
            facility_id=fac.id,
            name=f"Turbine F1 {tag}",
            code=f"SRC-F1-{tag}",
            equipment_id=f"EQ-F1-{tag}",
            type="stationary_combustion",
            activity="Stationary Combustion",
            status="Active",
        )
        db.session.add(src)

        em_ver = Emission(
            facility_id=fac.id,
            equipment_id=f"EQ-F1-{tag}",
            year=2024,
            month=6,
            process_type="stationary_combustion",
            fuel_type="Natural Gas",
            quantity=1000.0,
            unit="m3",
            co2_emissions=190.0,
            ch4_emissions=80.0,
            n2o_emissions=0.01,
            co2e_total=200.0,
            status="Verified",
            created_by=user.id,
            is_test=False,
        )
        db.session.add(em_ver)

        if extra_emissions:
            for item in extra_emissions(fac, user, tag):
                db.session.add(item)

        prod = ProductionData(
            facility_id=fac.id,
            year=2024,
            month=6,
            oil_amount=1000.0,
            gas_amount=100.0,
            gross_gas_mmsm3=100.0,
            injected_gas_mmsm3=40.0,
            gas_without_injected_mmsm3=60.0,
            crude_oil_mmboe=0.1,
            total_production_mmboe=0.5,
        )
        db.session.add(prod)

        cf_id = None
        if with_gc:
            cf = CustomFactor(
                facility_id=fac.id,
                name=f"Forensic GC Assay {tag}",
                parent_fuel="natural_gas",
                co2_factor=55.0,
                ch4_factor=0.001,
                n2o_factor=0.0001,
                unit="kg/MMBtu",
                status="Approved",
                is_archived=False,
                is_test=False,
                tenant_id=tid,
                gas_composition={
                    "ch4_mol_pct": 92.0,
                    "c2h6_mol_pct": 4.0,
                    "c3h8_mol_pct": 1.5,
                    "co2_mol_pct": 1.5,
                    "n2_mol_pct": 1.0,
                    "hhv_btu_scf": 1035.0,
                    "mw_kg_mole": 17.6,
                    "carbon_content": 0.745,
                },
            )
            db.session.add(cf)
            db.session.flush()
            cf_id = cf.id

        db.session.commit()
        return {
            "tag": tag,
            "tenant_id": tid,
            "user_id": user.id,
            "fac_id": fac.id,
            "cf_id": cf_id,
        }


def _remove_artifact_path(path_obj: Path | str | None) -> None:
    if not path_obj:
        return
    try:
        Path(path_obj).unlink(missing_ok=True)
    except OSError as exc:
        logger.warning("Failed cleaning test artifact %s: %s", path_obj, exc)


def _cleanup_isolated_tenant_fixture(info: dict):
    tid = info["tenant_id"]
    uid = info["user_id"]
    with app.app_context():
        db.session.rollback()
        with _MASTER_JOBS_LOCK:
            matching_jobs = [
                (jid, jdata)
                for jid, jdata in _MASTER_JOBS.items()
                if jdata.get("user_id") == uid or jdata.get("tenant_id") == tid
            ]
            for jid, jdata in matching_jobs:
                _remove_artifact_path(jdata.get("file_path"))
                _remove_artifact_path(_job_meta_path(jid))
                _MASTER_JOBS.pop(jid, None)

        fac_ids = [r[0] for r in db.session.query(Facility.id).filter_by(tenant_id=tid).all()]
        if info.get("fac_id") and info["fac_id"] not in fac_ids:
            fac_ids.append(info["fac_id"])
        if fac_ids:
            FacilityEquityShare.query.filter(FacilityEquityShare.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            ComponentInventory.query.filter(ComponentInventory.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            MitigationProject.query.filter(MitigationProject.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            CbamProductExport.query.filter(CbamProductExport.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            Scope3Emission.query.filter(Scope3Emission.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            OgmpSurvey.query.filter(OgmpSurvey.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            CustomFactor.query.filter(CustomFactor.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            EmissionSource.query.filter(EmissionSource.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            Emission.query.filter(Emission.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            ProductionData.query.filter(ProductionData.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            Facility.query.filter(Facility.id.in_(fac_ids)).delete(synchronize_session=False)

        JvPartner.query.filter_by(tenant_id=tid).delete(synchronize_session=False)
        PeriodLock.query.filter_by(tenant_id=tid).delete(synchronize_session=False)
        BaseYearRecalculation.query.filter_by(tenant_id=tid).delete(synchronize_session=False)
        SbtiTarget.query.filter_by(tenant_id=tid).delete(synchronize_session=False)
        User.query.filter_by(tenant_id=tid).delete(synchronize_session=False)
        db.session.commit()


def _assert_empty_chart_outputs_en_fr(data: dict) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        for fn, payload in (
            (generate_ogmp_reconciliation_chart, data["ogmp"]),
            (generate_scope3_category_chart, data["scope3"]),
            (generate_cbam_embeddings_chart, data["cbam_macc"]),
        ):
            for lang in ("en", "fr"):
                out_png = os.path.join(tmp, f"{fn.__name__}_{lang}.png")
                fn(payload, out_png, language=lang, use_cache=False)
                assert os.path.exists(out_png) and os.path.getsize(out_png) > 5_000
        assert plt.get_fignums() == []


def test_forensic_empty_modules_and_charts_honest_states_en_fr():
    info = _create_isolated_tenant_fixture()
    try:
        with app.app_context():
            data = aggregate_master_report_data(
                "regional", "basin_alpha", 2024, 2024, "AR5", tenant_id=info["tenant_id"]
            )
            assert data["ogmp"]["has_data"] is False
            assert data["scope3"]["has_data"] is False
            assert data["cbam_macc"]["has_cbam_data"] is False
            assert data["decarbonization_projects"] == []
            assert data["base_year_recalcs"] == []
            _assert_empty_chart_outputs_en_fr(data)

            for lang in ("en", "fr"):
                buf = generate_master_publication_pdf(
                    mode="regional",
                    region_key="basin_alpha",
                    start_year=2024,
                    end_year=2024,
                    gwp_standard="AR5",
                    language=lang,
                    tenant_id=info["tenant_id"],
                )
                pages = _extract_pages(buf.getvalue())
                full_text = " ".join(pages)

                # Zero fabricated fallback strings
                for fake in (
                    "Aerial LiDAR",
                    "Bridger Photonics",
                    "845.0",
                    "809.4",
                    "-4.2%",
                    "483,084",
                    "12,070",
                    "8,500",
                    "Sahara Blend Export Crude",
                    "309,500",
                    "24.5",
                ):
                    assert fake not in full_text, f"Fabricated value '{fake}' appeared in {lang} PDF"

                if lang == "en":
                    assert "NO RECORDS / NOT APPLICABLE IN SCOPE" in full_text
                    assert "NO BASE-YEAR RECALCULATIONS LOGGED" in full_text
                    assert "METHODOLOGY NOTICE" in full_text  # stored pollutant values only (F-RPT-07)
                    assert "Not Verified — Stack Data Required" in full_text
                    assert "DB facility topology notes" in full_text
                    assert "no multi-year trend inferred for a single period" in full_text
                    assert "Method 21 LDAR & VISR" not in full_text
                else:
                    assert "AUCUNE DONNÉE / NON APPLICABLE DANS CE PÉRIMÈTRE" in full_text
                    assert "AUCUN RECALCUL" in full_text
                    assert "AVIS MÉTHODOLOGIQUE" in full_text  # stored pollutant values only (F-RPT-07)
                    assert "Non vérifié — Mesures cheminée requises" in full_text
                    assert "DB facility topology notes" in full_text
                    assert "sans comparaison pluriannuelle" in full_text
                    assert "Method 21" not in full_text
    finally:
        _cleanup_isolated_tenant_fixture(info)


def test_forensic_governance_period_lock_reporting_metadata_and_toc_pages():
    info = _create_isolated_tenant_fixture()
    rm_id = None
    prev_rm = None
    def_fac_id = None
    def_prod_id = None
    def_em_id = None
    try:
        with app.app_context():
            # Seed a default-tenant ReportingMetadata row AND ensure default tenant has a Basin Alpha facility
            existing_rm = ReportingMetadata.query.filter_by(year=2024).first()
            if existing_rm:
                prev_rm = {
                    "id": existing_rm.id,
                    "assurance_level": existing_rm.assurance_level,
                    "assurance_provider": existing_rm.assurance_provider,
                }
                existing_rm.assurance_level = "Limited Assurance"
                existing_rm.assurance_provider = "Bureau Veritas Forensic"
            else:
                rm = ReportingMetadata(
                    year=2024,
                    assurance_level="Limited Assurance",
                    assurance_provider="Bureau Veritas Forensic",
                    is_tcfd_aligned=True,
                    has_reduction_target=True,
                    target_description="Forensic test target",
                )
                db.session.add(rm)
                db.session.flush()
                rm_id = rm.id

            if not Facility.query.filter_by(tenant_id="default", region="Basin Alpha").first():
                def_fac = Facility(
                    name=f"Default CPF {info['tag']}",
                    code=f"DEF-{info['tag']}",
                    region="Basin Alpha",
                    segment="Upstream",
                    country="Algeria",
                    tenant_id="default",
                )
                db.session.add(def_fac)
                db.session.flush()
                def_fac_id = def_fac.id
                def_prod = ProductionData(
                    facility_id=def_fac.id,
                    year=2024,
                    month=6,
                    oil_amount=500.0,
                    gas_amount=50.0,
                    gross_gas_mmsm3=50.0,
                    gas_without_injected_mmsm3=50.0,
                    total_production_mmboe=0.25,
                )
                def_em = Emission(
                    facility_id=def_fac.id,
                    equipment_id=f"EQ-DEF-{info['tag']}",
                    year=2024,
                    month=6,
                    process_type="stationary_combustion",
                    fuel_type="Natural Gas",
                    quantity=500.0,
                    unit="m3",
                    co2_emissions=95.0,
                    ch4_emissions=1.0,
                    n2o_emissions=0.01,
                    co2e_total=123.0,
                    status="Verified",
                    created_by=info["user_id"],
                    is_test=False,
                )
                db.session.add_all([def_prod, def_em])
                db.session.flush()
                def_prod_id = def_prod.id
                def_em_id = def_em.id

            db.session.commit()

            # 1. Unlocked non-default tenant -> no default ReportingMetadata leak, unlocked canvas/cover/signoff
            buf_open = generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2024,
                end_year=2024,
                language="en",
                tenant_id=info["tenant_id"],
            )
            pages_open = _extract_pages(buf_open.getvalue())
            full_open = " ".join(pages_open)

            # Check Unicode DejaVuSans/GHGSans embedding (ASCII/Unicode safe)
            raw_pdf = buf_open.getvalue()
            assert b"GHGSans" in raw_pdf or b"DejaVuSans" in raw_pdf

            assert "Limited Assurance" not in pages_open[0]
            assert "Bureau Veritas Forensic" not in pages_open[0]
            assert "Not Specified / Unverified" in pages_open[0]
            assert "PRELIMINARY / UNLOCKED" in pages_open[0]
            assert "[ PENDING SIGN-OFF ]" in full_open
            assert "13. INVENTORY DATA QUALITY AUDIT & FIELD IMPROVEMENT ROADMAP" in full_open
            assert "7. INVENTORY DATA QUALITY AUDIT" not in full_open
            assert "7. DYNAMIC INVENTORY DATA QUALITY AUDIT" not in full_open

            # Verify 2-pass TOC page numbers match actual pages!
            toc_idx = next(i for i, p in enumerate(pages_open) if "TABLE OF CONTENTS" in p)
            toc_text = pages_open[toc_idx]
            m_ch1 = re.search(r"Chapter 1\s+Hydrocarbon production.*?Page\s+(\d+)", toc_text)
            m_ch12 = re.search(r"Chapter 12\s+QA/QC protocols.*?Page\s+(\d+)", toc_text)
            m_ch13 = re.search(r"Chapter 13\s+Dynamic inventory data quality audit.*?Page\s+(\d+)", toc_text)
            m_sign = re.search(r"Assurance & Audit\s+MRV sign-off status.*?Page\s+(\d+)", toc_text)
            assert m_ch1 and m_ch12 and m_ch13 and m_sign, f"Missing expected TOC entries in: {toc_text}"
            assert "1. HYDROCARBON PRODUCTION & ENERGY DELIVERABILITY" in pages_open[int(m_ch1.group(1)) - 1]
            assert "12. QA/QC VERIFICATION" in pages_open[int(m_ch12.group(1)) - 1]
            assert "13. INVENTORY DATA QUALITY AUDIT & FIELD IMPROVEMENT ROADMAP" in pages_open[int(m_ch13.group(1)) - 1]
            assert "EXECUTIVE MRV SIGN-OFF" in pages_open[int(m_sign.group(1)) - 1]

            # Verify default tenant DOES display ReportingMetadata on Cover & QA/QC
            buf_def = generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2024,
                end_year=2024,
                language="en",
                tenant_id="default",
            )
            pages_def = _extract_pages(buf_def.getvalue())
            assert "Limited Assurance" in pages_def[0]
            assert "Bureau Veritas Forensic" in pages_def[0]

            # 2. Locked state -> LOCKED & SEALED headers & [ DIGITALLY SIGNED ] stamp
            lock_row = PeriodLock(
                year=2024,
                month=None,
                status="locked",
                locked_by=info["user_id"],
                signoff_signatory="Chief MRV Officer",
                signoff_notes="Annual statutory close complete",
                tenant_id=info["tenant_id"],
            )
            db.session.add(lock_row)
            db.session.commit()

            buf_locked = generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2024,
                end_year=2024,
                language="en",
                tenant_id=info["tenant_id"],
            )
            pages_locked = _extract_pages(buf_locked.getvalue())
            full_locked = " ".join(pages_locked)
            assert "LOCKED & SEALED" in pages_locked[0]
            assert "LOCKED & SEALED // ISO 14064-1" in pages_locked[1]
            assert "PRELIMINARY / UNLOCKED" not in pages_locked[0]
            assert "PRELIMINARY / UNLOCKED" not in pages_locked[1]
            assert "[ DIGITALLY SIGNED ]" in full_locked
            assert "Chief MRV Officer" in full_locked
            assert "Annual statutory close complete" in full_locked
    finally:
        with app.app_context():
            db.session.rollback()
            if prev_rm:
                ex = db.session.get(ReportingMetadata, prev_rm["id"])
                if ex:
                    ex.assurance_level = prev_rm["assurance_level"]
                    ex.assurance_provider = prev_rm["assurance_provider"]
            if rm_id:
                ReportingMetadata.query.filter_by(id=rm_id).delete(synchronize_session=False)
            if def_em_id:
                Emission.query.filter_by(id=def_em_id).delete(synchronize_session=False)
            if def_prod_id:
                ProductionData.query.filter_by(id=def_prod_id).delete(synchronize_session=False)
            if def_fac_id:
                Facility.query.filter_by(id=def_fac_id).delete(synchronize_session=False)
            db.session.commit()
        _cleanup_isolated_tenant_fixture(info)


def test_forensic_verified_filtering_methane_net_gas_and_appendix_b():
    def _extra_ems(fac, user, tag):
        return [
            Emission(
                facility_id=fac.id,
                equipment_id=f"EQ-P-{tag}",
                year=2024,
                month=6,
                process_type="stationary_combustion",
                fuel_type="Natural Gas",
                quantity=5000.0,
                unit="m3",
                co2_emissions=5000.0,
                ch4_emissions=0.0,
                n2o_emissions=0.0,
                co2e_total=5000.0,
                status="Pending",
                created_by=user.id,
                is_test=False,
            ),
            Emission(
                facility_id=fac.id,
                equipment_id=f"EQ-R-{tag}",
                year=2024,
                month=6,
                process_type="stationary_combustion",
                fuel_type="Natural Gas",
                quantity=3000.0,
                unit="m3",
                co2_emissions=3000.0,
                ch4_emissions=0.0,
                n2o_emissions=0.0,
                co2e_total=3000.0,
                status="Rejected",
                created_by=user.id,
                is_test=False,
            ),
            Emission(
                facility_id=fac.id,
                equipment_id=f"EQ-T-{tag}",
                year=2024,
                month=6,
                process_type="stationary_combustion",
                fuel_type="Natural Gas",
                quantity=9000.0,
                unit="m3",
                co2_emissions=9000.0,
                ch4_emissions=0.0,
                n2o_emissions=0.0,
                co2e_total=9000.0,
                status="Verified",
                created_by=user.id,
                is_test=True,
            ),
        ]

    info = _create_isolated_tenant_fixture(with_gc=True, extra_emissions=_extra_ems)
    try:
        with app.app_context():
            # Add Corporate SbtiTarget + Recalc with approved_by=None for boundary & approver checks
            sbti = SbtiTarget(
                base_year=2021,
                base_year_emissions=50000.0,
                target_year=2030,
                reduction_rate_pct=4.2,
                pathway_type="1.5C",
                scope_coverage="S1S2",
                tenant_id=info["tenant_id"],
            )
            recalc = BaseYearRecalculation(
                year=2021,
                reason=f"Pending approval check {info['tag']}",
                previous_emissions=10000.0,
                adjusted_emissions=10500.0,
                approved_by=None,
                tenant_id=info["tenant_id"],
            )
            db.session.add_all([sbti, recalc])
            db.session.commit()

            data = aggregate_master_report_data(
                "regional", "basin_alpha", 2024, 2024, "AR5", tenant_id=info["tenant_id"]
            )
            # Only the 200 tCO2e Verified non-test record counts; 3 unverified/test excluded
            assert data["timeline"][0]["scope1_co2e_t"] == pytest.approx(200.0)
            assert data["excluded_unverified"]["total_excluded"] == 3

            # Methane intensity must use net_gas_mmsm3 (60.0 MMSm3) + GC gas density (~0.74 kg/m3 vs generic 0.717)
            assert data["timeline"][0]["gross_gas_mmsm3"] == pytest.approx(100.0)
            assert data["timeline"][0]["net_gas_mmsm3"] == pytest.approx(60.0)
            # Expected CH4 mole/mass pct uses 80 t / (60e6 m3 * density) * 100 > using 100e6 m3!
            mi = data["timeline"][0]["methane_intensity_pct"]
            # With gross gas 100e6 * 0.717 = 71,700t -> 80/71700*100 = 0.1116%; with net gas 60e6 -> ~0.18%
            assert mi > 0.15, f"Expected methane intensity calculated against net_gas_mmsm3, got {mi}"

            # Appendix B YTD must equal Ch. 2 annual total (200 tCO2e) with no 12x duplication
            fname = data["facilities"][0]["name"]
            sub_fac = data["subannual_time_series"][fname]
            assert sub_fac["has_monthly_data"] is False
            assert sub_fac["ytd_totals"]["co2e"] == pytest.approx(200.0)

            buf = generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2024,
                end_year=2024,
                language="en",
                tenant_id=info["tenant_id"],
            )
            pages = _extract_pages(buf.getvalue())
            full_text = " ".join(pages)
            assert "[Corporate Group Boundary]" in full_text
            assert "Pending Approval" in full_text
            assert "QUARTERLY EMISSION REPORTING ONLY" in full_text
            assert "3 unverified" in full_text.lower() or "unverified/pending/test row(s)" in full_text.lower()
    finally:
        _cleanup_isolated_tenant_fixture(info)


def test_forensic_http_job_dataset_and_report_sha256_headers():
    info = _create_isolated_tenant_fixture()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    limiter.enabled = False
    try:
        with app.test_client() as client:
            with client.session_transaction() as sess:
                sess["user_id"] = info["user_id"]
                sess["role"] = "admin"
                sess["email"] = f"forensic_{info['tag']}@example.org"
                sess["orgName"] = f"Forensic Co {info['tag']}"
                sess["tenant_id"] = info["tenant_id"]

            post = client.post(
                "/api/reports/master-report",
                json={
                    "mode": "regional",
                    "region": "basin_alpha",
                    "start_year": 2024,
                    "end_year": 2024,
                    "gwp_standard": "AR5",
                    "language": "en",
                },
            )
            assert post.status_code == 202
            job = post.get_json()
            deadline = time.perf_counter() + 30.0
            state = None
            while time.perf_counter() < deadline:
                st = client.get(job["status_url"])
                assert st.status_code == 200
                state = st.get_json()
                if state["status"] == "completed":
                    break
                assert state["status"] != "failed", state
                time.sleep(0.1)
            assert state and state["status"] == "completed"
            assert len(state["sha256"]) == 64
            assert len(state["dataset_sha256"]) == 64

            dl = client.get(state["download_url"])
            assert dl.status_code == 200
            assert dl.headers["X-Report-SHA256"] == hashlib.sha256(dl.data).hexdigest()
            assert dl.headers["X-Report-SHA256"] == state["sha256"]
            assert dl.headers["X-Dataset-SHA256"] == state["dataset_sha256"]

            pages = _extract_pages(dl.data)
            full_text = " ".join(pages)
            assert state["dataset_sha256"] in full_text
    finally:
        _cleanup_isolated_tenant_fixture(info)


def test_phase2_french_localization_census_ch9_ch13_and_appendix_b():
    info = _create_isolated_tenant_fixture(with_gc=True)
    try:
        with app.app_context():
            fac_id = info["fac_id"]
            uid = info["user_id"]
            tag = info["tag"]

            # Adjust month-6 ProductionData & Emission + add months 1..5 so:
            # - has_monthly_data is True (>= 6 distinct months) -> renders French monthly section
            # - Total CO2e = 550.0 t & Total BOE = 10,000 -> Appendix B intensity = 0.055 (3 decimals!)
            base_prod = ProductionData.query.filter_by(facility_id=fac_id, month=6).first()
            base_prod.oil_amount = 0.0
            base_prod.gas_amount = 0.0
            base_prod.total_production_mmboe = 0.004
            for m in range(1, 6):
                db.session.add(
                    ProductionData(
                        facility_id=fac_id,
                        year=2024,
                        month=m,
                        oil_amount=0.0,
                        gas_amount=0.0,
                        gross_gas_mmsm3=10.0,
                        injected_gas_mmsm3=4.0,
                        gas_without_injected_mmsm3=6.0,
                        crude_oil_mmboe=0.0,
                        total_production_mmboe=0.0012,
                    )
                )
                db.session.add(
                    Emission(
                        facility_id=fac_id,
                        equipment_id=f"EQ-F1-{tag}",
                        year=2024,
                        month=m,
                        process_type="stationary_combustion",
                        fuel_type="Natural Gas",
                        quantity=100.0,
                        unit="m3",
                        co2_emissions=66.0,
                        ch4_emissions=4.0,
                        n2o_emissions=0.01,
                        co2e_total=70.0,
                        status="Verified",
                        created_by=uid,
                        is_test=False,
                    )
                )

            # ComponentInventory on facility so Census populates CPF Gas processing while Oil/Gas production stay 0
            db.session.add(
                ComponentInventory(
                    facility_id=fac_id,
                    equipment_type="Valves",
                    component_type="Gate",
                    service_type="Gas",
                    quantity=25,
                    methodology="Component Average",
                )
            )
            # Active MACC / MitigationProject to verify French project type & MACC rendering
            db.session.add(
                MitigationProject(
                    facility_id=fac_id,
                    year=2024,
                    name=f"LDAR Valve Upgrade {tag}",
                    project_type="METHANE_ABATEMENT",
                    quantity_tco2e=1200.0,
                    investment_amount=60000.0,
                    status="Active",
                    is_test=False,
                )
            )
            # Unapproved BaseYearRecalculation for long reason & approver wrapping check
            db.session.add(
                BaseYearRecalculation(
                    year=2021,
                    reason=f"Boundary alignment structural change {tag}",
                    previous_emissions=1000.0,
                    adjusted_emissions=1050.0,
                    approved_by=None,
                    tenant_id=info["tenant_id"],
                )
            )
            db.session.commit()

            # Check EN executive narrative humanized mi_basis + non-repeating zero leak note
            buf_en = generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2024,
                end_year=2024,
                language="en",
                tenant_id=info["tenant_id"],
            )
            full_en = " ".join(_extract_pages(buf_en.getvalue()))
            # the methane intensity is on marketed gas, OGCI / OGMP basis (BA-054)
            assert "basis: marketed gas (OGCI / OGMP)" in full_en
            assert "basis: marketed_gas" not in full_en
            assert "No production leak sources logged in this sub-category" in full_en

            # Check FR PDF end-to-end localizations
            buf_fr = generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2024,
                end_year=2024,
                language="fr",
                tenant_id=info["tenant_id"],
            )
            full_fr = " ".join(_extract_pages(buf_fr.getvalue()))

            # Executive Narrative #2 humanized French mi_basis
            assert "gaz commercialisé (OGCI / OGMP)" in full_fr
            assert "marketed_gas" not in full_fr

            # Equipment Census FR localization + non-repeating zero-count leak notes
            assert "Combustion – Turbines / Générateurs" in full_fr
            assert "Fuites d'équipements – Production gaz" in full_fr
            assert "Aucune source de fuite production enregistrée dans cette sous-catégorie" in full_fr

            # Ch. 5 & Ch. 7 & Ch. 10 FR empty perimeter_notes (note: MACC exists on Ch. 10, CBAM is empty)
            assert "Aucune campagne de mesure OGMP 2.0 Niveau 4/5 n'est enregistrée" in full_fr
            assert "Aucune émission Scope 3 vérifiée n'est enregistrée" in full_fr
            assert "Aucune exportation de produit soumise au MACF UE n'est enregistrée" in full_fr
            # Ch. 10 MACC localized project type (normalized underscores/case)
            assert "Atténuation CH4" in full_fr

            # Ch. 9 glidepath French milestone strings
            assert "Point de Référence" in full_fr
            assert "GES vs Référence" in full_fr
            assert "Torchage Opérationnel Actuel" in full_fr

            # Ch. 13 French dynamic audit headings, observations, recommendations, priorities
            assert "Fréquence d'Échantillonnage et d'Analyse des Combustibles" in full_fr
            assert "Mesure de l'Efficacité de Destruction en Torche (DRE)" in full_fr
            assert "Élevée" in full_fr
            assert "Fuel Property Sampling & Testing Frequency" not in full_fr

            # Appendix B: fixed spelling ("ventilations"), French headers & months, 3-decimal intensity 0.055
            assert "ventiliations" not in full_fr.lower()
            assert "ventilations mensuelles" in full_fr
            assert "Intensité Carbone (CO2e/BEP)" in full_fr
            assert "0.055" in full_fr
            assert "Fév" in full_fr and "Juil" in full_fr and "Déc" in full_fr
    finally:
        with app.app_context():
            db.session.rollback()
            ComponentInventory.query.filter_by(facility_id=info["fac_id"]).delete(synchronize_session=False)
            MitigationProject.query.filter_by(facility_id=info["fac_id"]).delete(synchronize_session=False)
            CbamProductExport.query.filter_by(facility_id=info["fac_id"]).delete(synchronize_session=False)
            Scope3Emission.query.filter_by(facility_id=info["fac_id"]).delete(synchronize_session=False)
            OgmpSurvey.query.filter_by(facility_id=info["fac_id"]).delete(synchronize_session=False)
            db.session.commit()
        _cleanup_isolated_tenant_fixture(info)


def test_phase2_assurance_provider_no_double_parens_and_populated_s3_ogmp_fr():
    info = _create_isolated_tenant_fixture(with_gc=True)
    rm_id = None
    prev_rm = None
    def_fac_id = None
    def_prod_id = None
    def_em_id = None
    try:
        with app.app_context():
            fac_id = info["fac_id"]
            # Populate OGMP, Scope 3 (long factor_unit), CBAM export on isolated tenant to verify table cells & alignment in FR
            db.session.add(
                OgmpSurvey(
                    facility_id=fac_id,
                    year=2024,
                    survey_date="2024-06-15",
                    survey_type="Optical Gas Imaging Survey (O&M Tier 4)",
                    instrument_vendor="FLIR GF320 Optical Camera",
                    measured_rate_kg_hr=2.5,
                    estimated_annual_tch4=21.9,
                    bottom_up_tch4=20.0,
                    variance_pct=9.5,
                    reconciliation_status="Reconciled",
                    status="Verified",
                )
            )
            db.session.add(
                Scope3Emission(
                    facility_id=fac_id,
                    year=2024,
                    month=6,
                    category="Category 1: Purchased Goods & Services",
                    sub_category="Chemicals & Catalysts",
                    activity_data=1500.0,
                    unit="tonnes",
                    factor_unit="kg CO2e/tonne.km",
                    emission_factor=1.25,
                    co2e=1875.0,
                    calculation_method="Supplier Primary (Tier 2)",
                    data_quality="high",
                    status="Verified",
                )
            )
            db.session.add(
                CbamProductExport(
                    facility_id=fac_id,
                    year=2024,
                    month=6,
                    product_name="Refined Condensate Blend Export Stream",
                    cn_code="2709 00",
                    export_destination="Rotterdam (EU)",
                    quantity_tonnes=50000.0,
                    specific_embedded_direct=0.142,
                    specific_embedded_indirect=0.012,
                )
            )

            existing_rm = ReportingMetadata.query.filter_by(year=2024).first()
            if existing_rm:
                prev_rm = {
                    "id": existing_rm.id,
                    "assurance_level": existing_rm.assurance_level,
                    "assurance_provider": existing_rm.assurance_provider,
                }
                existing_rm.assurance_level = "Self-Assessed / Unverified"
                existing_rm.assurance_provider = "Internal MRV Team (No Third-Party Verifier Engaged)"
            else:
                rm = ReportingMetadata(
                    year=2024,
                    assurance_level="Self-Assessed / Unverified",
                    assurance_provider="Internal MRV Team (No Third-Party Verifier Engaged)",
                    is_tcfd_aligned=True,
                    has_reduction_target=True,
                )
                db.session.add(rm)
                db.session.flush()
                rm_id = rm.id

            if not Facility.query.filter_by(tenant_id="default", region="Basin Alpha").first():
                def_fac = Facility(
                    name=f"Default CPF P2 {info['tag']}",
                    code=f"DEFP2-{info['tag']}",
                    region="Basin Alpha",
                    segment="Upstream",
                    country="Algeria",
                    tenant_id="default",
                )
                db.session.add(def_fac)
                db.session.flush()
                def_fac_id = def_fac.id
                def_prod = ProductionData(
                    facility_id=def_fac.id,
                    year=2024,
                    month=6,
                    oil_amount=500.0,
                    gas_amount=50.0,
                    gross_gas_mmsm3=50.0,
                    gas_without_injected_mmsm3=50.0,
                    total_production_mmboe=0.25,
                )
                def_em = Emission(
                    facility_id=def_fac.id,
                    equipment_id=f"EQ-DEFP2-{info['tag']}",
                    year=2024,
                    month=6,
                    process_type="stationary_combustion",
                    fuel_type="Natural Gas",
                    quantity=500.0,
                    unit="m3",
                    co2_emissions=95.0,
                    ch4_emissions=1.0,
                    n2o_emissions=0.01,
                    co2e_total=123.0,
                    status="Verified",
                    created_by=info["user_id"],
                    is_test=False,
                )
                db.session.add_all([def_prod, def_em])
                db.session.flush()
                def_prod_id = def_prod.id
                def_em_id = def_em.id

            db.session.commit()

            # Default tenant FR + EN: assurance_provider already has parens -> must use em-dash and NEVER '((' or '))'
            for lang in ("en", "fr"):
                buf_def = generate_master_publication_pdf(
                    mode="regional",
                    region_key="basin_alpha",
                    start_year=2024,
                    end_year=2024,
                    language=lang,
                    tenant_id="default",
                )
                full_def = " ".join(_extract_pages(buf_def.getvalue()))
                assert "((" not in full_def
                assert "))" not in full_def
                assert "Self-Assessed / Unverified — Internal MRV Team (No Third-Party Verifier Engaged)" in full_def

            # Isolated tenant populated FR: verify non-empty perimeter notes & full strings preserved (no awkward mid-word 20-char chop)
            buf_pop = generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2024,
                end_year=2024,
                language="fr",
                tenant_id=info["tenant_id"],
            )
            full_pop = " ".join(_extract_pages(buf_pop.getvalue()))
            assert "FLIR GF320 Optical Camera" in full_pop
            assert "kg CO2e/tonne.km" in full_pop
            assert "Refined Condensate Blend Export Stream" in full_pop
            assert "Réconciliation OGMP 2.0 Niveaux 4/5 et registre des composants LDAR" in full_pop
            assert "Émissions Scope 3 de la chaîne de valeur comptabilisées" in full_pop
            assert "Registre d'exportation MACF UE" in full_pop
    finally:
        with app.app_context():
            db.session.rollback()
            OgmpSurvey.query.filter_by(facility_id=info["fac_id"]).delete(synchronize_session=False)
            Scope3Emission.query.filter_by(facility_id=info["fac_id"]).delete(synchronize_session=False)
            CbamProductExport.query.filter_by(facility_id=info["fac_id"]).delete(synchronize_session=False)
            if prev_rm:
                ex = db.session.get(ReportingMetadata, prev_rm["id"])
                if ex:
                    ex.assurance_level = prev_rm["assurance_level"]
                    ex.assurance_provider = prev_rm["assurance_provider"]
            if rm_id:
                ReportingMetadata.query.filter_by(id=rm_id).delete(synchronize_session=False)
            if def_em_id:
                Emission.query.filter_by(id=def_em_id).delete(synchronize_session=False)
            if def_prod_id:
                ProductionData.query.filter_by(id=def_prod_id).delete(synchronize_session=False)
            if def_fac_id:
                Facility.query.filter_by(id=def_fac_id).delete(synchronize_session=False)
            db.session.commit()
        _cleanup_isolated_tenant_fixture(info)


def _poll_job_until_terminal(client, status_url: str, timeout_s: float = 30.0) -> dict:
    deadline = time.perf_counter() + timeout_s
    while time.perf_counter() < deadline:
        resp = client.get(status_url)
        assert resp.status_code == 200
        state = resp.get_json()
        if state["status"] in ("completed", "failed"):
            return state
        time.sleep(0.05)
    raise AssertionError(f"Master Report job did not finish within {timeout_s}s: {status_url}")


def _authenticate_test_client(client, info: dict) -> None:
    with client.session_transaction() as sess:
        sess["user_id"] = info["user_id"]
        sess["role"] = "admin"
        sess["email"] = f"forensic_{info['tag']}@example.org"
        sess["orgName"] = f"Forensic Co {info['tag']}"
        sess["tenant_id"] = info["tenant_id"]


def test_forensic_jv_and_single_partner_trailing_empty_year_alignment():
    info = _create_isolated_tenant_fixture()
    try:
        with app.app_context():
            # Fixture only has 2024 data; 2025 & 2026 are trailing empty years
            single_data = aggregate_master_report_data(
                "regional", "basin_alpha", 2023, 2026, "AR5", tenant_id=info["tenant_id"]
            )
            jv_single = single_data["jv_equity"]
            assert jv_single["is_jv"] is False
            assert jv_single["partners"][0]["latest_year"] == 2024
            assert jv_single["partners"][0]["latest_year_co2e"] == pytest.approx(200.0)

            buf = generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2023,
                end_year=2026,
                language="en",
                tenant_id=info["tenant_id"],
            )
            full_text = " ".join(_extract_pages(buf.getvalue()))
            assert "2024 Equity GHG (tCO2e)" in full_text
            assert "2026 Equity GHG (tCO2e)" not in full_text

            # Now attach two JV partners (60% / 40%) and confirm alignment for multi-partner mode too
            p_op = JvPartner(
                name=f"JV Op {info['tag']}",
                code=f"JVO_{info['tag']}",
                is_operator=True,
                tenant_id=info["tenant_id"],
            )
            p_non = JvPartner(
                name=f"JV Partner {info['tag']}",
                code=f"JVP_{info['tag']}",
                is_operator=False,
                tenant_id=info["tenant_id"],
            )
            db.session.add_all([p_op, p_non])
            db.session.flush()
            db.session.add_all([
                FacilityEquityShare(
                    facility_id=info["fac_id"],
                    partner_id=p_op.id,
                    equity_share_pct=60.0,
                    effective_start_date="2020-01-01",
                ),
                FacilityEquityShare(
                    facility_id=info["fac_id"],
                    partner_id=p_non.id,
                    equity_share_pct=40.0,
                    effective_start_date="2020-01-01",
                ),
            ])
            db.session.commit()

            multi_data = aggregate_master_report_data(
                "regional", "basin_alpha", 2023, 2026, "AR5", tenant_id=info["tenant_id"]
            )
            jv_multi = multi_data["jv_equity"]
            assert jv_multi["is_jv"] is True
            assert len(jv_multi["partners"]) == 2
            assert all(p["latest_year"] == 2024 for p in jv_multi["partners"])
            assert sum(p["latest_year_co2e"] for p in jv_multi["partners"]) == pytest.approx(200.0, rel=1e-3)
    finally:
        _cleanup_isolated_tenant_fixture(info)


def test_forensic_multifacility_equipment_census_chunked_rendering():
    info = _create_isolated_tenant_fixture()
    extra_names = [
        f"Alpha Train Two {info['tag']}",
        f"Beta Comp Hub {info['tag']}",
        f"Gamma Dehyd Unit {info['tag']}",
        f"Delta Flare Hdr {info['tag']}",
    ]
    try:
        with app.app_context():
            for idx, fname in enumerate(extra_names, start=2):
                f = Facility(
                    name=fname,
                    code=f"FOR{idx}-{info['tag']}",
                    region="Basin Alpha",
                    segment="Upstream",
                    country="Algeria",
                    tenant_id=info["tenant_id"],
                )
                db.session.add(f)
                db.session.flush()
                db.session.add_all([
                    EmissionSource(
                        facility_id=f.id,
                        name=f"Source {idx} {info['tag']}",
                        code=f"SRC{idx}-{info['tag']}",
                        equipment_id=f"EQ{idx}-{info['tag']}",
                        type="flaring" if idx % 2 == 0 else "stationary_combustion",
                        status="Active",
                    ),
                    Emission(
                        facility_id=f.id,
                        equipment_id=f"EQ{idx}-{info['tag']}",
                        year=2024,
                        month=6,
                        process_type="flaring" if idx % 2 == 0 else "stationary_combustion",
                        fuel_type="Natural Gas",
                        quantity=100.0,
                        unit="m3",
                        co2_emissions=50.0,
                        ch4_emissions=1.0,
                        n2o_emissions=0.01,
                        co2e_total=75.0,
                        status="Verified",
                        created_by=info["user_id"],
                        is_test=False,
                    ),
                    ProductionData(
                        facility_id=f.id,
                        year=2024,
                        month=6,
                        oil_amount=100.0,
                        gas_amount=10.0,
                        gross_gas_mmsm3=10.0,
                        gas_without_injected_mmsm3=8.0,
                        total_production_mmboe=0.05,
                    ),
                ])
            db.session.commit()

            data = aggregate_master_report_data(
                "regional", "basin_alpha", 2024, 2024, "AR5", tenant_id=info["tenant_id"]
            )
            assert len(data["facilities"]) == 5

            # Check 3-facility dynamic single table fit
            styles = _build_styles()
            three_fac_data = dict(data, facilities=data["facilities"][:3])
            elems_3 = build_equipment_census_elements(three_fac_data, styles, lang="en")
            tables_3 = [el for el in elems_3 if hasattr(el, "_argW")]
            assert len(tables_3) == 1
            assert sum(tables_3[0]._argW) == pytest.approx(520.0)

            # Check full 5-facility PDF splits into two 4-fac sub-tables and keeps all 5 facilities
            buf = generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2024,
                end_year=2024,
                language="en",
                tenant_id=info["tenant_id"],
            )
            full_text = " ".join(_extract_pages(buf.getvalue()))
            assert "Facility Group 1/2" in full_text
            assert "Facility Group 2/2" in full_text
            for fac in data["facilities"]:
                assert fac["name"][:15] in full_text
    finally:
        _cleanup_isolated_tenant_fixture(info)


def test_forensic_multiworker_disk_job_persistence_and_invalid_job_id():
    info = _create_isolated_tenant_fixture()
    other_tag = uuid.uuid4().hex[:8]
    other_uid = None
    created_artifacts: list[Path] = []
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    limiter.enabled = False
    try:
        with app.app_context():
            other_user = User(
                email=f"other_{other_tag}@example.org",
                fullName=f"Other Admin {other_tag}",
                orgName=f"Other Co {other_tag}",
                sector="Oil & Gas",
                role="admin",
                status="active",
                tenant_id=f"other_{other_tag}",
            )
            other_user.set_password("OtherTest!123")
            db.session.add(other_user)
            db.session.commit()
            other_uid = other_user.id

        with app.test_client() as client:
            _authenticate_test_client(client, info)
            post = client.post(
                "/api/reports/master-report",
                json={"mode": "regional", "region": "basin_alpha", "start_year": 2024, "end_year": 2024},
            )
            assert post.status_code == 202
            job_id = post.get_json()["job_id"]
            state = _poll_job_until_terminal(client, post.get_json()["status_url"])
            assert state["status"] == "completed"

            meta_path = _job_meta_path(job_id)
            assert meta_path is not None and meta_path.exists()
            with _MASTER_JOBS_LOCK:
                if job_id in _MASTER_JOBS and _MASTER_JOBS[job_id].get("file_path"):
                    created_artifacts.append(Path(_MASTER_JOBS[job_id]["file_path"]))
            created_artifacts.append(meta_path)

            # Simulate fresh Gunicorn worker with empty RAM job dict
            with _MASTER_JOBS_LOCK:
                _MASTER_JOBS.clear()

            st_disk = client.get(f"/api/reports/master-report/jobs/{job_id}")
            assert st_disk.status_code == 200
            disk_json = st_disk.get_json()
            assert disk_json["status"] == "completed"
            assert disk_json["sha256"] == state["sha256"]

            with _MASTER_JOBS_LOCK:
                _MASTER_JOBS.clear()
            dl_disk = client.get(f"/api/reports/master-report/jobs/{job_id}/download")
            assert dl_disk.status_code == 200
            assert dl_disk.headers["X-Report-SHA256"] == state["sha256"]
            assert dl_disk.headers["X-Dataset-SHA256"] == state["dataset_sha256"]

            # Malformed job_ids rejected cleanly
            assert client.get("/api/reports/master-report/jobs/..bad_id").status_code == 404
            assert client.get("/api/reports/master-report/jobs/bad..id/download").status_code == 404

        with app.test_client() as other_client:
            with other_client.session_transaction() as sess:
                sess["user_id"] = other_uid
                sess["role"] = "admin"
                sess["email"] = f"other_{other_tag}@example.org"
                sess["tenant_id"] = f"other_{other_tag}"
            assert other_client.get(f"/api/reports/master-report/jobs/{job_id}").status_code == 403
            assert other_client.get(f"/api/reports/master-report/jobs/{job_id}/download").status_code == 403
    finally:
        for art in created_artifacts:
            _remove_artifact_path(art)
        if other_uid is not None:
            with app.app_context():
                User.query.filter_by(id=other_uid).delete(synchronize_session=False)
                db.session.commit()
        _cleanup_isolated_tenant_fixture(info)


def test_forensic_http_400_validation_benchmark_sanitized_failure_and_filename(monkeypatch):
    assert _sanitize_filename_part("Demo Operator Co.") == "Demo Operator Co."
    assert "/" not in _sanitize_filename_part("../../etc/passwd")
    assert ".." not in _sanitize_filename_part("../../etc/passwd")

    info = _create_isolated_tenant_fixture()
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    limiter.enabled = False
    try:
        with app.test_client() as client:
            _authenticate_test_client(client, info)

            r_bad_json = client.post(
                "/api/reports/master-report",
                data="{not-json",
                content_type="application/json",
            )
            assert r_bad_json.status_code == 400
            assert r_bad_json.get_json()["field"] == "payload"

            assert client.post("/api/reports/master-report", json=["array"]).status_code == 400
            invalid_cases = [
                ({"start_year": True}, "start_year"),
                ({"start_year": 1850}, "start_year"),
                ({"end_year": 2200}, "end_year"),
                ({"start_year": 2025, "end_year": 2023}, "start_year"),
                ({"start_year": 1990, "end_year": 2025}, "end_year"),
                ({"mode": "invalid_mode"}, "mode"),
                ({"gwp_standard": "20yr"}, "gwp_standard"),
                ({"language": "es"}, "language"),
                ({"region": 123}, "region"),
            ]
            for payload, expected_field in invalid_cases:
                resp = client.post("/api/reports/master-report", json=payload)
                assert resp.status_code == 400, f"Expected 400 for {payload}, got {resp.status_code}"
                body = resp.get_json()
                assert body.get("error") and body.get("field") == expected_field

            assert client.post("/api/reports/master-report/benchmark-excel", json=["not_an_object"]).status_code == 400
            for payload, expected_field in (
                ({"start_year": 2025, "end_year": 2023}, "start_year"),
                ({"gwp_standard": "20yr"}, "gwp_standard"),
                ({"start_year": False}, "start_year"),
            ):
                bresp = client.post("/api/reports/master-report/benchmark-excel", json=payload)
                assert bresp.status_code == 400
                assert bresp.get_json().get("field") == expected_field

            # Omitted defaults must still enqueue cleanly
            ok_nat = client.post("/api/reports/master-report", json={"mode": "national"})
            assert ok_nat.status_code == 202
            nat_state = _poll_job_until_terminal(client, ok_nat.get_json()["status_url"])
            assert nat_state["status"] == "completed"

            # Sanitized failure state (no internal trace/db path leaked)
            def _boom(*_args, **_kwargs):
                raise RuntimeError(r"sqlite3 OperationalError C:\internal\secret.db")

            monkeypatch.setattr(reports_master_route, "generate_master_publication_pdf", _boom)
            post_fail = client.post(
                "/api/reports/master-report",
                json={"mode": "regional", "region": "basin_alpha", "start_year": 2024, "end_year": 2024},
            )
            assert post_fail.status_code == 202
            fail_id = post_fail.get_json()["job_id"]
            fail_state = _poll_job_until_terminal(client, post_fail.get_json()["status_url"])
            assert fail_state["status"] == "failed"
            assert f"(ref: {fail_id[:8]})" in fail_state["error"]
            assert "sqlite3" not in fail_state["error"]
            assert "secret.db" not in fail_state["error"]

            fail_dl = client.get(f"/api/reports/master-report/jobs/{fail_id}/download")
            assert fail_dl.status_code == 500
            assert "sqlite3" not in fail_dl.get_json()["error"]
    finally:
        _cleanup_isolated_tenant_fixture(info)


def test_forensic_per_facility_pfd_module_isolation(monkeypatch):
    info = _create_isolated_tenant_fixture()
    try:
        with app.app_context():
            fac2 = Facility(
                name=f"Forensic FlareFac {info['tag']}",
                code=f"FF2-{info['tag']}",
                region="Basin Alpha",
                segment="Upstream",
                country="Algeria",
                tenant_id=info["tenant_id"],
            )
            db.session.add(fac2)
            db.session.flush()
            db.session.add_all([
                Emission(
                    facility_id=fac2.id,
                    equipment_id=f"EQ-FL2-{info['tag']}",
                    year=2024,
                    month=6,
                    process_type="flaring",
                    fuel_type="Associated Gas",
                    quantity=100.0,
                    unit="m3",
                    co2_emissions=50.0,
                    ch4_emissions=1.0,
                    n2o_emissions=0.01,
                    co2e_total=75.0,
                    status="Verified",
                    created_by=info["user_id"],
                    is_test=False,
                ),
                ProductionData(
                    facility_id=fac2.id,
                    year=2024,
                    month=6,
                    oil_amount=200.0,
                    gas_amount=20.0,
                    gross_gas_mmsm3=20.0,
                    gas_without_injected_mmsm3=15.0,
                    total_production_mmboe=0.1,
                ),
            ])
            db.session.commit()

            data = aggregate_master_report_data(
                "regional", "basin_alpha", 2024, 2024, "AR5", tenant_id=info["tenant_id"]
            )
            fac1_name = f"Forensic CPF {info['tag']}"
            by_fac = data["active_modules_by_facility"]
            assert by_fac[fac1_name] == ["combustion"]
            assert by_fac[fac2.name] == ["flare"]

            captured: dict[str, list[str] | None] = {}
            orig_fn = master_report_engine.generate_process_overview_diagram

            def _spy_pfd(facility_name, out_path, language="en", dpi=150, use_cache=True, active_modules=None):
                captured[facility_name] = list(active_modules) if active_modules is not None else None
                return orig_fn(
                    facility_name,
                    out_path,
                    language=language,
                    dpi=dpi,
                    use_cache=use_cache,
                    active_modules=active_modules,
                )

            monkeypatch.setattr(master_report_engine, "generate_process_overview_diagram", _spy_pfd)
            generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2024,
                end_year=2024,
                language="en",
                tenant_id=info["tenant_id"],
            )
            assert captured[fac1_name] == ["combustion"]
            assert captured[fac2.name] == ["flare"]
    finally:
        _cleanup_isolated_tenant_fixture(info)


def test_forensic_ch13_mitigation_project_year_window_filter():
    info = _create_isolated_tenant_fixture()
    try:
        with app.app_context():
            db.session.add_all([
                MitigationProject(
                    facility_id=info["fac_id"],
                    year=2021,
                    name=f"Old Project 2021 {info['tag']}",
                    project_type="EFFICIENCY",
                    quantity_tco2e=500.0,
                    status="Active",
                    is_test=False,
                ),
                MitigationProject(
                    facility_id=info["fac_id"],
                    year=2024,
                    name=f"Active Project 2024 {info['tag']}",
                    project_type="EFFICIENCY",
                    quantity_tco2e=600.0,
                    status="Active",
                    is_test=False,
                ),
                MitigationProject(
                    facility_id=info["fac_id"],
                    year=None,
                    name=f"Ongoing Timeless Project {info['tag']}",
                    project_type="METHANE_ABATEMENT",
                    quantity_tco2e=700.0,
                    status="Active",
                    is_test=False,
                ),
            ])
            db.session.commit()

            data = aggregate_master_report_data(
                "regional", "basin_alpha", 2024, 2024, "AR5", tenant_id=info["tenant_id"]
            )
            topics = " | ".join(r.get("topic", "") for r in data.get("dynamic_quality_audit", []))
            assert f"Active Project 2024 {info['tag']}" in topics
            assert f"Ongoing Timeless Project {info['tag']}" in topics
            assert f"Old Project 2021 {info['tag']}" not in topics
    finally:
        _cleanup_isolated_tenant_fixture(info)


def test_forensic_pdf_buffer_class_and_pfd_base_cache_lru_bound():
    info = _create_isolated_tenant_fixture()
    try:
        clear_chart_cache()
        assert len(_PFD_BASE_CACHE) == 0

        for idx in range(_MAX_PFD_BASE_CACHE_ENTRIES + 4):
            _get_pfd_base_template(
                "en",
                150,
                active_tuple=(f"mod_{idx}",),
                has_filter=True,
            )
        assert len(_PFD_BASE_CACHE) == _MAX_PFD_BASE_CACHE_ENTRIES
        assert ("en", 150, True, ("mod_0",)) not in _PFD_BASE_CACHE
        assert ("en", 150, True, (f"mod_{_MAX_PFD_BASE_CACHE_ENTRIES + 3}",)) in _PFD_BASE_CACHE

        # Ensure empty active filter and unfiltered mode keep distinct keys
        _get_pfd_base_template("en", 150, active_tuple=(), has_filter=True)
        _get_pfd_base_template("en", 150, active_tuple=(), has_filter=False)
        assert ("en", 150, True, ()) in _PFD_BASE_CACHE
        assert ("en", 150, False, ()) in _PFD_BASE_CACHE

        with app.app_context():
            buf = generate_master_publication_pdf(
                mode="regional",
                region_key="basin_alpha",
                start_year=2024,
                end_year=2024,
                language="en",
                tenant_id=info["tenant_id"],
            )
            assert isinstance(buf, MasterReportPdfBuffer)
            assert isinstance(buf, io.BytesIO)
            assert len(buf.report_hash) == 64
            assert buf.dataset_hash and len(buf.dataset_hash) == 64
    finally:
        clear_chart_cache()
        _cleanup_isolated_tenant_fixture(info)

