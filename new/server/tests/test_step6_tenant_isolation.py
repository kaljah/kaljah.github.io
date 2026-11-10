"""
Step 6 Regression Tests — Multi-Tenant Isolation
================================================
Proves that:
1. Master report endpoints (/regions, /master-report async PDF, /benchmark-excel)
   strictly include only the authenticated user's tenant facilities, emissions,
   partners, custom factors, SBTi targets, base-year recalculations, and projects.
2. Empty tenants receive no fallback/default tenant data.
3. Regional benchmark & comparison endpoints only aggregate regions/facilities
   belonging to the caller's tenant (including when two tenants share a region name).
4. Cross-tenant access attempts (job polling/download, facility_id queries,
   CBAM/OGMP/National exports, facility updates, custom factors, tenant config)
   are rejected with HTTP 403.
"""

import io
import os
import time
import uuid

import openpyxl
import pypdfium2 as pdfium
import pytest
from app import app
from extensions import db
from models import (
    BaseYearRecalculation,
    CbamProductExport,
    CustomFactor,
    Emission,
    Facility,
    FacilityEquityShare,
    JvPartner,
    MitigationProject,
    MitigationRecord,
    OgmpSurvey,
    ProductionData,
    SbtiTarget,
    Scope2Emission,
    Scope3Emission,
    User,
)
from routes.dashboard import clear_dashboard_cache
from routes.reports_master import _MASTER_JOBS, _MASTER_JOBS_LOCK


def _pdf_text(pdf_bytes: bytes) -> str:
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        chunks = []
        for i in range(len(pdf)):
            page = pdf[i]
            tp = page.get_textpage()
            try:
                chunks.append(tp.get_text_range())
            finally:
                tp.close()
                page.close()
        return " ".join(" ".join(chunks).split())
    finally:
        pdf.close()


def _with_tenant_kwarg(model_cls, tenant_id: str, **kwargs):
    if hasattr(model_cls, "tenant_id"):
        kwargs["tenant_id"] = tenant_id
    return model_cls(**kwargs)


def _login_session(client, user: User, tenant_id: str):
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = user.role
        sess["email"] = user.email
        sess["orgName"] = user.orgName
        sess["tenant_id"] = tenant_id


def _run_master_pdf(client, payload: dict) -> bytes:
    resp = client.post("/api/reports/master-report", json=payload)
    assert resp.status_code in (200, 202), f"Unexpected start status {resp.status_code}: {resp.get_json()}"
    if resp.status_code == 200 and resp.mimetype == "application/pdf":
        return resp.data

    body = resp.get_json()
    job_id = body["job_id"]
    deadline = time.time() + 30.0
    while time.time() < deadline:
        st = client.get(f"/api/reports/master-report/jobs/{job_id}")
        assert st.status_code == 200
        sdata = st.get_json()
        if sdata["status"] == "completed":
            dl = client.get(f"/api/reports/master-report/jobs/{job_id}/download")
            assert dl.status_code == 200
            return dl.data
        if sdata["status"] == "failed":
            pytest.fail(f"Master report job failed: {sdata}")
        time.sleep(0.05)
    pytest.fail("Timed out waiting for master report background job")


