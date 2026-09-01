import sys
import os
import random
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app
from extensions import db
from models import (
    User,
    Facility,
    ProductionData,
    Emission,
    Scope2Emission,
    Scope3Emission,
    MitigationProject,
    MethaneSourceType,
    SbtiTarget,
    BaseYear,
    SystemSetting,
)

# Standard Facilities across Algerian Oil & Gas assets
FACILITIES_SPEC = [
    {
        "name": "ADR - Adrar Refined & Gas Complex",
        "location": "Adrar",
        "region": "ADR",
        "division": "Raffinage",
        "activity": "Downstream",
        "field": "Raffinerie",
        "code": "FAC-ADR",
        "segment": "Downstream",
        "latitude": 27.8744,
        "longitude": -0.2939,
    },
    {
        "name": "REB - Rhourde El Baguel Processing Facility",
        "location": "Ouargla",
        "region": "REB",
        "division": "Exploration & Production",
        "activity": "Upstream",
        "field": "OF",
        "code": "FAC-REB",
        "segment": "Upstream",
        "latitude": 31.8500,
        "longitude": 5.5500,
    },
    {
        "name": "HBK - Haoud Berkaoui Field",
        "location": "Ouargla",
        "region": "HBK",
        "division": "Exploration & Production",
        "activity": "Upstream",
        "field": "OF",
        "code": "FAC-HBK",
        "segment": "Upstream",
        "latitude": 31.9000,
        "longitude": 5.3000,
    },
    {
        "name": "GTL - Gas-to-Liquids Facility",
        "location": "In Salah",
        "region": "GTL",
        "division": "Petrochimie",
        "activity": "Downstream",
        "field": "Pétrochimie",
        "code": "FAC-GTL",
        "segment": "Downstream",
        "latitude": 27.2000,
        "longitude": 2.4667,
    },
    {
        "name": "OHT - Oued Noumer Terminal",
        "location": "Ghardaia",
        "region": "OHT",
        "division": "Transport",
        "activity": "Midstream",
        "field": "GF",
        "code": "FAC-OHT",
        "segment": "Midstream",
        "latitude": 32.4900,
        "longitude": 3.6700,
    },
    {
        "name": "STAH - Stah Gas Gathering Station",
        "location": "Illizi",
        "region": "STAH",
        "division": "Exploration & Production",
        "activity": "Upstream",
        "field": "GF",
        "code": "FAC-STAH",
        "segment": "Upstream",
        "latitude": 28.5000,
        "longitude": 8.7000,
    },
    {
        "name": "TFT - Tin Fouye Tabankort Gas Hub",
        "location": "Illizi",
        "region": "TFT",
        "division": "Exploration & Production",
        "activity": "Upstream",
        "field": "GF",
        "code": "FAC-TFT",
        "segment": "Upstream",
        "latitude": 28.8000,
        "longitude": 7.9000,
    },
    {
        "name": "HMD - Hassi Messaoud Production Center",
        "location": "Ouargla",
        "region": "HMD",
        "division": "Exploration & Production",
        "activity": "Upstream",
        "field": "OF",
        "code": "FAC-HMD",
        "segment": "Upstream",
        "latitude": 31.6800,
        "longitude": 6.0700,
    },
    {
        "name": "RNS - Rhourde Nouss Processing Plant",
        "location": "Illizi",
        "region": "RNS",
        "division": "Exploration & Production",
        "activity": "Upstream",
        "field": "GF",
        "code": "FAC-RNS",
        "segment": "Upstream",
        "latitude": 29.8000,
        "longitude": 6.7000,
    },
    {
        "name": "BRS - Bir Sebaa Treatment Facility",
        "location": "Touggourt",
        "region": "BRS",
        "division": "Exploration & Production",
        "activity": "Upstream",
        "field": "OF",
        "code": "FAC-BRS",
        "segment": "Upstream",
        "latitude": 32.9000,
        "longitude": 6.1000,
    },
    {
        "name": "MLN - Menzel Ledjmet North",
        "location": "Ouargla",
        "region": "MLN",
        "division": "Exploration & Production",
        "activity": "Upstream",
        "field": "OF",
        "code": "FAC-MLN",
        "segment": "Upstream",
        "latitude": 31.4000,
        "longitude": 7.8000,
    },
    {
        "name": "OURHOUD - Ourhoud Central Processing Facility",
        "location": "Ouargla",
        "region": "OURHOUD",
        "division": "Exploration & Production",
        "activity": "Upstream",
        "field": "OF",
        "code": "FAC-OURHOUD",
        "segment": "Upstream",
        "latitude": 31.5500,
        "longitude": 6.9000,
    },
]

