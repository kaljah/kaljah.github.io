"""Comprehensive tests for EU CBAM quarter filtering, pre-export validation, and XML/Excel compliance."""
import io
import uuid
import xml.etree.ElementTree as ET

import openpyxl
from app import app
from extensions import db
from models import (
    CbamProductExport,
    Emission,
    Facility,
    ProductionData,
    ReportingMetadata,
    Scope2Emission,
    User,
    UserFacilityAccess,
)


def _login_as(client, user: User, tenant_id: str):
    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["role"] = user.role
        sess["email"] = user.email
        sess["orgName"] = user.orgName
        sess["tenant_id"] = tenant_id


def test_cbam_quarter_filtering_xml_provenance_ccs_and_validate_endpoint():
    tenant = f"cbam_t_{uuid.uuid4().hex[:8]}"
    prev_meta = None
    with app.app_context():
        admin = User(
            email=f"cbam_adm_{uuid.uuid4().hex[:8]}@example.org",
            fullName="CBAM Admin",
            orgName="Mediterranean Hydrogen Co.",
            sector="Oil & Gas",
            role="admin",
            tenant_id=tenant,
            status="active",
            is_test=True,
        )
        admin.set_password("StrongPass!123")
        it_user = User(
            email=f"cbam_it_{uuid.uuid4().hex[:8]}@example.org",
            fullName="IT User",
            orgName="Mediterranean Hydrogen Co.",
            sector="Oil & Gas",
            role="it_admin",
            tenant_id=tenant,
            status="active",
            is_test=True,
        )
        it_user.set_password("StrongPass!123")
        db.session.add_all([admin, it_user])
        db.session.flush()

        fac = Facility(
            name=f"CBAM Plant {uuid.uuid4().hex[:6]}",
            code=f"CBAM-{uuid.uuid4().hex[:6]}",
            location="Coastal",
            region="Coast",
            division="Export",
            activity="LNG",
            field="GNL",
            country="Algeria",
            tenant_id=tenant,
            is_test=True,
        )
        db.session.add(fac)
        db.session.flush()

        meta = ReportingMetadata.query.filter_by(year=2025).first()
        if meta:
            prev_meta = (meta.assurance_level, meta.assurance_provider)
            meta.assurance_level = "Reasonable Assurance (ISO 14064-3)"
            meta.assurance_provider = "Bureau Veritas Demo"
        else:
            meta = ReportingMetadata(
                year=2025,
                assurance_level="Reasonable Assurance (ISO 14064-3)",
                assurance_provider="Bureau Veritas Demo",
            )
            db.session.add(meta)
        db.session.add(Emission(
            facility_id=fac.id, year=2025, month=4,
            process_type="Stationary Combustion", fuel_type="Natural Gas",
            quantity=1000.0, unit="m3", co2e_total=5000.0,
            status="Verified", is_test=False,  # an export counts real records only (BA-011); removed with the facility
        ))
        db.session.add(Scope2Emission(
            facility_id=fac.id, year=2025, month=4, source_type="electricity",
            electricity_kwh=200000.0, emission_factor=0.5, co2e=100.0,
            grid_region="National Grid", status="Verified",
        ))
        db.session.add(ProductionData(
            facility_id=fac.id, year=2025, month=4,
            oil_amount=0.0, gas_amount=1000000.0, gas_unit="mscf",
            is_test=True,
        ))
        # Q1 record (month=2) and Q2 record (month=5)
        db.session.add_all([
            CbamProductExport(
                facility_id=fac.id, year=2025, month=2, quarter="Q1",
                product_name="Anhydrous Ammonia Q1", cn_code="2814 10 00",
                quantity_tonnes=1000.0, export_destination="EU - France",
                specific_embedded_direct=1.80, specific_embedded_indirect=0.15,
                captured_co2_tonnes=200.0, ccs_certificate_id="CERT-Q1-CCS",
                carbon_price_paid_eur=15.0, carbon_price_legal_ref="Origin Tax Art. 9",
                is_complex_good=True, precursor_name="Natural Gas Feed",
                precursor_cn_code="2711 21 00", precursor_ratio=2.0,
                precursor_see_dir=0.20, precursor_see_indir=0.05,
                created_by=admin.id,
            ),
            CbamProductExport(
                facility_id=fac.id, year=2025, month=5, quarter="Q2",
                product_name="Clean Hydrogen Q2", cn_code="2804 10 00",
                quantity_tonnes=500.0, export_destination="EU - Germany",
                specific_embedded_direct=3.50, specific_embedded_indirect=0.25,
                created_by=admin.id,
            ),
        ])
        db.session.commit()
        admin_id, it_id, fac_id = admin.id, it_user.id, fac.id

    try:
        with app.test_client() as client:
            # Unauthenticated blocked
            assert client.get("/api/reports/cbam-validate").status_code == 401

            # IT role blocked
            _login_as(client, it_user, tenant)
            assert client.get("/api/reports/cbam-validate?year=2025").status_code == 403

            _login_as(client, admin, tenant)

            # Strict invalid quarter returns 400
            r_bad_q = client.get(f"/api/reports/cbam-validate?year=2025&quarter=Q9&facility_id={fac_id}")
            assert r_bad_q.status_code == 400
            assert client.get(f"/api/reports/cbam-export?format=xml&year=2025&quarter=BAD&facility_id={fac_id}").status_code == 400

            # Pre-export validation on Q1 returns exact 1 Q1 record & ready=True
            r_val = client.get(f"/api/reports/cbam-validate?year=2025&quarter=Q1&facility_id={fac_id}")
            assert r_val.status_code == 200
            vdata = r_val.get_json()
            assert vdata["ready"] is True
            assert vdata["quarter"] == "Q1"
            assert vdata["period_start"] == "2025-01-01"
            assert vdata["period_end"] == "2025-03-31"
            assert vdata["record_count"] == 1
            assert vdata["assurance_level"] == "Reasonable Assurance (ISO 14064-3)"
            assert vdata["summary"]["total_captured_co2_tonnes"] == 200.0
            assert len(vdata["checks"]) >= 5

            # XML filtered to Q1 contains only Q1 dates, Gross/CCS/Net, provenance, dynamic assurance, TotalPrecursorContribution (never PrecursorContribution)
            r_xml = client.get(f"/api/reports/cbam-export?format=xml&year=2025&quarter=Q1&facility_id={fac_id}")
            assert r_xml.status_code == 200
            xml_txt = r_xml.data.decode("utf-8")
            assert "<PrecursorContribution>" not in xml_txt
            assert "<TotalPrecursorContribution" in xml_txt

            root = ET.fromstring(r_xml.data)
            assert root.findtext(".//{*}PeriodStart") == "2025-01-01"
            assert root.findtext(".//{*}PeriodEnd") == "2025-03-31"
            assert root.findtext(".//{*}Quarter") == "Q1"
            assert root.findtext(".//{*}AssuranceLevel") == "Reasonable Assurance (ISO 14064-3)"
            assert root.findtext(".//{*}AssuranceProvider") == "Bureau Veritas Demo"
            assert root.findtext(".//{*}TotalPrecursorContribution") == "0.5000"
            goods = root.findall(".//{*}Good")
            assert len(goods) == 1
            g = goods[0]
            assert g.findtext(".//{*}GrossDirect") == "2.0000"  # 1.80 + 200/1000
            assert g.findtext(".//{*}CapturedCO2Reduction") == "0.2000"
            assert g.findtext(".//{*}Direct") == "1.8000"
            assert g.findtext(".//{*}HasVerifiedScope1Data") == "true"
            assert g.findtext(".//{*}HasVerifiedScope2Data") == "true"

            # Excel export for Q2 reflects Q2 period bounds
            r_xl = client.get(f"/api/reports/cbam-export?format=excel&year=2025&quarter=Q2&facility_id={fac_id}")
            assert r_xl.status_code == 200
            wb = openpyxl.load_workbook(io.BytesIO(r_xl.data))
            inst_vals = "\n".join(str(c.value) for row in wb["A_InstData"].iter_rows() for c in row if c.value is not None)
            assert "2025-04-01" in inst_vals and "2025-06-30" in inst_vals
            assert "Reasonable Assurance" in inst_vals
    finally:
        with app.app_context():
            db.session.rollback()
            if prev_meta is not None:
                m = ReportingMetadata.query.filter_by(year=2025).first()
                if m:
                    m.assurance_level, m.assurance_provider = prev_meta
            for mdl in (CbamProductExport, Emission, Scope2Emission, ProductionData):
                mdl.query.filter_by(facility_id=fac_id).delete(synchronize_session=False)
            Facility.query.filter_by(id=fac_id).delete(synchronize_session=False)
            User.query.filter(User.id.in_([admin_id, it_id])).delete(synchronize_session=False)
            db.session.commit()


