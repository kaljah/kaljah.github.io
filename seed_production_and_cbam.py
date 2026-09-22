"""
Seed Production Data and EU CBAM Product Exports
Populates realistic production (bbl oil, mscf gas) and CBAM export batches
for facilities 1-16 across 2022-2026 to power the full Carbon Intensity pipeline.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'new', 'server'))

from app import app, db
from models import Facility, ProductionData, CbamProductExport, User
from routes.dashboard import clear_dashboard_cache

def seed():
    with app.app_context():
        admin = User.query.filter_by(role='admin').first()
        admin_id = admin.id if admin else 1

        print("--- Seeding Production Data ---")
        facilities = Facility.query.all()
        fac_map = {f.id: f for f in facilities}

        prod_profiles = {
            1: (45000.0, 320000.0),    # Tosyali Steel DRI
            2: (25000.0, 480000.0),    # Fertial Ammonia
            3: (15000.0, 180000.0),    # GICA Cement
            4: (120000.0, 3500000.0),  # Sonatrach Gas HMD
            5: (85000.0, 1400000.0),   # ADR (E&P DP)
            6: (65000.0, 950000.0),    # REB (E&P DP)
            7: (72000.0, 1100000.0),   # HBK (E&P DP)
            8: (90000.0, 1600000.0),   # GTL (E&P DP)
            9: (55000.0, 800000.0),    # OHT (E&P DP)
            10: (60000.0, 900000.0),   # STAH (E&P DP)
            11: (110000.0, 2200000.0), # TFT (E&P DP)
            12: (95000.0, 1800000.0),  # HMD (E&P DP)
            13: (50000.0, 750000.0),   # RNS (E&P DP)
            14: (130000.0, 2800000.0), # HRM (E&P DP)
            15: (40000.0, 600000.0),   # INAS (E&P DP)
            16: (80000.0, 1500000.0),  # BRS (E&P AST)
        }

        seeded_prod = 0
        for yr in [2022, 2023, 2024, 2025, 2026]:
            months = range(1, 7) if yr == 2026 else range(1, 13)
            year_factor = 1.0 + (yr - 2024) * 0.03

            for fid, (base_oil, base_gas) in prod_profiles.items():
                fac = fac_map.get(fid)
                if not fac:
                    continue

                for m in months:
                    existing = ProductionData.query.filter_by(facility_id=fid, year=yr, month=m).first()
                    if not existing:
                        m_factor = year_factor * (1.0 + ((m % 5) - 2) * 0.015)
                        p = ProductionData(
                            facility_id=fid,
                            year=yr,
                            month=m,
                            oil_amount=round(base_oil * m_factor, 2),
                            gas_amount=round(base_gas * m_factor, 2),
                            unit="bbl",
                            oil_unit="bbl",
                            gas_unit="mscf",
                            activity=fac.activity,
                            division=fac.division,
                            region=fac.region,
                            field=fac.field,
                            created_by=admin_id,
                        )
                        db.session.add(p)
                        seeded_prod += 1

        db.session.commit()
        print(f"Successfully seeded {seeded_prod} monthly production records.")

        print("--- Seeding EU CBAM Product Export Records ---")
        cbam_records = [
            # Tosyali Steel DRI (Facility 1)
            {
                "facility_id": 1,
                "product_name": "Direct Reduced Iron (DRI)",
                "cn_code": "7203 10 00",
                "year": 2024,
                "month": 6,
                "quantity_tonnes": 25000.0,
                "export_destination": "EU - Italy",
                "specific_embedded_direct": 1.1250,
                "specific_embedded_indirect": 0.2450,
            },
            {
                "facility_id": 1,
                "product_name": "Hot Rolled Bars & Wire Rod",
                "cn_code": "7213 10 00",
                "year": 2026,
                "month": 3,
                "quantity_tonnes": 18500.0,
                "export_destination": "EU - Spain",
                "specific_embedded_direct": 1.3400,
                "specific_embedded_indirect": 0.3120,
            },
            # Fertial Ammonia (Facility 2)
            {
                "facility_id": 2,
                "product_name": "Anhydrous Ammonia",
                "cn_code": "2814 10 00",
                "year": 2024,
                "month": 8,
                "quantity_tonnes": 15000.0,
                "export_destination": "EU - France",
                "specific_embedded_direct": 1.8200,
                "specific_embedded_indirect": 0.1150,
            },
            {
                "facility_id": 2,
                "product_name": "Urea / Ammonium Nitrate Solutions",
                "cn_code": "3102 10 10",
                "year": 2026,
                "month": 2,
                "quantity_tonnes": 22000.0,
                "export_destination": "EU - Belgium",
                "specific_embedded_direct": 0.9450,
                "specific_embedded_indirect": 0.0880,
            },
            # GICA Cement (Facility 3)
            {
                "facility_id": 3,
                "product_name": "Grey Portland Clinker",
                "cn_code": "2523 10 00",
                "year": 2024,
                "month": 11,
                "quantity_tonnes": 40000.0,
                "export_destination": "EU - Italy",
                "specific_embedded_direct": 0.7650,
                "specific_embedded_indirect": 0.0620,
            },
            # Sonatrach Gas Hassi Messaoud (Facility 4)
            {
                "facility_id": 4,
                "product_name": "Liquefied Natural Gas (LNG)",
                "cn_code": "2711 11 00",
                "year": 2024,
                "month": 9,
                "quantity_tonnes": 55000.0,
                "export_destination": "EU - Spain",
                "specific_embedded_direct": 0.2850,
                "specific_embedded_indirect": 0.0350,
            },
        ]

        seeded_cbam = 0
        for item in cbam_records:
            existing = CbamProductExport.query.filter_by(
                facility_id=item["facility_id"],
                cn_code=item["cn_code"],
                year=item["year"],
                month=item["month"]
            ).first()
            if not existing:
                rec = CbamProductExport(
                    facility_id=item["facility_id"],
                    product_name=item["product_name"],
                    cn_code=item["cn_code"],
                    year=item["year"],
                    month=item["month"],
                    quantity_tonnes=item["quantity_tonnes"],
                    export_destination=item["export_destination"],
                    specific_embedded_direct=item["specific_embedded_direct"],
                    specific_embedded_indirect=item["specific_embedded_indirect"],
                    created_by=admin_id,
                )
                db.session.add(rec)
                seeded_cbam += 1

        db.session.commit()
        print(f"Successfully seeded {seeded_cbam} CBAM product export records.")

        clear_dashboard_cache()
        print("Dashboard cache invalidated.")

if __name__ == "__main__":
    seed()
