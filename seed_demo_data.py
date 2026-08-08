import sys
import os
import uuid

# Add server directory to path
sys.path.insert(0, os.path.abspath(r'c:\Users\samsung\Desktop\H2\new\server'))

from app import app
from extensions import db
from models import User, Facility, Emission, Scope2Emission, Scope3Emission

def seed_data():
    with app.app_context():
        db.create_all()

        user = User.query.filter_by(email='a').first()
        if not user:
            print("Admin user 'a' not found. Creating...")
            user = User(
                fullName='Admin User',
                orgName='Carbon Tech Algeria',
                email='a',
                role='admin',
                sector='Industrial Decarbonization & CBAM',
                department='Engineering & Sustainability',
                jobTitle='Lead Carbon Auditor',
                location='Algiers',
                status='active'
            )
            user.set_password('a')
            db.session.add(user)
            db.session.commit()

        # Clean existing test emissions
        Emission.query.delete()
        Scope2Emission.query.delete()
        Scope3Emission.query.delete()
        Facility.query.delete()
        db.session.commit()

        facilities_data = [
            {
                "name": "Complexe Sidérurgique DRI/EAF (Tosyali)",
                "location": "Bethioua, Oran",
                "activity": "Steel & Iron (Acier DRI)",
                "division": "Metallurgy",
                "region": "West",
                "field": "Industrial Zone",
                "code": "STL-TOS-01",
                "segment": "Heavy Industry"
            },
            {
                "name": "Complexe Ammoniac & Engrais Azotés (Fertial)",
                "location": "Arzew, Oran",
                "activity": "Chemicals & Fertilizers",
                "division": "Petrochemicals",
                "region": "West",
                "field": "Arzew Port",
                "code": "FERT-ARZ-01",
                "segment": "Heavy Industry"
            },
            {
                "name": "Cimenterie Industrielle de Chlef (GICA)",
                "location": "Chlef",
                "activity": "Cement & Clinker",
                "division": "Building Materials",
                "region": "Center",
                "field": "Chlef Plant",
                "code": "CIM-GIC-01",
                "segment": "Heavy Industry"
            },
            {
                "name": "Centre de Traitement Gazier Hassi Messaoud (Sonatrach)",
                "location": "Hassi Messaoud, Ouargla",
                "activity": "Upstream & Midstream Gas",
                "division": "Exploration & Production",
                "region": "South",
                "field": "HMD Field",
                "code": "GAS-HMD-01",
                "segment": "Oil & Gas"
            }
        ]

        facilities = []
        for f_data in facilities_data:
            fac = Facility(
                name=f_data["name"],
                location=f_data["location"],
                activity=f_data["activity"],
                division=f_data["division"],
                region=f_data["region"],
                field=f_data["field"],
                code=f_data["code"],
                segment=f_data["segment"],
                created_by=user.id
            )
            db.session.add(fac)
            facilities.append(fac)
        db.session.commit()

        # Seed sample emissions records with realistic Tier 3 numbers
        records = [
            # Tosyali Steel
            {"facility": facilities[0], "year": 2026, "month": 1, "proc": "Stationary Combustion", "fuel": "Natural Gas DRI", "qty": 500000.0, "unit": "m3", "co2": 45000.0, "ch4": 12.5, "n2o": 2.1, "co2e": 45350.0, "method": "ef_facility_specific"},
            {"facility": facilities[0], "year": 2026, "month": 2, "proc": "Stoichiometry", "fuel": "Carbon Electrodes EAF", "qty": 12000.0, "unit": "tonnes", "co2": 28000.0, "ch4": 5.0, "n2o": 1.2, "co2e": 28150.0, "method": "direct_measurement"},
            
            # Fertial Ammonia
            {"facility": facilities[1], "year": 2026, "month": 1, "proc": "Steam Methane Reforming", "fuel": "Feedstock Gas", "qty": 650000.0, "unit": "m3", "co2": 52000.0, "ch4": 8.0, "n2o": 1.5, "co2e": 52250.0, "method": "engineering_estimate"},
            {"facility": facilities[1], "year": 2026, "month": 2, "proc": "Vented Tail Gas", "fuel": "N2O Abatement", "qty": 45.0, "unit": "tonnes", "co2": 1500.0, "ch4": 0.0, "n2o": 45.0, "co2e": 13425.0, "method": "direct_measurement"},
            
            # GICA Cement
            {"facility": facilities[2], "year": 2026, "month": 1, "proc": "Calcination Process", "fuel": "Limestone (CaCO3)", "qty": 75000.0, "unit": "tonnes", "co2": 38500.0, "ch4": 0.0, "n2o": 0.0, "co2e": 38500.0, "method": "ef_facility_specific"},
            {"facility": facilities[2], "year": 2026, "month": 1, "proc": "Stationary Combustion", "fuel": "Natural Gas Kiln", "qty": 210000.0, "unit": "m3", "co2": 18200.0, "ch4": 3.2, "n2o": 0.8, "co2e": 18320.0, "method": "ef_facility_specific"},

            # Sonatrach Gas
            {"facility": facilities[3], "year": 2026, "month": 1, "proc": "AGR Acid Gas Removal", "fuel": "Amine Flash", "qty": 350000.0, "unit": "m3", "co2": 31000.0, "ch4": 15.0, "n2o": 0.0, "co2e": 31420.0, "method": "engineering_estimate"},
            {"facility": facilities[3], "year": 2026, "month": 1, "proc": "Flaring", "fuel": "High Pressure Flare Gas", "qty": 180000.0, "unit": "m3", "co2": 22000.0, "ch4": 85.0, "n2o": 0.5, "co2e": 24400.0, "method": "ef_facility_specific"},
            {"facility": facilities[3], "year": 2026, "month": 1, "proc": "Compressor Fugitive", "fuel": "Wet Seal Methane", "qty": 110.0, "unit": "kg", "co2": 0.0, "ch4": 110.0, "n2o": 0.0, "co2e": 3080.0, "method": "direct_measurement"}
        ]

        for i, r in enumerate(records):
            em = Emission(
                record_id=f"REC-2026-{i+1:04d}",
                facility_id=r["facility"].id,
                year=r["year"],
                month=r["month"],
                process_type=r["proc"],
                fuel_type=r["fuel"],
                quantity=r["qty"],
                unit=r["unit"],
                company_name=r["facility"].name,
                group_name=r["facility"].division,
                activity=r["facility"].activity,
                division=r["facility"].division,
                region=r["facility"].region,
                field=r["facility"].field,
                co2_emissions=r["co2"],
                ch4_emissions=r["ch4"],
                n2o_emissions=r["n2o"],
                co2e_total=r["co2e"],
                calc_method=r["method"],
                status='Verified',
                uncertainty=0.03,
                ogmp_level=4
            )
            db.session.add(em)
        db.session.commit()
        print(f"Successfully seeded {len(facilities)} facilities and {len(records)} emission records for Admin User!")

if __name__ == '__main__':
    seed_data()
