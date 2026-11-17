"""Comprehensive tests for UNEP OGMP 2.0 Level 4 / Level 5 engine, API, RBAC, and 13-sheet workbook."""
import io
import math
import uuid

import openpyxl
import pytest
from types import SimpleNamespace

from app import app
from extensions import db
from models import (
    Facility,
    OgmpAnnualReport,
    OgmpAsset,
    OgmpAssetReport,
    OgmpAuditTrail,
    OgmpEmissionSource,
    OgmpImplementationPlan,
    OgmpReportingEntity,
    OgmpSiteMeasurement,
    OgmpTarget,
    ProductionData,
    User,
    UserFacilityAccess,
)
from services.ogmp_reconciliation import (
    MID_DOWNSTREAM_SOURCE_CATALOG,
    UPSTREAM_SOURCE_CATALOG,
    build_default_implementation_plan,
    compute_bottom_up_rss,
    compute_portfolio_materiality,
    compute_top_down_rss,
    evaluate_l4_materiality,
    get_source_catalog,
    reconcile_l4_l5,
    validate_emission_source_payload,
)


def _login_as(client, user: User, tenant_id: str):
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = user.role
        sess["email"] = user.email
        sess["orgName"] = user.orgName
        sess["tenant_id"] = tenant_id


def _make_user(role: str, tenant_id: str, email_prefix: str) -> User:
    u = User(
        email=f"{email_prefix}_{uuid.uuid4().hex[:8]}@example.org",
        fullName=f"Test {role}",
        orgName="Test Energy Corp",
        sector="Oil & Gas",
        role=role,
        tenant_id=tenant_id,
        status="active",
        is_test=True,
    )
    u.set_password("StrongPass!123")
    db.session.add(u)
    db.session.flush()
    return u


def _make_facility(tenant_id: str, name: str, activity: str = "EP", segment: str = "Upstream") -> Facility:
    f = Facility(
        name=f"{name}_{uuid.uuid4().hex[:6]}",
        location="Sector Test",
        region="Basin Test",
        division="Production",
        activity=activity,
        segment=segment,
        field="OF",
        country="Algeria",
        operator_status="operated",
        equity_share_pct=100.0,
        ogmp_membership_year=2023,
        reconciliation_threshold=20.0,
        tenant_id=tenant_id,
        is_test=True,
    )
    db.session.add(f)
    db.session.flush()
    return f


# ---------------------------------------------------------------------------
# Pure Domain Logic Tests
# ---------------------------------------------------------------------------

def test_ogmp_source_catalog_counts_and_rules():
    assert len(UPSTREAM_SOURCE_CATALOG) == 15
    assert len(MID_DOWNSTREAM_SOURCE_CATALOG) == 12
    assert len({s["code"] for s in UPSTREAM_SOURCE_CATALOG}) == 15
    assert len({s["code"] for s in MID_DOWNSTREAM_SOURCE_CATALOG}) == 12

    up = get_source_catalog("Upstream")
    assert len(up["active"]) == 15
    md = get_source_catalog("Midstream")
    assert len(md["active"]) == 12
    assert len(up["pathways"]) == 6

    # N/A forces ch4 to zero
    na_clean = validate_emission_source_payload({
        "source_code": "UP-08",
        "source_name": "Well Completions",
        "ogmp_level": 3,
        "status_flag": "N/A",
        "ch4_tonnes": 12.5,
    })
    assert na_clean["ch4_tonnes"] == 0.0

    # Quantified == 0 requires zero_emission_explanation
    with pytest.raises(ValueError, match="zero_emission_explanation"):
        validate_emission_source_payload({
            "source_code": "UP-04",
            "source_name": "Pneumatic Devices",
            "ogmp_level": 4,
            "status_flag": "Quantified",
            "ch4_tonnes": 0.0,
        })

    # YoY > +/-10% requires yoy_explanation
    with pytest.raises(ValueError, match="yoy_explanation"):
        validate_emission_source_payload(
            {
                "source_code": "UP-02",
                "source_name": "Flaring",
                "ogmp_level": 4,
                "status_flag": "Quantified",
                "ch4_tonnes": 80.0,
            },
            prior_year_ch4=100.0,  # -20% YoY
        )

    ok_yoy = validate_emission_source_payload(
        {
            "source_code": "UP-02",
            "source_name": "Flaring",
            "ogmp_level": 4,
            "status_flag": "Quantified",
            "ch4_tonnes": 80.0,
            "yoy_explanation": "VRU tie-in reduced flaring.",
        },
        prior_year_ch4=100.0,
    )
    assert ok_yoy["yoy_change_pct"] == -20.0