@pytest.fixture
def two_tenant_dataset():
    """Creates two isolated tenants (default & mena_operator_b) + an empty third tenant."""
    tag = uuid.uuid4().hex[:8]
    created_fac_ids = []

    with app.app_context():
        clear_dashboard_cache()
        admin_a = _with_tenant_kwarg(
            User,
            "default",
            email=f"t6_admin_a_{tag}@example.org",
            fullName="Tenant A Admin",
            orgName="Demo Operator Co.",
            sector="Oil & Gas",
            role="admin",
            status="active",
        )
        admin_a.set_password("StrongPassA123!")
        op_a = _with_tenant_kwarg(
            User,
            "default",
            email=f"t6_op_a_{tag}@example.org",
            fullName="Tenant A Operator",
            orgName="Demo Operator Co.",
            sector="Oil & Gas",
            role="operator",
            location="Basin Alpha",
            status="active",
        )
        op_a.set_password("StrongPassA123!")

        admin_b = _with_tenant_kwarg(
            User,
            "mena_operator_b",
            email=f"t6_admin_b_{tag}@alamal-petro.com",
            fullName="Tenant B Admin",
            orgName="Al-Amal Petroleum Corp",
            sector="Oil & Gas",
            role="admin",
            status="active",
        )
        admin_b.set_password("StrongPassB123!")

        admin_c = _with_tenant_kwarg(
            User,
            "gamma_operator_c",
            email=f"t6_admin_c_{tag}@gamma-energy.org",
            fullName="Tenant C Admin",
            orgName="Gamma Energy Ltd",
            sector="Oil & Gas",
            role="admin",
            status="active",
        )
        admin_c.set_password("StrongPassC123!")

        db.session.add_all([admin_a, op_a, admin_b, admin_c])
        db.session.flush()

        fac_a1 = _with_tenant_kwarg(
            Facility,
            "default",
            name=f"Alpha Secret Facility {tag}",
            code=f"T6A1-{tag}",
            region="Basin Alpha",
            segment="Upstream",
            country="Algeria",
            field="Alpha Field",
        )
        fac_a_shared = _with_tenant_kwarg(
            Facility,
            "default",
            name=f"Alpha Shared Asset {tag}",
            code=f"T6ASH-{tag}",
            region="Shared Basin",
            segment="Midstream",
            country="Algeria",
            field="Shared Field A",
        )
        fac_b1 = _with_tenant_kwarg(
            Facility,
            "mena_operator_b",
            name=f"Beta Horizon Asset {tag}",
            code=f"T6B1-{tag}",
            region="TenantB Basin",
            segment="Upstream",
            country="MENA Region",
            field="Beta Field",
        )
        fac_b_shared = _with_tenant_kwarg(
            Facility,
            "mena_operator_b",
            name=f"Beta Shared Asset {tag}",
            code=f"T6BSH-{tag}",
            region="Shared Basin",
            segment="Upstream",
            country="MENA Region",
            field="Shared Field B",
        )
        db.session.add_all([fac_a1, fac_a_shared, fac_b1, fac_b_shared])
        db.session.flush()
        created_fac_ids = [fac_a1.id, fac_a_shared.id, fac_b1.id, fac_b_shared.id]

        # Seed verified 2024 emissions for both tenants with distinct markers
        records = [
            Emission(
                facility_id=fac_a1.id,
                year=2024,
                month=1,
                process_type="stationary_combustion",
                activity="Stationary Combustion",
                fuel_type="natural_gas",
                quantity=100000.0,
                unit="m3",
                co2_emissions=12000.0,
                ch4_emissions=12.0,
                n2o_emissions=0.05,
                co2e_total=12345.0,
                status="Verified",
                created_by=admin_a.id,
            ),
            Emission(
                facility_id=fac_a_shared.id,
                year=2024,
                month=2,
                process_type="flaring",
                activity="Flaring",
                fuel_type="flare_gas",
                quantity=10000.0,
                unit="m3",
                co2_emissions=2000.0,
                ch4_emissions=5.0,
                n2o_emissions=0.01,
                co2e_total=2140.0,
                status="Verified",
                created_by=admin_a.id,
            ),
            Emission(
                facility_id=fac_b1.id,
                year=2024,
                month=1,
                process_type="stationary_combustion",
                activity="Stationary Combustion",
                fuel_type="natural_gas",
                quantity=500000.0,
                unit="m3",
                co2_emissions=86000.0,
                ch4_emissions=100.0,
                n2o_emissions=0.3,
                co2e_total=88888.0,
                status="Verified",
                created_by=admin_b.id,
            ),
            Emission(
                facility_id=fac_b_shared.id,
                year=2024,
                month=2,
                process_type="flaring",
                activity="Flaring",
                fuel_type="flare_gas",
                quantity=40000.0,
                unit="m3",
                co2_emissions=9000.0,
                ch4_emissions=30.0,
                n2o_emissions=0.02,
                co2e_total=9845.0,
                status="Verified",
                created_by=admin_b.id,
            ),
            Scope2Emission(
                facility_id=fac_a1.id,
                year=2024,
                month=1,
                source_type="electricity",
                electricity_kwh=1500000.0,
                emission_factor=0.5,
                co2e=1111.0,
                co2e_location_based=1111.0,
                co2e_market_based=1111.0,
                status="Verified",
                created_by=admin_a.id,
            ),
            Scope2Emission(
                facility_id=fac_b1.id,
                year=2024,
                month=1,
                source_type="electricity",
                electricity_kwh=4500000.0,
                emission_factor=0.5,
                co2e=3333.0,
                co2e_location_based=3333.0,
                co2e_market_based=3333.0,
                status="Verified",
                created_by=admin_b.id,
            ),
            Scope3Emission(
                facility_id=fac_a1.id,
                year=2024,
                month=1,
                category="Category 1: Purchased Goods",
                sub_category=f"Alpha Steel Supply {tag}",
                activity_data=1000.0,
                unit="USD",
                emission_factor=2.222,
                co2e=2222.0,
                status="Verified",
                created_by=admin_a.id,
            ),
            Scope3Emission(
                facility_id=fac_b1.id,
                year=2024,
                month=1,
                category="Category 1: Purchased Goods",
                sub_category=f"Beta Cement Supply {tag}",
                activity_data=2000.0,
                unit="USD",
                emission_factor=2.222,
                co2e=4444.0,
                status="Verified",
                created_by=admin_b.id,
            ),
            ProductionData(
                facility_id=fac_a1.id,
                year=2024,
                month=1,
                gross_gas_mmsm3=10.0,
                crude_oil_mmboe=0.5,
                total_production_mmboe=0.5,
            ),
            ProductionData(
                facility_id=fac_b1.id,
                year=2024,
                month=1,
                gross_gas_mmsm3=25.0,
                crude_oil_mmboe=1.2,
                total_production_mmboe=1.2,
            ),
            OgmpSurvey(
                facility_id=fac_a1.id,
                year=2024,
                survey_date="2024-06-15",
                survey_type="Drone OGI",
                measured_rate_kg_hr=1.5,
                estimated_annual_tch4=13.1,
                instrument_vendor=f"AlphaVendor-{tag}",
            ),
            OgmpSurvey(
                facility_id=fac_b1.id,
                year=2024,
                survey_date="2024-06-20",
                survey_type="Satellite",
                measured_rate_kg_hr=5.5,
                estimated_annual_tch4=48.1,
                instrument_vendor=f"BetaSatVendor-{tag}",
            ),
            CbamProductExport(
                facility_id=fac_a1.id,
                year=2024,
                month=1,
                product_name=f"Alpha Urea {tag}",
                cn_code="3102 10 00",
                quantity_tonnes=1000.0,
                specific_embedded_direct=1.5,
            ),
            CbamProductExport(
                facility_id=fac_b1.id,
                year=2024,
                month=1,
                product_name=f"Beta Ammonia {tag}",
                cn_code="2814 10 00",
                quantity_tonnes=2000.0,
                specific_embedded_direct=2.1,
            ),
            MitigationProject(
                facility_id=fac_a1.id,
                name=f"Alpha Decarb Project {tag}",
                project_type="flare_recovery",
                year=2024,
                quantity_tco2e=1500.0,
                status="active",
                created_by=admin_a.id,
            ),
            MitigationProject(
                facility_id=fac_b1.id,
                name=f"Beta Decarb Project {tag}",
                project_type="methane_ldar",
                year=2024,
                quantity_tco2e=9500.0,
                status="active",
                created_by=admin_b.id,
            ),
            _with_tenant_kwarg(
                MitigationRecord,
                "default",
                type="Offset",
                subtype=f"Alpha Mitigation Ledger {tag}",
                year=2024,
                quantity_tco2e=500.0,
                notes=f"Alpha Mitigation Ledger {tag}",
                reference_id=f"AM-{tag}",
            ),
            _with_tenant_kwarg(
                MitigationRecord,
                "mena_operator_b",
                type="Offset",
                subtype=f"Beta Mitigation Ledger {tag}",
                year=2024,
                quantity_tco2e=2500.0,
                notes=f"Beta Mitigation Ledger {tag}",
                reference_id=f"BM-{tag}",
            ),
            _with_tenant_kwarg(
                CustomFactor,
                "default",
                facility_id=fac_a1.id,
                name=f"Alpha Secret Fuel {tag}",
                parent_fuel="natural_gas",
                co2_factor=56.1,
                ch4_factor=0.001,
                n2o_factor=0.0001,
                unit="kg/MMBtu",
                status="Approved",
                created_by=admin_a.id,
            ),
            _with_tenant_kwarg(
                CustomFactor,
                "mena_operator_b",
                facility_id=fac_b1.id,
                name=f"Beta Secret Fuel {tag}",
                parent_fuel="natural_gas",
                co2_factor=58.4,
                ch4_factor=0.002,
                n2o_factor=0.0002,
                unit="kg/MMBtu",
                status="Approved",
                created_by=admin_b.id,
            ),
            _with_tenant_kwarg(
                BaseYearRecalculation,
                "default",
                year=2021,
                reason=f"Alpha Base Year Marker {tag}",
                previous_emissions=555000.0,
                adjusted_emissions=555555.0,
                created_by=admin_a.id,
            ),
            _with_tenant_kwarg(
                BaseYearRecalculation,
                "mena_operator_b",
                year=2022,
                reason=f"Beta Base Year Marker {tag}",
                previous_emissions=777000.0,
                adjusted_emissions=777777.0,
                created_by=admin_b.id,
            ),
            _with_tenant_kwarg(
                SbtiTarget,
                "default",
                base_year=2021,
                base_year_emissions=666666.0,
                target_year=2030,
                reduction_rate_pct=4.2,
                pathway_type="1.5C",
                created_by=admin_a.id,
            ),
            _with_tenant_kwarg(
                SbtiTarget,
                "mena_operator_b",
                base_year=2022,
                base_year_emissions=999999.0,
                target_year=2035,
                reduction_rate_pct=5.0,
                pathway_type="1.5C",
                created_by=admin_b.id,
            ),
        ]

        partner_a = _with_tenant_kwarg(
            JvPartner,
            "default",
            name=f"Alpha JV Partner {tag}",
            code=f"AJVP{tag[:4]}".upper(),
            country="Algeria",
            is_operator=False,
        )
        partner_b = _with_tenant_kwarg(
            JvPartner,
            "mena_operator_b",
            name=f"Al-Amal JV Partner {tag}",
            code=f"BJVP{tag[:4]}".upper(),
            country="MENA Region",
            is_operator=True,
        )
        db.session.add_all(records + [partner_a, partner_b])
        db.session.flush()

        share_a = FacilityEquityShare(
            facility_id=fac_a1.id,
            partner_id=partner_a.id,
            equity_share_pct=35.0,
            effective_start_date="2020-01-01",
        )
        share_b = FacilityEquityShare(
            facility_id=fac_b1.id,
            partner_id=partner_b.id,
            equity_share_pct=100.0,
            effective_start_date="2020-01-01",
        )
        db.session.add_all([share_a, share_b])
        db.session.commit()

        info = {
            "tag": tag,
            "admin_a_id": admin_a.id,
            "op_a_id": op_a.id,
            "admin_b_id": admin_b.id,
            "admin_c_id": admin_c.id,
            "fac_a1_id": fac_a1.id,
            "fac_a_shared_id": fac_a_shared.id,
            "fac_b1_id": fac_b1.id,
            "fac_b_shared_id": fac_b_shared.id,
            "fac_a1_name": fac_a1.name,
            "fac_a_shared_name": fac_a_shared.name,
            "fac_b1_name": fac_b1.name,
            "fac_b_shared_name": fac_b_shared.name,
            "partner_a_id": partner_a.id,
            "partner_b_id": partner_b.id,
            "partner_a_name": partner_a.name,
            "partner_b_name": partner_b.name,
            "cf_a_id": records[-6].id,
            "cf_b_id": records[-5].id,
            "cf_a_name": records[-6].name,
            "cf_b_name": records[-5].name,
            "mit_rec_ids": [records[-8].id, records[-7].id],
            "proj_a_name": f"Alpha Decarb Project {tag}",
            "proj_b_name": f"Beta Decarb Project {tag}",
            "by_a_id": records[-4].id,
            "by_b_id": records[-3].id,
            "sbti_ids": [records[-2].id, records[-1].id],
        }

    try:
        yield info
    finally:
        with app.app_context():
            db.session.rollback()
            with _MASTER_JOBS_LOCK:
                for jid, jdata in list(_MASTER_JOBS.items()):
                    if jdata.get("user_id") in (
                        info["admin_a_id"],
                        info["op_a_id"],
                        info["admin_b_id"],
                        info["admin_c_id"],
                    ):
                        path = jdata.get("file_path")
                        if path and os.path.exists(path):
                            try:
                                os.remove(path)
                            except OSError:
                                pass
                        _MASTER_JOBS.pop(jid, None)

            fids = created_fac_ids
            if fids:
                for mdl in (
                    FacilityEquityShare,
                    MitigationProject,
                    CbamProductExport,
                    OgmpSurvey,
                    ProductionData,
                    Scope3Emission,
                    Scope2Emission,
                    Emission,
                    CustomFactor,
                ):
                    mdl.query.filter(mdl.facility_id.in_(fids)).delete(synchronize_session=False)
            BaseYearRecalculation.query.filter(
                BaseYearRecalculation.id.in_([info["by_a_id"], info["by_b_id"]])
            ).delete(synchronize_session=False)
            SbtiTarget.query.filter(SbtiTarget.id.in_(info["sbti_ids"])).delete(synchronize_session=False)
            MitigationRecord.query.filter(MitigationRecord.id.in_(info["mit_rec_ids"])).delete(synchronize_session=False)
            JvPartner.query.filter(
                JvPartner.id.in_([info["partner_a_id"], info["partner_b_id"]])
            ).delete(synchronize_session=False)
            if fids:
                Facility.query.filter(Facility.id.in_(fids)).delete(synchronize_session=False)
            User.query.filter(
                User.id.in_([info["admin_a_id"], info["op_a_id"], info["admin_b_id"], info["admin_c_id"]])
            ).delete(synchronize_session=False)
            db.session.commit()
            clear_dashboard_cache()


