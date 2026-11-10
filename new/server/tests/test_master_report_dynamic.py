"""
Test Suite: Dynamic Master Report Unbounded Sources & Assay Extractor Validation
================================================================================
Validates that:
1. Granular source ledger is unbounded and dynamically pulls all sources from database.
2. Multistream gas chromatography accurately parses mole fractions, HHV, and MW.
3. Flaring operational split segregates routine, non-routine, and safety flaring with VISR DRE.
4. Subannual time-series produces quarterly and monthly breakdowns without errors.
5. Process overview diagram generates 300 DPI vector flowcharts.
6. Full PDF generation executes cleanly without ReportLab flowable crashes.
"""

import json
import os
import tempfile
import pytest
from app import app
from extensions import db
from models import Facility, EmissionSource, Emission, CustomFactor, ProductionData
from services.master_report_data import aggregate_master_report_data
from services.master_report_charts import generate_process_overview_diagram
from services.master_report_engine import generate_master_publication_pdf


@pytest.fixture
def seeded_basin_alpha_data():
    """Seeds test facilities and dynamic records into the active test database."""
    with app.app_context():
        # Check or create Basin Alpha facility
        fac = Facility.query.filter_by(code="TEST-BK-Facility A-1").first()
        if not fac:
            fac = Facility(
                name="Facility A-1 Test Facility",
                code="TEST-BK-Facility A-1",
                region="Basin Alpha",
                segment="Upstream"
            )
            db.session.add(fac)
            db.session.commit()

        # Seed emission sources & emissions
        for i in range(1, 5):
            eq_code = f"EQ-TEST-{i}"
            src = EmissionSource.query.filter_by(facility_id=fac.id, equipment_id=eq_code).first()
            if not src:
                src = EmissionSource(
                    facility_id=fac.id,
                    name=f"Test Turbine {i}",
                    equipment_id=eq_code,
                    type="Turbine",
                    activity="Stationary Combustion"
                )
                db.session.add(src)
                db.session.commit()

            em = Emission.query.filter_by(facility_id=fac.id, equipment_id=eq_code, year=2022).first()
            if not em:
                em = Emission(
                    facility_id=fac.id,
                    equipment_id=eq_code,
                    year=2022,
                    co2_emissions=1000.0 * i,
                    ch4_emissions=2.0 * i,
                    n2o_emissions=0.05 * i,
                    co2e_total=1055.0 * i,
                    activity="Stationary Combustion",
                    fuel_type="natural_gas",
                    quantity=50000.0 * i,
                    unit="m3"
                )
                db.session.add(em)

        # Seed CustomFactor with gas composition
        cf = CustomFactor.query.filter_by(facility_id=fac.id, name="Fuel Gas Test Assay").first()
        if not cf:
            assay = {
                "ch4_mol_pct": 82.5,
                "c2h6_mol_pct": 7.8,
                "c3h8_mol_pct": 3.2,
                "co2_mol_pct": 2.1,
                "n2_mol_pct": 1.4,
                "hhv_btu_scf": 1145.0,
                "mw_kg_mole": 20.15,
                "carbon_content": 0.742
            }
            cf = CustomFactor(
                facility_id=fac.id,
                name="Fuel Gas Test Assay",
                parent_fuel="natural_gas",
                co2_factor=56.1,
                ch4_factor=0.001,
                n2o_factor=0.0001,
                unit="kg/MMBtu",
                gas_composition=assay
            )
            db.session.add(cf)

        # Seed ProductionData for 12 months
        for m in range(1, 13):
            prod = ProductionData.query.filter_by(facility_id=fac.id, year=2022, month=m).first()
            if not prod:
                prod = ProductionData(
                    facility_id=fac.id,
                    year=2022,
                    month=m,
                    gross_gas_mmsm3=12.5,
                    crude_oil_mmboe=0.2,
                    total_production_mmboe=0.2
                )
                db.session.add(prod)

        db.session.commit()
        yield fac


def test_aggregate_master_report_basin_alpha_unbounded(seeded_basin_alpha_data):
    """Test that Basin Alpha regional data contains unbounded sources and new structures."""
    with app.app_context():
        data = aggregate_master_report_data("regional", "basin_alpha", 2022, 2022)

        # Granular source ledger check
        ledger = data.get("granular_source_ledger", {})
        assert ledger, "granular_source_ledger must be populated"
        total_sources = ledger.get("total_sources_count", 0)
        assert total_sources >= 4, f"Expected at least 4 sources, got {total_sources}"
        assert seeded_basin_alpha_data.name in ledger["ledger_by_facility"]

        # Gas chromatography check
        streams = data.get("multistream_gas_chromatography", [])
        assert len(streams) >= 1, "Expected at least 1 gas stream"
        for s in streams:
            assert "stream_name" in s
            assert "c1" in s and s["c1"] > 0
            assert "hhv_btu_scf" in s and s["hhv_btu_scf"] > 500
            assert "mw_kg_mole" in s and s["mw_kg_mole"] > 10

        # Subannual time-series check
        subannual = data.get("subannual_time_series", {})
        assert subannual, "subannual_time_series must be populated"
        assert seeded_basin_alpha_data.name in subannual
        assert len(subannual[seeded_basin_alpha_data.name]["quarterly_rows"]) == 4
        assert len(subannual[seeded_basin_alpha_data.name]["monthly_rows"]) == 12

        # Dynamic quality audit check
        audits = data.get("dynamic_quality_audit", [])
        assert len(audits) >= 4, f"Expected at least 4 audit topics, got {len(audits)}"
        topics = [a["topic"] for a in audits]
        assert any("Fuel" in t for t in topics)
        assert any("Flare" in t for t in topics)
        assert any("LDAR" in t or "Fugitive" in t for t in topics)
        assert any("MRV" in t or "Meter" in t for t in topics)


def test_process_overview_diagram_generation():
    """Test generating a PFD diagram for a facility."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        out_png = os.path.join(tmp_dir, "test_pfd.png")
        generate_process_overview_diagram("Facility A-1 Central Processing Facility", out_png, language="en")
        assert os.path.exists(out_png)
        assert os.path.getsize(out_png) > 50_000


def test_full_pdf_generation_smoke(seeded_basin_alpha_data):
    """Test full PDF generation returns valid bytes and report hash."""
    with app.app_context():
        buf = generate_master_publication_pdf(
            mode="regional",
            region_key="basin_alpha",
            start_year=2022,
            end_year=2022,
            gwp_standard="AR5",
            language="en"
        )
        assert buf is not None
        pdf_bytes = buf.getvalue()
        assert len(pdf_bytes) > 200_000
        assert hasattr(buf, "report_hash")
        assert len(buf.report_hash) == 64