def test_l4_materiality_thresholds_and_l3_floor():
    # >= 90% at L4 passes
    sources_92 = [
        SimpleNamespace(id=1, source_code="UP-01", source_name="S1", ogmp_level=4, status_flag="Quantified", ch4_tonnes=92.0, uncertainty_pct=10.0),
        SimpleNamespace(id=2, source_code="UP-02", source_name="S2", ogmp_level=3, status_flag="Quantified", ch4_tonnes=8.0, uncertainty_pct=20.0),
    ]
    mat92 = evaluate_l4_materiality(sources_92)
    assert mat92["passed"] is True
    assert mat92["l4_materiality_pct"] == 92.0

    # 75% at L4 fails without justification, passes with justification if remaining material >= L3
    sources_75 = [
        SimpleNamespace(id=1, source_code="UP-01", source_name="S1", ogmp_level=4, status_flag="Quantified", ch4_tonnes=75.0, uncertainty_pct=10.0),
        SimpleNamespace(id=2, source_code="UP-02", source_name="S2", ogmp_level=3, status_flag="Quantified", ch4_tonnes=25.0, uncertainty_pct=20.0),
    ]
    assert evaluate_l4_materiality(sources_75)["passed"] is False
    assert evaluate_l4_materiality(sources_75, l4_justification="SCADA metered L3 fallback")["passed"] is True

    # Remaining material source (>=5%) below L3 fails even at 92% L4
    sources_bad_l2 = [
        SimpleNamespace(id=1, source_code="UP-01", source_name="S1", ogmp_level=4, status_flag="Quantified", ch4_tonnes=92.0, uncertainty_pct=10.0),
        SimpleNamespace(id=2, source_code="UP-02", source_name="S2", ogmp_level=2, status_flag="Quantified", ch4_tonnes=8.0, uncertainty_pct=45.0),
    ]
    bad = evaluate_l4_materiality(sources_bad_l2, l4_justification="Justification provided")
    assert bad["passed"] is False
    assert len(bad["remaining_material_below_l3"]) == 1