def test_master_report_regions_isolated_per_tenant(client, two_tenant_dataset):
    info = two_tenant_dataset
    with app.app_context():
        admin_a = db.session.get(User, info["admin_a_id"])
        admin_b = db.session.get(User, info["admin_b_id"])
        admin_c = db.session.get(User, info["admin_c_id"])

    # Tenant A regions
    _login_session(client, admin_a, "default")
    res_a = client.get("/api/reports/master-report/regions")
    assert res_a.status_code == 200
    body_a = res_a.get_json()
    fac_names_a = [fn for r in body_a["regions"] for fn in r.get("facility_names", [])]
    assert info["fac_a1_name"] in fac_names_a
    assert info["fac_a_shared_name"] in fac_names_a
    assert info["fac_b1_name"] not in fac_names_a
    assert info["fac_b_shared_name"] not in fac_names_a
    shared_a = [r for r in body_a["regions"] if "shared" in r["name"].lower() or "shared" in r["key"]]
    assert len(shared_a) == 1
    assert shared_a[0]["facility_count"] == 1

    # Tenant B regions
    _login_session(client, admin_b, "mena_operator_b")
    res_b = client.get("/api/reports/master-report/regions")
    assert res_b.status_code == 200
    body_b = res_b.get_json()
    fac_names_b = [fn for r in body_b["regions"] for fn in r.get("facility_names", [])]
    assert info["fac_b1_name"] in fac_names_b
    assert info["fac_b_shared_name"] in fac_names_b
    assert info["fac_a1_name"] not in fac_names_b
    assert info["fac_a_shared_name"] not in fac_names_b
    nat_b = next(r for r in body_b["regions"] if r["key"] == "national")
    assert "Al-Amal" in nat_b["name"]
    shared_b = [r for r in body_b["regions"] if "shared" in r["name"].lower() or "shared" in r["key"]]
    assert len(shared_b) == 1
    assert shared_b[0]["facility_count"] == 1

    # Empty Tenant C receives zero regions / facilities
    _login_session(client, admin_c, "gamma_operator_c")
    res_c = client.get("/api/reports/master-report/regions")
    assert res_c.status_code == 200
    body_c = res_c.get_json()
    assert body_c["regions"] == []


