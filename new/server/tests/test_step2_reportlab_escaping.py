import io

from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table

from app import app
from extensions import db, limiter
from models import (
    BaseYearRecalculation,
    CbamProductExport,
    Emission,
    EmissionSource,
    Facility,
    JvPartner,
    MitigationProject,
    OgmpSurvey,
    ProductionData,
    Scope2Emission,
    Scope3Emission,
    User,
)
from routes.reports import create_pdf_report
from services.master_report_appendices import (
    build_dynamic_quality_audit_elements,
    build_equipment_census_elements,
    build_facility_appendix_elements,
    build_flaring_operational_elements,
    build_gas_chromatography_elements,
    build_granular_source_ledger_elements,
    build_qaqc_uncertainty_elements,
    build_subannual_timeseries_elements,
)
from services.master_report_engine import _build_styles, generate_master_publication_pdf

XSS_FACILITY_1 = 'Fac-1 <svg onload=alert(1)> <b> & "Quote" \'Single\''
# Put '<', '<b>', and '<svg>' right across truncation boundaries (15, 18, 22, 24, 25, 26)
# so escaping BEFORE slicing splits '&lt;' into '&l' or '&a' and leaves unescaped/broken XML!
XSS_FACILITY_2 = 'PrefixTwelve1<b><svg onload="alert(1)"> & > \'End\''
XSS_LONG_PREFIX = 'A' * 14 + '<b><>&"\'<svg onload=alert(2)>'


def _extract_all_paragraph_texts(flowables) -> list[str]:
    texts = []
    for item in flowables:
        if isinstance(item, Paragraph):
            texts.append(item.getPlainText())
        elif isinstance(item, Table):
            for row in getattr(item, "_cellvalues", []):
                for cell in row:
                    if isinstance(cell, Paragraph):
                        texts.append(cell.getPlainText())
                    elif isinstance(cell, str):
                        texts.append(cell)
    return texts


def _render_flowables_to_pdf_bytes(elements) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    doc.build(list(elements))
    return buf.getvalue()