def test_rss_uncertainty_pathways_and_option2_variance():
    # RSS math: sqrt((100*0.10)^2 + (100*0.20)^2) = sqrt(100 + 400) = sqrt(500) = 22.3607
    srcs = [
        SimpleNamespace(ogmp_level=4, status_flag="Quantified", ch4_tonnes=100.0, uncertainty_pct=10.0),
        SimpleNamespace(ogmp_level=4, status_flag="Quantified", ch4_tonnes=100.0, uncertainty_pct=20.0),
    ]
    bu = compute_bottom_up_rss(srcs)
    assert math.isclose(bu["half_width_tch4"], math.sqrt(500), rel_tol=1e-3)
    assert bu["ci_low_tch4"] < 200.0 < bu["ci_high_tch4"]

    # Pathway 1: within 20% and overlapping 95% CIs -> Level 5
    meas_p1 = [SimpleNamespace(measurement_mode="Annualized", option_mode="Option 1", measured_rate_kg_hr=24.0, operating_hours_year=8760.0, annualized_tch4=210.0, uncertainty_pct=15.0)]
    res_p1 = reconcile_l4_l5(srcs, meas_p1, threshold_pct=20.0)
    assert res_p1["pathway_code"] == "1"
    assert res_p1["reporting_level"] == 5
    assert res_p1["ci_overlaps"] is True

    # Pathway 2a: variance > 20% (+25%), but wide CIs still overlap -> Level 5 under 2a
    meas_2a = [SimpleNamespace(measurement_mode="Annualized", option_mode="Option 1", measured_rate_kg_hr=28.5, operating_hours_year=8760.0, annualized_tch4=250.0, uncertainty_pct=25.0)]
    res_2a = reconcile_l4_l5(srcs, meas_2a, threshold_pct=20.0)
    assert res_2a["pathway_code"] == "2a"
    assert res_2a["ci_overlaps"] is True

    # Pathway 2b: TD >> BU and disjoint CIs -> Level 4 Discrepancy Flagged
    meas_2b = [SimpleNamespace(measurement_mode="Annualized", option_mode="Option 1", measured_rate_kg_hr=50.0, operating_hours_year=8760.0, annualized_tch4=400.0, uncertainty_pct=5.0)]
    res_2b = reconcile_l4_l5(srcs, meas_2b, threshold_pct=20.0)
    assert res_2b["pathway_code"] == "2b"
    assert res_2b["reporting_level"] == 4
    assert res_2b["ci_overlaps"] is False

    # Pathway 2c: BU >> TD and disjoint CIs -> Pathway 2c
    meas_2c = [SimpleNamespace(measurement_mode="Annualized", option_mode="Option 1", measured_rate_kg_hr=10.0, operating_hours_year=8760.0, annualized_tch4=80.0, uncertainty_pct=5.0)]
    res_2c = reconcile_l4_l5(srcs, meas_2c, threshold_pct=20.0)
    assert res_2c["pathway_code"] == "2c"

    # Pathway 2d: Instantaneous disjoint -> Pathway 2d
    meas_2d = [SimpleNamespace(measurement_mode="Instantaneous", option_mode="Option 1", measured_rate_kg_hr=45.0, operating_hours_year=8760.0, annualized_tch4=390.0, uncertainty_pct=5.0)]
    res_2d = reconcile_l4_l5(srcs, meas_2d, threshold_pct=20.0)
    assert res_2d["pathway_code"] == "2d"

    # Option 2 multi-campaign widens CI when campaigns diverge
    opt1_multi = compute_top_down_rss([
        SimpleNamespace(measurement_mode="Annualized", option_mode="Option 1", annualized_tch4=150.0, uncertainty_pct=10.0),
        SimpleNamespace(measurement_mode="Annualized", option_mode="Option 1", annualized_tch4=250.0, uncertainty_pct=10.0),
    ], option_mode="Option 1")
    opt2_multi = compute_top_down_rss([
        SimpleNamespace(measurement_mode="Annualized", option_mode="Option 2", annualized_tch4=150.0, uncertainty_pct=10.0),
        SimpleNamespace(measurement_mode="Annualized", option_mode="Option 2", annualized_tch4=250.0, uncertainty_pct=10.0),
    ], option_mode="Option 2")
    assert opt2_multi["half_width_tch4"] > opt1_multi["half_width_tch4"]


def test_portfolio_95pct_materiality_and_implementation_plans():
    entities = [
        SimpleNamespace(id=1, facility_id=10, entity_name="Op Asset A", asset_name="A", segment="Upstream", country="DZ", operator_status="operated", operating_company="TestOp", working_interest_pct=100.0, is_nojv_material_excluded=False, is_member_reported_nojv=False, exclusion_reason=""),
        SimpleNamespace(id=2, facility_id=11, entity_name="NOJV Small", asset_name="B", segment="Midstream", country="DZ", operator_status="non_operated", operating_company="PartnerX", working_interest_pct=2.0, is_nojv_material_excluded=True, is_member_reported_nojv=True, exclusion_reason="<5% share"),
    ]
    res = compute_portfolio_materiality(entities, {10: 500.0, 11: 500.0})
    # Equity: 500 vs 10 => Total 510 => Minor NOJV = 1.96% (<5%), Included = 98.04% (>=95%)
    assert res["meets_95pct_threshold"] is True
    assert res["nojv_exclusion_count"] == 1
    assert res["member_reported_nojv_count"] == 1

    op_plan = build_default_implementation_plan(1, "Op Asset", operator_status="operated", base_year=2023)
    nojv_plan = build_default_implementation_plan(2, "NOJV Asset", operator_status="non_operated", base_year=2023)
    assert len(op_plan) == 11  # Y0..Y10
    assert op_plan[3]["target_level"] == 5  # Operated reaches L5 at Y3
    assert nojv_plan[5]["target_level"] == 5  # NOJV reaches L5 at Y5


# ---------------------------------------------------------------------------
# API Integration, RBAC, Tenant Isolation & 13-Sheet Workbook Tests
# ---------------------------------------------------------------------------