def test_master_report_pdf_and_jobs_isolated_between_tenants(client, two_tenant_dataset):
    info = two_tenant_dataset
    with app.app_context():
        admin_a = db.session.get(User, info["admin_a_id"])
        admin_b = db.session.get(User, info["admin_b_id"])
        admin_c = db.session.get(User, info["admin_c_id"])

    # 1. Tenant A National Master Report must exclude all Tenant B identifiers
    _login_session(client, admin_a, "default")
    pdf_a = _run_master_pdf(
        client,
        {"mode": "national", "start_year": 2024, "end_year": 2024, "gwp_standard": "AR5", "language": "en"},
    )
    txt_a = _pdf_text(pdf_a)
    assert info["fac_a1_name"] in txt_a
    assert info["proj_a_name"] in txt_a
    assert info["fac_b1_name"] not in txt_a
    assert info["fac_b_shared_name"] not in txt_a
    assert info["partner_b_name"] not in txt_a
    assert info["proj_b_name"] not in txt_a
    assert info["cf_b_name"] not in txt_a
    assert "Al-Amal Petroleum" not in txt_a

    # 2. Tenant A Shared Basin Regional Report must exclude Tenant B's Shared Basin asset
    pdf_a_shared = _run_master_pdf(
        client,
        {
            "mode": "regional",
            "region": "shared_basin",
            "start_year": 2024,
            "end_year": 2024,
            "gwp_standard": "AR5",
            "language": "en",
        },
    )
    txt_a_shared = _pdf_text(pdf_a_shared)
    assert info["fac_a_shared_name"] in txt_a_shared
    assert info["fac_b_shared_name"] not in txt_a_shared

    # 3. Tenant B National Master Report must brand as Al-Amal and exclude all Tenant A identifiers
    _login_session(client, admin_b, "mena_operator_b")
    start_b = client.post(
        "/api/reports/master-report",
        json={"mode": "national", "start_year": 2024, "end_year": 2024, "gwp_standard": "AR5", "language": "en"},
    )
    assert start_b.status_code == 202
    job_b_id = start_b.get_json()["job_id"]

    # Wait for Tenant B's job to complete as Tenant B
    deadline = time.time() + 30.0
    while time.time() < deadline:
        st = client.get(f"/api/reports/master-report/jobs/{job_b_id}")
        assert st.status_code == 200
        if st.get_json()["status"] == "completed":
            break
        time.sleep(0.05)
    dl_b = client.get(f"/api/reports/master-report/jobs/{job_b_id}/download")
    assert dl_b.status_code == 200
    txt_b = _pdf_text(dl_b.data)
    assert "Al-Amal Petroleum" in txt_b
    assert info["fac_b1_name"] in txt_b
    assert info["partner_b_name"] in txt_b
    assert info["proj_b_name"] in txt_b
    assert info["fac_a1_name"] not in txt_b
    assert info["fac_a_shared_name"] not in txt_b
    assert info["partner_a_name"] not in txt_b
    assert info["proj_a_name"] not in txt_b
    assert info["cf_a_name"] not in txt_b
    assert "Demo Operator Co." not in txt_b

    # 4. Cross-tenant access to Tenant B's job ID must be rejected with 403
    _login_session(client, admin_a, "default")
    assert client.get(f"/api/reports/master-report/jobs/{job_b_id}").status_code == 403
    assert client.get(f"/api/reports/master-report/jobs/{job_b_id}/download").status_code == 403

    # 5. Empty Tenant C receives a clean 0-asset report without Tenant A/B leakage
    _login_session(client, admin_c, "gamma_operator_c")
    pdf_c = _run_master_pdf(
        client,
        {"mode": "national", "start_year": 2024, "end_year": 2024, "gwp_standard": "AR5", "language": "en"},
    )
    txt_c = _pdf_text(pdf_c)
    assert info["fac_a1_name"] not in txt_c
    assert info["fac_b1_name"] not in txt_c
    assert info["proj_a_name"] not in txt_c
    assert info["proj_b_name"] not in txt_c