def test_all_appendix_builders_escape_before_truncating_and_render():
    styles = _build_styles()
    dummy_data = {
        "mode": "national",
        "start_year": 2024,
        "end_year": 2025,
        "facilities": [
            {"id": 1, "name": XSS_FACILITY_2, "code": "<C1&2>", "region": "<Reg&1>"},
            {"id": 2, "name": XSS_LONG_PREFIX, "code": '"C2"', "region": "'Reg2'"},
        ],
        "timeline": [
            {
                "year": 2024,
                "measured_dre_pct": 98.5,
                "flaring_intensity_pct": 0.4,
                "decree_21_330_compliant": True,
                "total_co2e_t": 1200.0,
                "gross_gas_mmsm3": 50.0,
            }
        ],
        "uncertainty": {
            "inventory_uncertainty_pct": "±5.0% <b><test&1>",
            "tier_breakdown": {"Tier 3": 80.0},
            "categories": [
                {
                    "category": "Combustion <Gas & Flare>",
                    "total_emissions": 1000.0,
                    "uncertainty_1sigma": 0.025,
                    "uncertainty_pct": "±5.0%",
                    "level": "low",
                }
            ],
        },
        "base_year_recalcs": [
            {
                "year": 2024,
                "date": "2024-06-01",
                "reason": XSS_FACILITY_1 + " <script><b>alert(1)",
                "previous_emissions_t": 1000.0,
                "adjusted_emissions_t": 1100.0,
                "delta_pct": 10.0,
                "approved_by": 'Auditor <"A&B"> <b>',
            }
        ],
        "facility_breakdowns": [
            {
                "name": XSS_FACILITY_1,
                "code": '<code>"1"&\'2\'<b>',
                "region": '<reg onclick="x()"> & <b>South',
                "timeline": [
                    {
                        "year": 2024,
                        "gross_gas_mmsm3": 10.0,
                        "liquid_mmbbl": 1.0,
                        "total_mmboe": 2.0,
                        "scope1_t": 500.0,
                        "flaring_mmsm3": 0.1,
                        "routine_mmsm3": 0.02,
                        "flaring_intensity_pct": 0.2,
                        "carbon_intensity_kg_boe": 12.0,
                    }
                ],
            }
        ],
        "equipment_census": [
            {
                "category": 'Turbine <svg onload=alert(1)> <b> & "HP"',
                "counts": {XSS_FACILITY_2: 4, XSS_LONG_PREFIX: 2},
                "total": 6,
                "notes": "Notes with <b><tag> & 'quotes' and \"double\" > signs",
            }
        ],
        "multistream_gas_chromatography": [
            {
                "stream_name": 'Header <Fuel & "Sweet"> <b> \'S1\'',
                "facility_name": 'ABCDEFGHIJKLMNOP<b onload=1><svg>',
                "carbon_content": 0.75,
                "c1": 85.0,
                "c2": 6.0,
                "c3": 3.0,
                "c4": 1.0,
                "c5": 0.5,
                "c6": 0.2,
                "c7": 0.1,
                "c8": 0.0,
                "co2": 2.0,
                "hhv_btu_scf": 1050.0,
                "mw_kg_mole": 18.2,
            }
        ],
        "flaring_operational_split": {
            "by_facility": {
                'ABCDEFGHIJKLMNOPQRSTU<b><svg>': {
                    "routine_mmsm3": 0.1,
                    "non_routine_mmsm3": 0.2,
                    "safety_mmsm3": 0.05,
                    "total_mmsm3": 0.35,
                    "measured_dre_pct": 98.0,
                    "flaring_ghg_co2e_mmt": 0.001,
                }
            },
            "total_routine_mmsm3": 0.1,
            "total_non_routine_mmsm3": 0.2,
            "total_safety_mmsm3": 0.05,
            "total_flaring_mmsm3": 0.35,
            "total_flaring_ghg_co2e_mmt": 0.001,
        },
        "dynamic_quality_audit": [
            {
                "topic": 'Calibration <svg onload=alert(1)> <b> & "ISO"',
                "observation": "Meter drift < 1.5% & 'raw' > threshold <b>",
                "recommendation": 'Inspect "<tag>" & <b>verify',
                "priority": "High",
                "statutory_ref": 'Decree <21-330> <b> & "ISO 14064-1"',
            }
        ],
        "granular_source_ledger": {
            "total_sources_count": 1,
            "ledger_by_facility": {
                'FacilityName14_<b><svg onload=alert(1)> & "X"': [
                    {
                        "source_name": '12345678901234567890123<b><svg>',
                        "module": '123456789012345678901<b>&"m"',
                        "scope": "Scope 1",
                        "quantity": 100.0,
                        "unit": '123456<b>&',
                        "co2": 200.0,
                        "ch4": 1.0,
                        "n2o": 0.1,
                        "co2e": 250.0,
                    }
                ]
            },
        },
        "subannual_time_series": {
            XSS_FACILITY_1: {
                "quarterly_rows": [
                    {
                        "co2e": 100.0,
                        "co2": 90.0,
                        "ch4": 0.3,
                        "n2o": 0.01,
                        "oil_bbl": 1000.0,
                        "gas_mscf": 5000.0,
                        "total_boe": 1800.0,
                        "intensity_co2e_boe": 0.055,
                        "energy_hhv": 1e9,
                        "daily_avg_co2e": 1.1,
                    }
                    for _ in range(4)
                ],
                "monthly_rows": [
                    {
                        "co2e": 10.0,
                        "co2": 9.0,
                        "ch4": 0.03,
                        "n2o": 0.001,
                        "oil_bbl": 100.0,
                        "total_boe": 180.0,
                        "intensity_co2e_boe": 0.055,
                        "energy_hhv": 1e8,
                        "daily_avg_co2e": 0.3,
                    }
                    for _ in range(12)
                ],
                "has_monthly_data": True,
            }
        },
    }

    for lang in ("en", "fr"):
        flowables = []
        flowables.extend(build_qaqc_uncertainty_elements(dummy_data, styles, lang=lang))
        flowables.extend(build_facility_appendix_elements(dummy_data, styles, lang=lang))
        flowables.extend(build_equipment_census_elements(dummy_data, styles, lang=lang))
        flowables.extend(build_gas_chromatography_elements(dummy_data, styles, lang=lang))
        flowables.extend(build_flaring_operational_elements(dummy_data, styles, lang=lang))
        flowables.extend(build_dynamic_quality_audit_elements(dummy_data, styles, lang=lang))
        flowables.extend(build_granular_source_ledger_elements(dummy_data, styles, lang=lang))
        flowables.extend(build_subannual_timeseries_elements(dummy_data, styles, lang=lang))

        plain_texts = _extract_all_paragraph_texts(flowables)
        joined = "\n".join(plain_texts)
        # Literal <svg onload=alert(1)> must NOT be silently eaten as an XML tag!
        assert "<svg onload=alert(1)>" in joined, "ReportLab stripped unescaped <svg> tag instead of rendering literal text"
        assert "PrefixTwelve1<b" in joined, "Facility header column must truncate first then escape safely"
        assert "&lt" not in joined and "&amp" not in joined, "Must not double-escape or slice inside XML entities"

        pdf_bytes = _render_flowables_to_pdf_bytes(flowables)
        assert pdf_bytes.startswith(b"%PDF-1.")