def test_ogmp_l4_l5_full_api_workflow_rbac_and_workbook():
    tenant = f"ogmp_t_{uuid.uuid4().hex[:8]}"
    other_tenant = f"ogmp_other_{uuid.uuid4().hex[:8]}"

    with app.app_context():
        admin = _make_user("admin", tenant, "ogmp_admin")
        auditor = _make_user("auditor", tenant, "ogmp_aud")
        it_user = _make_user("it_admin", tenant, "ogmp_it")
        other_admin = _make_user("admin", other_tenant, "ogmp_other_adm")

        fac = _make_facility(tenant, "OGMP Alpha Hub", "EP", "Upstream")
        non_og_fac = _make_facility(tenant, "Cement Kiln Site", "Cement & Clinker", "Cement")
        db.session.add(UserFacilityAccess(user_id=auditor.id, facility_id=fac.id, access_level="verifier"))
        db.session.add(ProductionData(
            facility_id=fac.id, year=2025, month=6,
            oil_amount=100000.0, gas_amount=5000000.0, oil_unit="bbl", gas_unit="mscf",
            is_test=True,
        ))
        db.session.commit()
        fac_id, non_og_id = fac.id, non_og_fac.id
        user_ids = [admin.id, auditor.id, it_user.id, other_admin.id]
        fac_ids = [fac.id, non_og_fac.id]

    try:
        with app.test_client() as client:
            # 1. IT role blocked (403)
            _login_as(client, it_user, tenant)
            assert client.get("/api/ogmp/entities").status_code == 403
            assert client.get("/api/ogmp/catalogs").status_code == 403

            # 2. Auditor can GET but cannot POST (403)
            _login_as(client, auditor, tenant)
            assert client.get("/api/ogmp/catalogs").status_code == 200
            assert client.post("/api/ogmp/entities", json={"entity_name": "X"}).status_code == 403

            # 3. Admin creates entity, target, asset
            _login_as(client, admin, tenant)
            cats = client.get("/api/ogmp/catalogs?segment=Upstream").get_json()
            assert len(cats["upstream"]) == 15 and len(cats["mid_downstream"]) == 12

            r_ent = client.post("/api/ogmp/entities", json={
                "facility_id": fac_id,
                "entity_name": "Alpha OGMP Entity",
                "asset_name": "Alpha Asset",
                "segment": "Upstream",
                "operator_status": "operated",
                "working_interest_pct": 100.0,
                "membership_year": 2023,
            })
            assert r_ent.status_code == 201, r_ent.get_json()
            ent_id = r_ent.get_json()["id"]

            assert client.post("/api/ogmp/targets", json={
                "reporting_entity_id": ent_id,
                "target_year": 2025,
                "upstream_target_pct": 0.20,
            }).status_code == 201

            assert client.post("/api/ogmp/assets", json={
                "reporting_entity_id": ent_id,
                "facility_id": fac_id,
                "asset_name": "Alpha Train 1",
            }).status_code == 201

            # 4. Non-O&G facility rejected
            r_nonog = client.post("/api/ogmp/emission-sources", json={
                "facility_id": non_og_id,
                "year": 2025,
                "source_code": "UP-01",
                "source_name": "Combustion",
                "ogmp_level": 4,
                "ch4_tonnes": 10.0,
            })
            assert r_nonog.status_code == 400

            # 5. Log L4 source + zero-emission enforcement + L5 site measurement -> Reconcile -> Level 5 Pathway 1
            assert client.post("/api/ogmp/emission-sources", json={
                "facility_id": fac_id, "year": 2025, "segment": "Upstream",
                "source_code": "UP-02", "source_name": "Flaring", "ogmp_level": 4,
                "status_flag": "Quantified", "ch4_tonnes": 100.0, "uncertainty_pct": 12.0,
            }).status_code == 201

            assert client.post("/api/ogmp/emission-sources", json={
                "facility_id": fac_id, "year": 2025, "segment": "Upstream",
                "source_code": "UP-04", "source_name": "Pneumatics", "ogmp_level": 4,
                "status_flag": "Quantified", "ch4_tonnes": 0.0,
            }).status_code == 400

            assert client.post("/api/ogmp/emission-sources", json={
                "facility_id": fac_id, "year": 2025, "segment": "Upstream",
                "source_code": "UP-04", "source_name": "Pneumatics", "ogmp_level": 4,
                "status_flag": "Quantified", "ch4_tonnes": 0.0,
                "zero_emission_explanation": "Instrument air conversion",
            }).status_code == 201

            assert client.post("/api/ogmp/site-measurements", json={
                "facility_id": fac_id, "year": 2025,
                "campaign_date": "2025-07-01", "survey_type": "Drone LiDAR / OGI Survey",
                "measurement_mode": "Annualized", "option_mode": "Option 1",
                "measured_rate_kg_hr": 12.0, "operating_hours_year": 8760.0, "uncertainty_pct": 15.0,
            }).status_code == 201  # ~105.12 tCH4 (+5.12% vs 100 tCH4 BU)

            r_rec = client.post("/api/ogmp/reconcile", json={"facility_id": fac_id, "year": 2025})
            assert r_rec.status_code == 200, r_rec.get_json()
            rec = r_rec.get_json()
            assert rec["reporting_level"] == 5
            assert rec["pathway_code"] == "1"
            assert rec["ci_overlaps"] is True
            assert rec["reconciliation_status"] == "Reconciled"

            # 6. Generate Y0-Y10 plan, verify portfolio materiality & audit trail
            r_plan = client.post("/api/ogmp/implementation-plans", json={"facility_id": fac_id, "generate_default": True})
            assert r_plan.status_code == 201
            assert len(r_plan.get_json()) == 11

            # regenerating replaces those milestones, so it needs confirm: true
            r_again = client.post("/api/ogmp/implementation-plans", json={"facility_id": fac_id, "generate_default": True})
            assert r_again.status_code == 409
            assert r_again.get_json()["requires_confirmation"] is True
            assert r_again.get_json()["existing_count"] == 11
            r_conf = client.post("/api/ogmp/implementation-plans", json={"facility_id": fac_id, "generate_default": True, "confirm": True})
            assert r_conf.status_code == 201
            assert len(r_conf.get_json()) == 11
            assert len(client.get("/api/ogmp/implementation-plans").get_json()) == 11

            r_port = client.get("/api/ogmp/portfolio-materiality?year=2025")
            assert r_port.status_code == 200
            assert r_port.get_json()["meets_95pct_threshold"] is True

            r_aud = client.get("/api/ogmp/audit-trail")
            assert r_aud.status_code == 200
            assert len(r_aud.get_json()) >= 4

            # 7. Export 13-sheet OGMP workbook
            r_xl = client.get(f"/api/reports/ogmp-export?year=2025&facility_id={fac_id}")
            assert r_xl.status_code == 200
            wb = openpyxl.load_workbook(io.BytesIO(r_xl.data))
            assert len(wb.sheetnames) >= 14  # 13 official tabs (Sheets 0-12) + Audit Assurance
            assert "Audit Assurance" in wb.sheetnames
            assert any("Uncertainty" in s or "Reconciliation" in s for s in wb.sheetnames)
            assert any("Portfolio" in s or "Materiality" in s for s in wb.sheetnames)

            # 8. Cross-tenant admin cannot read another tenant's entity or facility
            _login_as(client, other_admin, other_tenant)
            assert client.get(f"/api/ogmp/emission-sources?facility_id={fac_id}").status_code == 403
            assert len(client.get("/api/ogmp/entities").get_json()) == 0
    finally:
        with app.app_context():
            db.session.rollback()
            tids = [tenant, other_tenant]
            OgmpAuditTrail.query.filter(OgmpAuditTrail.tenant_id.in_(tids)).delete(synchronize_session=False)
            OgmpImplementationPlan.query.filter(OgmpImplementationPlan.tenant_id.in_(tids)).delete(synchronize_session=False)
            OgmpAssetReport.query.filter(OgmpAssetReport.tenant_id.in_(tids)).delete(synchronize_session=False)
            OgmpEmissionSource.query.filter(OgmpEmissionSource.tenant_id.in_(tids)).delete(synchronize_session=False)
            OgmpSiteMeasurement.query.filter(OgmpSiteMeasurement.tenant_id.in_(tids)).delete(synchronize_session=False)
            OgmpAnnualReport.query.filter(OgmpAnnualReport.tenant_id.in_(tids)).delete(synchronize_session=False)
            OgmpAsset.query.filter(OgmpAsset.tenant_id.in_(tids)).delete(synchronize_session=False)
            OgmpTarget.query.filter(OgmpTarget.tenant_id.in_(tids)).delete(synchronize_session=False)
            OgmpReportingEntity.query.filter(OgmpReportingEntity.tenant_id.in_(tids)).delete(synchronize_session=False)
            UserFacilityAccess.query.filter(UserFacilityAccess.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            ProductionData.query.filter(ProductionData.facility_id.in_(fac_ids)).delete(synchronize_session=False)
            Facility.query.filter(Facility.id.in_(fac_ids)).delete(synchronize_session=False)
            User.query.filter(User.id.in_(user_ids)).delete(synchronize_session=False)
            db.session.commit()