def test_benchmark_excel_isolated_per_tenant(client, two_tenant_dataset):
    info = two_tenant_dataset
    with app.app_context():
        admin_a = db.session.get(User, info["admin_a_id"])
        admin_b = db.session.get(User, info["admin_b_id"])

    _login_session(client, admin_a, "default")
    res_a = client.post(
        "/api/reports/master-report/benchmark-excel",
        json={"start_year": 2024, "end_year": 2024},
    )
    assert res_a.status_code == 200
    wb_a = openpyxl.load_workbook(io.BytesIO(res_a.data))
    rows_a = list(wb_a.active.iter_rows(values_only=True))
    cells_a = "\n".join(str(v) for row in rows_a for v in row if v is not None)
    assert "Basin Alpha" in cells_a
    assert "Shared Basin" in cells_a
    assert "TenantB Basin" not in cells_a
    assert "Al-Amal" not in cells_a
    shared_row_a = [r for r in rows_a if r and r[0] and "Shared Basin" in str(r[0])]
    assert len(shared_row_a) == 1
    assert shared_row_a[0][2] == 1  # only Tenant A's facility in Shared Basin
    assert float(shared_row_a[0][4]) == pytest.approx(2140.0, rel=1e-2)

    _login_session(client, admin_b, "mena_operator_b")
    res_b = client.post(
        "/api/reports/master-report/benchmark-excel",
        json={"start_year": 2024, "end_year": 2024},
    )
    assert res_b.status_code == 200
    wb_b = openpyxl.load_workbook(io.BytesIO(res_b.data))
    rows_b = list(wb_b.active.iter_rows(values_only=True))
    cells_b = "\n".join(str(v) for row in rows_b for v in row if v is not None)
    assert "TenantB Basin" in cells_b
    assert "Shared Basin" in cells_b
    assert "Basin Alpha" not in cells_b
    assert "Demo Operator Co." not in cells_b
    shared_row_b = [r for r in rows_b if r and r[0] and "Shared Basin" in str(r[0])]
    assert len(shared_row_b) == 1
    assert shared_row_b[0][2] == 1  # only Tenant B's facility in Shared Basin
    assert float(shared_row_b[0][4]) == pytest.approx(9845.0, rel=1e-2)