def test_standard_create_pdf_report_with_xml_and_xss_payloads():
    payload = 'Fac <svg onload=alert(1)> <b> & "test" \'single\' > 99 ' + ("Z" * 300)
    emissions_data = [
        {
            "scope": 1,
            "date": "2024-06-01",
            "facility_name": payload,
            "process_type": 'Combustion <tag> <b> & "quote" \'x\'',
            "fuel_type": 'Gas <script> <para> & > \'y\'',
            "amount": 1234.5,
            "unit": 'm3 <&>"\'<b>',
            "co2_emissions": 100.0,
            "ch4_emissions": 1.0,
            "n2o_emissions": 0.1,
            "total_co2e": 150.0,
        }
    ]
    filters = {
        "year": "2024",
        "division": 'Div <svg onload=alert(1)> <b> & "A"',
        "field": "Field < > & 'B'",
        "process_type": 'Proc & <tag>',
        "method": 'Method "M" <x>',
        "search": 'Search <svg onload=alert(9)> & \'q\'',
    }
    buf = create_pdf_report(emissions_data, filters)
    assert buf.getvalue().startswith(b"%PDF-1.")


def test_master_reports_all_modes_and_export_endpoints_with_xss_names(monkeypatch):
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["RATELIMIT_ENABLED"] = False
    limiter.enabled = False

    monkeypatch.setenv("AUTO_MIGRATE", "false")

    with app.app_context():
        admin = User.query.filter_by(email="xss_step2_admin@example.test").first()
        if not admin:
            admin = User(
                email="xss_step2_admin@example.test",
                fullName='Admin <svg onload=alert(1)> & "Test"',
                orgName='Operator <XSS & Co> "Demo" \'Inc\'',
                sector="Energy",
                role="admin",
                location="Basin Alpha",
                status="active",
            )
            admin.set_password("Step2-XSS-Pass!123")
            db.session.add(admin)
            db.session.flush()

        fac_xss_code = "XSS-STEP2-F1"
        fac = Facility.query.filter_by(code=fac_xss_code).first()
        if not fac:
            fac = Facility(
                name='Fac-XSS-123456<b><svg onload=alert(1)> & "Quote" \'A\'',
                code=fac_xss_code,
                region="basin_alpha",
                field='Field <A & B> "C"',
                division='Div <1> & \'2\'',
                location="Basin Alpha",
                segment="Upstream",
            )
            db.session.add(fac)
            db.session.flush()

        partner = JvPartner.query.filter_by(code="JVXSS").first()
        if not partner:
            partner = JvPartner(
                name='JV <Partner> <b> & "Test"',
                code="JVXSS",
                is_operator=False,
            )
            db.session.add(partner)
            db.session.flush()

        if not Emission.query.filter_by(record_id="xss-step2-em-1").first():
            db.session.add(
                Emission(
                    record_id="xss-step2-em-1",
                    facility_id=fac.id,
                    created_by=admin.id,
                    year=2024,
                    month=6,
                    process_type="stationary_combustion",
                    fuel_type='Gas <Fuel> <b> & "Sweet"',
                    quantity=1000.0,
                    unit="m3",
                    co2_emissions=200.0,
                    ch4_emissions=0.5,
                    n2o_emissions=0.05,
                    co2e_total=225.0,
                    status="Verified",
                    equipment_id='EQ-123456789012345678901<b><svg onload=x()>',
                    group_name='Grp <A & B> "G"',
                )
            )

        if not ProductionData.query.filter_by(facility_id=fac.id, year=2024, month=6).first():
            db.session.add(
                ProductionData(
                    facility_id=fac.id,
                    year=2024,
                    month=6,
                    oil_amount=5000.0,
                    gas_amount=15000.0,
                    gross_gas_mmsm3=10.0,
                    crude_oil_mmboe=0.03,
                    total_production_mmboe=0.05,
                )
            )

        if not EmissionSource.query.filter_by(facility_id=fac.id, name='12345678901234567890123<b><svg>').first():
            db.session.add(
                EmissionSource(
                    facility_id=fac.id,
                    name='12345678901234567890123<b><svg>',
                    type='Turbine <T> <b> & "X"',
                    status="Active",
                )
            )

        if not Scope2Emission.query.filter_by(facility_id=fac.id, year=2024, month=6).first():
            db.session.add(
                Scope2Emission(
                    facility_id=fac.id,
                    created_by=admin.id,
                    year=2024,
                    month=6,
                    source_type="electricity",
                    electricity_kwh=1000.0,
                    emission_factor=0.5,
                    co2e=0.5,
                    status="Verified",
                    grid_region='Grid <R> <b> & "1"',
                )
            )

        # Slice boundary tests at index 24 and 26 where '&lt;' would be split if pre-escaped in master_report_data!
        if not Scope3Emission.query.filter_by(facility_id=fac.id, year=2024, month=6).first():
            db.session.add(
                Scope3Emission(
                    facility_id=fac.id,
                    created_by=admin.id,
                    year=2024,
                    month=6,
                    category='123456789012345678901234<b><svg onload=alert(1)>',
                    sub_category='1234567890123456789012<b>&"s"',
                    activity_data=100.0,
                    unit='unit<>1234&"u"',
                    emission_factor=0.1,
                    co2e=10.0,
                    status="Verified",
                )
            )

        if not OgmpSurvey.query.filter_by(facility_id=fac.id, year=2024).first():
            db.session.add(
                OgmpSurvey(
                    facility_id=fac.id,
                    year=2024,
                    survey_type='1234567890123456789012<b><svg>',
                    instrument_vendor='123456789012345678<b>&"v"',
                    survey_date="2024-07-01",
                    measured_rate_kg_hr=10.0,
                    estimated_annual_tch4=87.6,
                    bottom_up_tch4=90.0,
                    variance_pct=-2.7,
                )
            )

        if not CbamProductExport.query.filter_by(facility_id=fac.id, year=2024).first():
            db.session.add(
                CbamProductExport(
                    facility_id=fac.id,
                    year=2024,
                    product_name='123456789012345678901<b><svg>&"p"',
                    cn_code="2709 00",
                    quantity_tonnes=1000.0,
                    specific_embedded_direct=0.05,
                    specific_embedded_indirect=0.01,
                    export_destination='1234567890123456789<EU>&"d"',
                )
            )

        if not MitigationProject.query.filter_by(facility_id=fac.id, year=2024).first():
            db.session.add(
                MitigationProject(
                    facility_id=fac.id,
                    year=2024,
                    name='123456789012345678901234<b><svg>',
                    project_type="efficiency",
                    quantity_tco2e=500.0,
                    investment_amount=10000.0,
                    status="Active",
                )
            )

        if not BaseYearRecalculation.query.filter_by(year=2024, reason='Recalc <b><svg onload=1> & "Reason"').first():
            db.session.add(
                BaseYearRecalculation(
                    year=2024,
                    reason='Recalc <b><svg onload=1> & "Reason"',
                    previous_emissions=1000.0,
                    adjusted_emissions=1100.0,
                    approved_by=admin.id,
                )
            )

        db.session.commit()

        try:
            for lang in ("en", "fr"):
                for mode, reg in (("national", "national"), ("regional", "basin_alpha"), ("comparison", None)):
                    pdf_buf = generate_master_publication_pdf(
                        mode=mode,
                        region_key=reg,
                        start_year=2024,
                        end_year=2024,
                        allowed_facility_ids=[fac.id],
                        language=lang,
                    )
                    assert pdf_buf.getvalue().startswith(b"%PDF-1."), f"Master report {mode}/{lang} did not produce valid PDF"

            with app.test_client() as c:
                assert c.post("/api/auth/login", json={"email": "xss_step2_admin@example.test", "password": "Step2-XSS-Pass!123"}).status_code == 200
                r_exp = c.get(f"/api/reports/export?format=pdf&facility_id={fac.id}&year=2024")
                assert r_exp.status_code == 200 and r_exp.data.startswith(b"%PDF-1.")

                r_gen = c.post("/api/reports/generate", json={"filters": {"facility_id": fac.id, "year": 2024}})
                assert r_gen.status_code == 200 and r_gen.data.startswith(b"%PDF-1.")

                r_nat = c.get(f"/api/reports/national-inventory-export?facility_id={fac.id}&year=2024")
                assert r_nat.status_code == 200

                r_ogmp = c.get(f"/api/reports/ogmp-export?facility_id={fac.id}&year=2024")
                assert r_ogmp.status_code == 200

                r_cbam_xl = c.get(f"/api/reports/cbam-export?format=excel&facility_id={fac.id}&year=2024")
                assert r_cbam_xl.status_code == 200

                r_cbam_xml = c.get(f"/api/reports/cbam-export?format=xml&facility_id={fac.id}&year=2024")
                assert r_cbam_xml.status_code == 200

                r_bench = c.post("/api/reports/master-report/benchmark-excel", json={"start_year": 2024, "end_year": 2024})
                assert r_bench.status_code == 200
        finally:
            BaseYearRecalculation.query.filter_by(year=2024, reason='Recalc <b><svg onload=1> & "Reason"').delete()
            MitigationProject.query.filter_by(facility_id=fac.id).delete()
            CbamProductExport.query.filter_by(facility_id=fac.id).delete()
            OgmpSurvey.query.filter_by(facility_id=fac.id).delete()
            Scope3Emission.query.filter_by(facility_id=fac.id).delete()
            Scope2Emission.query.filter_by(facility_id=fac.id).delete()
            EmissionSource.query.filter_by(facility_id=fac.id).delete()
            ProductionData.query.filter_by(facility_id=fac.id).delete()
            Emission.query.filter_by(facility_id=fac.id).delete()
            JvPartner.query.filter_by(code="JVXSS").delete()
            Facility.query.filter_by(id=fac.id).delete()
            User.query.filter_by(email="xss_step2_admin@example.test").delete()
            db.session.commit()