OGMP_SOURCES = [
    {"code": "PNEUMATIC_DEVICE", "name": "Pneumatic Controllers & Pumps", "category": "vented", "default_ef_reference": "API Compendium Table 5-15", "default_level": 3},
    {"code": "COMPRESSOR_SEAL", "name": "Compressor Seals & Packings", "category": "vented", "default_ef_reference": "API Compendium Table 5-9", "default_level": 3},
    {"code": "TANK_VENTING", "name": "Atmospheric Storage Tanks", "category": "vented", "default_ef_reference": "API Compendium Table 5-12", "default_level": 3},
    {"code": "FLARE_UNCOMBUSTED", "name": "Flaring Incomplete Combustion", "category": "flaring", "default_ef_reference": "API Compendium Table 4-1", "default_level": 3},
    {"code": "FUGITIVE_VALVE", "name": "Fugitive Valve & Flange Leaks", "category": "fugitive", "default_ef_reference": "API Compendium Table 6-1", "default_level": 3},
]

def restore_data():
    with app.app_context():
        db.create_all()
        random.seed(42)

        # 1. Ensure user a@a and admin users exist
        user = User.query.filter_by(email="a@a").first()
        if not user:
            user = User(
                fullName="Admin User",
                orgName="Sonatrach Operations",
                email="a@a",
                role="admin",
                sector="Oil & Gas",
                department="Sustainability & Carbon Management",
                jobTitle="Sustainability Director",
                location="Global",
                status="active"
            )
            user.set_password("a")
            db.session.add(user)
            db.session.commit()

        # 2. Seed OGMP Source Types
        for og in OGMP_SOURCES:
            existing = MethaneSourceType.query.filter_by(code=og["code"]).first()
            if not existing:
                src = MethaneSourceType(
                    code=og["code"],
                    name=og["name"],
                    category=og["category"],
                    default_ef_reference=og["default_ef_reference"],
                    default_level=og["default_level"]
                )
                db.session.add(src)
        db.session.commit()

        # 3. Seed Facilities
        facilities_map = {}
        for spec in FACILITIES_SPEC:
            fac = Facility.query.filter_by(code=spec["code"]).first()
            if not fac:
                fac = Facility(
                    name=spec["name"],
                    location=spec["location"],
                    region=spec["region"],
                    division=spec["division"],
                    activity=spec["activity"],
                    field=spec["field"],
                    code=spec["code"],
                    segment=spec["segment"],
                    country="Algeria",
                    ogmp_membership_year=2023,
                    reconciliation_threshold=20.0,
                    latitude=spec["latitude"],
                    longitude=spec["longitude"],
                    created_by=user.id,
                )
                db.session.add(fac)
                db.session.commit()
            facilities_map[spec["region"]] = fac

        # 4. Clean existing emissions to repopulate complete operational history
        Emission.query.delete()
        Scope2Emission.query.delete()
        Scope3Emission.query.delete()
        ProductionData.query.delete()
        MitigationProject.query.delete()
        db.session.commit()

        years = [2022, 2023, 2024]
        processes = [
            ("combustion", "Natural Gas", "scf", 0.054, 0.0001, 0.00001, 1000000),
            ("flaring", "Natural Gas", "scf", 0.060, 0.0012, 0.00005, 500000),
            ("venting", "Natural Gas", "scf", 0.010, 0.0180, 0.0, 300000),
            ("pneumatic_device", "Natural Gas", "devices", 0.0, 50.0, 0.0, 20),
            ("fugitives_equipment", "Natural Gas", "components", 0.0, 15.0, 0.0, 150),
            ("tank_flashing", "Crude Oil", "bbl", 0.005, 0.025, 0.0, 40000),
            ("blowdown", "Natural Gas", "events", 0.0, 250.0, 0.0, 8),
            ("dehydrator", "Natural Gas", "m3", 0.002, 0.015, 0.0, 200000),
        ]

        # 5. Populate Monthly Scope 1 Emissions & Production Data (2022 - 2024)
        for yr in years:
            for m in range(1, 13):
                for region_code, fac in facilities_map.items():
                    # Production Data
                    oil_bbl = random.randint(30000, 150000)
                    gas_mscf = random.randint(50000, 300000)
                    p_data = ProductionData(
                        facility_id=fac.id,
                        month=m,
                        year=yr,
                        oil_amount=oil_bbl,
                        gas_amount=gas_mscf,
                        oil_unit="bbl",
                        gas_unit="mscf",
                        activity=fac.activity,
                        division=fac.division,
                        region=fac.region,
                        field=fac.field,
                        created_by=user.id,
                    )
                    db.session.add(p_data)

                    # Scope 1 Emissions
                    for proc, fuel, unit, ef_co2, ef_ch4, ef_n2o, base_qty in processes:
                        qty = base_qty * random.uniform(0.85, 1.25)
                        co2 = qty * ef_co2
                        ch4 = qty * ef_ch4
                        n2o = qty * ef_n2o
                        # AR5 GWP: CO2=1, CH4=28, N2O=265
                        co2e = co2 * 1.0 + ch4 * 28.0 + n2o * 265.0

                        em = Emission(
                            record_id=str(uuid.uuid4()),
                            facility_id=fac.id,
                            year=yr,
                            month=m,
                            process_type=proc,
                            fuel_type=fuel,
                            quantity=round(qty, 2),
                            unit=unit,
                            co2_emissions=round(co2, 2),
                            ch4_emissions=round(ch4, 2),
                            n2o_emissions=round(n2o, 2),
                            co2e_total=round(co2e, 2),
                            calc_method="ef_facility_specific",
                            gwp_version="AR5",
                            status="Verified",
                            activity=fac.activity,
                            division=fac.division,
                            region=fac.region,
                            field=fac.field,
                            created_by=user.id,
                            approved_by=user.id,
                            approved_at=datetime.now(timezone.utc),
                        )
                        db.session.add(em)

                    # Scope 2 Emissions (Electricity & Steam)
                    kwh = random.randint(80000, 450000)
                    # Algerian grid factor ~0.55 kgCO2e/kWh = 0.00055 tCO2e/kWh
                    s2_co2e = kwh * 0.00055
                    s2 = Scope2Emission(
                        facility_id=fac.id,
                        year=yr,
                        month=m,
                        source_type="electricity",
                        electricity_kwh=kwh,
                        grid_region="Algerian National Grid",
                        location=fac.location,
                        activity=fac.activity,
                        division=fac.division,
                        region=fac.region,
                        field=fac.field,
                        co2e=round(s2_co2e, 2),
                        emission_factor=0.55,
                        status="Verified",
                        created_by=user.id,
                        approved_by=user.id,
                        approved_at=datetime.now(timezone.utc),
                    )
                    db.session.add(s2)

                    # Scope 3 Emissions (Purchased Goods, Capital Goods, Transport, Use of Sold Products)
                    s3_categories = [
                        ("1", "Purchased Goods & Services", "Steel pipes, valves & chemicals", random.randint(20000, 80000), "kg", 1.8),
                        ("2", "Capital Goods", "Heavy machinery & compressors", random.randint(10000, 50000), "USD", 0.45),
                        ("4", "Upstream Transportation", "Pipeline transport & shipping", random.randint(15000, 60000), "tkm", 0.12),
                        ("6", "Business Travel", "Domestic & International flights", random.randint(5000, 25000), "passenger-km", 0.15),
                        ("11", "Use of Sold Products", "Combustion of crude oil & gas exports", random.randint(50000, 200000), "bbl", 0.43),
                    ]
                    for cat_id, cat_name, desc, amount, unit, ef in s3_categories:
                        s3_co2e = amount * ef / 1000.0 if unit != "bbl" else amount * ef
                        s3 = Scope3Emission(
                            facility_id=fac.id,
                            year=yr,
                            month=m,
                            category=cat_id,
                            sub_category=cat_name,
                            notes=desc,
                            activity_data=amount,
                            unit=unit,
                            emission_factor=ef,
                            co2e=round(s3_co2e, 2),
                            calculation_method="Spend-based / Physical Allocation",
                            status="Verified",
                            created_by=user.id,
                            approved_by=user.id,
                            approved_at=datetime.now(timezone.utc),
                        )
                        db.session.add(s3)

        # 6. Mitigation Projects
        projects = [
            ("Flare Gas Recovery Unit (FGRU)", "flaring_reduction", "completed", 2023, 185000, 4500000),
            ("LDAR Optical Gas Imaging (OGI) Program", "fugitive_reduction", "active", 2024, 65000, 850000),
            ("Solar Hybrid Microgrid Integration", "renewable", "active", 2024, 42000, 3200000),
            ("Zero-Bleed Pneumatic Controllers Retrofit", "efficiency", "planned", 2024, 28000, 600000),
        ]
        for name, p_type, status, yr, reduction, cost in projects:
            p = MitigationProject(
                facility_id=facilities_map["HMD"].id,
                name=name,
                project_type=p_type,
                status=status,
                year=yr,
                quantity_tco2e=reduction,
                investment_amount=cost,
                description="Facility Decarbonization Initiative",
                created_by=user.id,
            )
            db.session.add(p)

        # 7. Base Year & SBTi Target (1.5°C Pathway)
        base = BaseYear.query.first()
        if not base:
            base = BaseYear(
                id=1,
                year=2022,
                locked=1,
            )
            db.session.add(base)

        sbti = SbtiTarget.query.first()
        if not sbti:
            sbti = SbtiTarget(
                base_year=2022,
                base_year_emissions=17350000.0,
                target_year=2050,
                reduction_rate_pct=4.2,
                pathway_type="1.5C",
                created_by=user.id,
            )
            db.session.add(sbti)

        db.session.commit()
        print("[SUCCESS] All operational data, facilities, Scope 1, 2, 3 emissions, production data, and SBTi targets restored successfully for user 'a@a'!")

if __name__ == "__main__":
    restore_data()