def test_cbam_validate_flags_missing_ccs_and_bad_cn_code():
    tenant = f"cbam_err_{uuid.uuid4().hex[:8]}"
    with app.app_context():
        admin = User(
            email=f"cbam_err_{uuid.uuid4().hex[:8]}@example.org",
            fullName="CBAM Err Admin",
            orgName="Err Org",
            sector="Oil & Gas",
            role="admin",
            tenant_id=tenant,
            status="active",
            is_test=True,
        )
        admin.set_password("StrongPass!123")
        db.session.add(admin)
        db.session.flush()
        fac = Facility(name=f"Err Fac {uuid.uuid4().hex[:6]}", code=f"CBAMERR-{uuid.uuid4().hex[:6]}", country="Algeria", tenant_id=tenant, is_test=True)
        db.session.add(fac)
        db.session.flush()
        db.session.add(CbamProductExport(
            facility_id=fac.id, year=2025, month=3, quarter="Q1",
            product_name="Bad Record", cn_code="BAD",
            quantity_tonnes=100.0, export_destination="EU - Spain",
            specific_embedded_direct=1.0, specific_embedded_indirect=0.1,
            captured_co2_tonnes=50.0, ccs_certificate_id="",  # missing cert ID
            carbon_price_paid_eur=10.0, carbon_price_legal_ref="",  # missing Art. 9 legal ref
            is_complex_good=True, precursor_name="", precursor_cn_code="", precursor_ratio=0.0,
            created_by=admin.id,
        ))
        db.session.commit()
        admin_id, fac_id = admin.id, fac.id

    try:
        with app.test_client() as client:
            _login_as(client, admin, tenant)
            res = client.get(f"/api/reports/cbam-validate?year=2025&quarter=Q1&facility_id={fac_id}")
            assert res.status_code == 200
            body = res.get_json()
            assert body["ready"] is False
            fields = {e["field"] for e in body["errors"]}
            assert {"cn_code", "ccs_certificate_id", "carbon_price_legal_ref", "precursor"}.issubset(fields)
    finally:
        with app.app_context():
            db.session.rollback()
            CbamProductExport.query.filter_by(facility_id=fac_id).delete(synchronize_session=False)
            Facility.query.filter_by(id=fac_id).delete(synchronize_session=False)
            User.query.filter_by(id=admin_id).delete(synchronize_session=False)
            db.session.commit()