def test_cross_tenant_api_endpoints_and_writes_blocked(client, two_tenant_dataset):
    info = two_tenant_dataset
    with app.app_context():
        admin_a = db.session.get(User, info["admin_a_id"])
        admin_b = db.session.get(User, info["admin_b_id"])

    # Tenant A attempts to read/write Tenant B resources
    _login_session(client, admin_a, "default")
    assert client.get(f"/api/emissions/?facility_id={info['fac_b1_id']}").status_code == 403
    assert client.get(f"/api/reports/cbam-export?facility_id={info['fac_b1_id']}").status_code == 403
    assert client.get(f"/api/reports/ogmp-export?facility_id={info['fac_b1_id']}").status_code == 403
    assert client.get(f"/api/reports/national-inventory-export?facility_id={info['fac_b1_id']}").status_code == 403
    assert client.put(f"/api/facilities/{info['fac_b1_id']}", json={"name": "Hijacked"}).status_code == 403
    assert client.delete(f"/api/base-years/{info['by_b_id']}").status_code == 403
    assert client.get("/api/tenant/config?tenant_id=mena_operator_b").status_code == 403

    # Tenant B dashboard, facilities, SBTi, base year, custom factors only show Tenant B
    _login_session(client, admin_b, "mena_operator_b")
    fac_res = client.get("/api/facilities/")
    assert fac_res.status_code == 200
    fac_names = {f["name"] for f in fac_res.get_json()}
    assert info["fac_b1_name"] in fac_names
    assert info["fac_b_shared_name"] in fac_names
    assert info["fac_a1_name"] not in fac_names
    assert info["fac_a_shared_name"] not in fac_names

    sbti_res = client.get("/api/dashboard/sbti-trajectory")
    assert sbti_res.status_code == 200
    sbti_body = sbti_res.get_json()
    assert sbti_body["base_year"] == 2022
    assert sbti_body["target_base_year_emissions"] == pytest.approx(999999.0)

    cf_res = client.get("/api/custom-factors/")
    assert cf_res.status_code == 200
    cf_body = cf_res.get_json()
    cf_items = cf_body["factors"] if isinstance(cf_body, dict) and "factors" in cf_body else cf_body
    cf_names = {c["name"] for c in cf_items}
    assert info["cf_b_name"] in cf_names
    assert info["cf_a_name"] not in cf_names

    assert client.delete(f"/api/custom-factors/{info['cf_a_id']}").status_code == 403

    by_res = client.get("/api/base-years")
    assert by_res.status_code == 200
    by_reasons = " ".join(r.get("reason", "") for r in by_res.get_json().get("history", []))
    assert info["tag"] in by_reasons
    assert "Alpha Base Year Marker" not in by_reasons

    # Tenant B dashboard batch-all must only sum Tenant B's emissions & mitigations
    dash_b = client.get("/api/dashboard/batch-all?year=2024")
    assert dash_b.status_code == 200
    dash_body = dash_b.get_json()
    rows_2024 = [r for r in dash_body.get("summary", []) if r.get("year") == 2024]
    assert rows_2024, f"Expected 2024 summary row for Tenant B, got {dash_body.get('summary')}"
    # Tenant B S1 = 88888 + 9845 = 98733.0, S2 = 3333.0; Tenant A would add 14485 S1 + 1111 S2 if leaked
    assert sum(r["scope1_total"] for r in rows_2024) == pytest.approx(98733.0, rel=1e-3)
    assert sum(r["scope2_total"] for r in rows_2024) == pytest.approx(3333.0, rel=1e-3)
    mit_list = dash_body.get("mitigation") or []
    mit_names = " ".join(str(m.get("name", "")) for m in mit_list)
    assert f"Alpha Mitigation Ledger {info['tag']}" not in mit_names
    assert f"Beta Mitigation Ledger {info['tag']}" in mit_names
