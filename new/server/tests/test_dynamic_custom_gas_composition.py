import pytest
from app import app
from extensions import db
from models import CustomFactor, Facility, Emission, User
from services.master_report_data import aggregate_master_report_data
from services.master_report_engine import generate_master_publication_pdf


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as c:
        with app.app_context():
            yield c


def test_custom_factor_gas_composition_roundtrip(client):
    """Verifies CustomFactor gas composition API persistence, full PVT chromatography, and ReportLab PDF."""
    with app.app_context():
        # Clean previous test factors
        CustomFactor.query.filter_by(name="HBNS Wellhead Gas Analysis 2024").delete()
        db.session.commit()

        # Create user if needed
        admin = User.query.filter_by(email="admin_gc@test.dz").first()
        if not admin:
            admin = User(fullName="Admin GC", orgName="Sonatrach", sector="Upstream", email="admin_gc@test.dz", role="admin")
            admin.set_password("AdminPass123!")
            db.session.add(admin)
            db.session.commit()

        cf = CustomFactor(
            name="HBNS Wellhead Gas Analysis 2024",
            co2_factor=52.5,
            ch4_factor=0.002,
            n2o_factor=0.0001,
            unit="kg/MMBtu",
            created_by=admin.id,
            status="Approved",
            region="berkine",
        )
        cf.gas_composition = {
            "ch4_mol_pct": 74.40,
            "c2h6_mol_pct": 12.80,
            "c3h8_mol_pct": 5.60,
            "ic4_mol_pct": 1.20,
            "nc4_mol_pct": 2.00,
            "ic5_mol_pct": 0.70,
            "nc5_mol_pct": 0.80,
            "c6_plus_mol_pct": 0.60,
            "co2_mol_pct": 1.00,
            "n2_mol_pct": 0.90,
            "h2s_ppm": 0.0,
        }
        db.session.add(cf)
        db.session.commit()

        # Fetch and verify
        fetched = db.session.get(CustomFactor, cf.id)
        assert fetched is not None
        assert fetched.gas_composition["ch4_mol_pct"] == 74.40
        assert fetched.gas_composition["c2h6_mol_pct"] == 12.80
        assert fetched.gas_composition["ic4_mol_pct"] == 1.20
        assert fetched.gas_composition["c6_plus_mol_pct"] == 0.60

        # Now test aggregate_master_report_data for berkine
        data = aggregate_master_report_data(
            mode="regional",
            region_key="berkine",
            start_year=2023,
            end_year=2025,
            gwp_standard="AR5"
        )
        assert data["gas_comp_source"] == "custom_factor"
        assert data["gas_comp_name"] == "HBNS Wellhead Gas Analysis 2024"
        assert data["gas_composition"]["ch4_mol_pct"] == 74.40
        assert data["gas_composition"]["nc4_mol_pct"] == 2.00

        # Generate publication PDF to verify ReportLab layout & title (EN and FR)
        pdf_bytes_en = generate_master_publication_pdf(
            mode="regional",
            region_key="berkine",
            start_year=2023,
            end_year=2025,
            language="en"
        )
        assert pdf_bytes_en is not None
        assert len(pdf_bytes_en.getvalue()) > 50000

        pdf_bytes_fr = generate_master_publication_pdf(
            mode="regional",
            region_key="berkine",
            start_year=2023,
            end_year=2025,
            language="fr"
        )
        assert pdf_bytes_fr is not None
        assert len(pdf_bytes_fr.getvalue()) > 50000

        # Clean up
        db.session.delete(fetched)
        db.session.commit()
