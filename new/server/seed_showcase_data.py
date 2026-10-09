"""
Seed rich fictional data for Neocarbon:
- Algerian oil, gas, refining, and petrochemical facilities with accurate coordinates
- Multi-year monthly production data (2022-2026) in bbl and mscf
- Comprehensive Scope 1 emissions (Combustion, Flaring, Venting, Fugitive) with status='Verified'
- Scope 2 and Scope 3 verified emissions
- EU CBAM product exports for heavy industry and petrochemical products
- OGMP 2.0 Gold Standard empirical top-down surveys (Sentinel-5P, Drone OGI, Aerial LiDAR)
- Operational flaring streams and field-measured DRE % for Decree 21-330
"""
import sys
import os
import uuid
import datetime

sys.path.insert(0, os.path.abspath(r'c:\Users\samsung\Desktop\H2\new\server'))

from app import app
from extensions import db
from models import (
    User,
    Facility,
    ProductionData,
    Emission,
    Scope2Emission,
    Scope3Emission,
    CbamProductExport,
    OgmpSurvey,
    FlaringDetail,
)
from routes.dashboard import clear_dashboard_cache

def seed():
    with app.app_context():
        print("=== SEEDING REALISTIC FICTIONAL SHOWCASE DATA ===")
        
        # 1. Update or create primary facilities with real coordinates and standard classifications
        facilities_blueprint = [
            {
                "code": "HMD-01",
                "name": "Hassi Messaoud (HMD-South CPF)",
                "location": "Ouargla, Algeria",
                "region": "Ouargla / HMD",
                "division": "Production",
                "activity": "EP",
                "segment": "Upstream",
                "field": "OF",
                "latitude": 31.6800,
                "longitude": 6.0650,
                "description": "Super-giant oil field central processing facility, separation trains, and high-pressure gas reinjection station.",
                "operator_status": "operated",
                "equity_share_pct": 100.0,
                "ogmp_membership_year": 2023,
                "reconciliation_threshold": 15.0,
            },
            {
                "code": "HRM-01",
                "name": "Hassi R'Mel (HRM Central Gas Hub)",
                "location": "Laghouat, Algeria",
                "region": "Laghouat / HRM",
                "division": "Gas Processing",
                "activity": "GP",
                "segment": "Midstream",
                "field": "GF",
                "latitude": 32.9300,
                "longitude": 3.2700,
                "description": "National gas hub, condensate stabilization trains, booster compression, and major export manifold.",
                "operator_status": "operated",
                "equity_share_pct": 100.0,
                "ogmp_membership_year": 2023,
                "reconciliation_threshold": 10.0,
            },
            {
                "code": "RNS-01",
                "name": "Rhourde Nouss (RNS Sour Gas Plant)",
                "location": "Illizi, Algeria",
                "region": "Illizi / RNS",
                "division": "Production",
                "activity": "EP",
                "segment": "Upstream",
                "field": "GF",
                "latitude": 30.4100,
                "longitude": 6.5800,
                "description": "Sour gas sweetening, mercury removal, NGL extraction, and gas recycling complex.",
                "operator_status": "operated",
                "equity_share_pct": 100.0,
                "ogmp_membership_year": 2023,
                "reconciliation_threshold": 15.0,
            },
            {
                "code": "TFT-01",
                "name": "Tin Fouye Tabankort (TFT Gathering & CPF)",
                "location": "Illizi, Algeria",
                "region": "Illizi / TFT",
                "division": "Production",
                "activity": "EP",
                "segment": "Upstream",
                "field": "GF",
                "latitude": 28.8400,
                "longitude": 7.6900,
                "description": "Associated wet gas gathering, condensate stabilization, and low-pressure compression.",
                "operator_status": "operated",
                "equity_share_pct": 65.0,
                "ogmp_membership_year": 2023,
                "reconciliation_threshold": 20.0,
            },
            {
                "code": "HBNS-01",
                "name": "Hassi Berkine South (HBNS CPF)",
                "location": "Berkine Basin, Algeria",
                "region": "Berkine / HBNS",
                "division": "Production",
                "activity": "EP",
                "segment": "Upstream",
                "field": "OF",
                "latitude": 31.3300,
                "longitude": 7.4900,
                "description": "Berkine Basin Block 404a central oil treatment facility, water injection, and gas reinjection plant.",
                "operator_status": "operated",
                "equity_share_pct": 51.0,
                "ogmp_membership_year": 2023,
                "reconciliation_threshold": 15.0,
            },
            {
                "code": "GL1Z-01",
                "name": "Arzew LNG & Ammonia Terminal (GL1Z)",
                "location": "Arzew, Oran, Algeria",
                "region": "Oran / Arzew",
                "division": "Liquefaction",
                "activity": "LNG",
                "segment": "Downstream",
                "field": "GNL",
                "latitude": 35.8500,
                "longitude": -0.2800,
                "description": "Six-train baseload LNG liquefaction plant, cryogenic storage tanks, and anhydrous ammonia export marine dock.",
                "operator_status": "operated",
                "equity_share_pct": 100.0,
                "ogmp_membership_year": 2023,
                "reconciliation_threshold": 10.0,
            },
            {
                "code": "RA1K-01",
                "name": "Skikda Refining Complex (RA1K)",
                "location": "Skikda, Algeria",
                "region": "Skikda",
                "division": "Refining",
                "activity": "REF",
                "segment": "Downstream",
                "field": "Raffinerie",
                "latitude": 36.8800,
                "longitude": 6.9100,
                "description": "Atmospheric crude distillation, vacuum distillation, catalytic reforming, and aromatics extraction unit.",
                "operator_status": "operated",
                "equity_share_pct": 100.0,
                "ogmp_membership_year": 2023,
                "reconciliation_threshold": 15.0,
            }
        ]

        # Map facilities by code
        fac_obj_map = {}
        for fb in facilities_blueprint:
            fac = Facility.query.filter_by(code=fb["code"]).first()
            if not fac:
                # Check by name
                fac = Facility.query.filter_by(name=fb["name"]).first()
            if not fac:
                fac = Facility(**fb)
                db.session.add(fac)
                db.session.flush()
                print(f"Created facility: {fac.name} (ID: {fac.id})")
            else:
                for k, v in fb.items():
                    setattr(fac, k, v)
                print(f"Updated facility: {fac.name} (ID: {fac.id})")
            fac_obj_map[fb["code"]] = fac

        # Also update old facilities if present
        f1 = Facility.query.get(1)
        if f1 and f1.code not in fac_obj_map:
            f1.latitude = 30.41
            f1.longitude = 6.58
            f1.region = "Illizi / RNS"
            f1.activity = "EP"
            f1.division = "Production"
            f1.segment = "Upstream"

        f2 = Facility.query.get(2)
        if f2 and f2.code not in fac_obj_map:
            f2.latitude = 31.68
            f2.longitude = 6.06
            f2.region = "Ouargla / HMD"
            f2.activity = "EP"
            f2.division = "Production"
            f2.segment = "Upstream"

        f3 = Facility.query.get(3)
        if f3 and f3.code not in fac_obj_map:
            f3.latitude = 32.93
            f3.longitude = 3.27
            f3.region = "Laghouat / HRM"
            f3.activity = "GP"
            f3.division = "Gas Processing"
            f3.segment = "Midstream"

        f4 = Facility.query.get(4)
        if f4 and f4.code not in fac_obj_map:
            f4.latitude = 32.93
            f4.longitude = 3.27
            f4.region = "Laghouat / HRM"
            f4.activity = "GP"
            f4.division = "Gas Processing"
            f4.segment = "Midstream"

        db.session.commit()

        # 2. SEED PRODUCTION DATA (2022 to 2026)
        print("--- Seeding Monthly Production Data ---")
        all_facilities = Facility.query.all()
        # Monthly production profiles (oil_bbl, gas_mscf)
        prod_rates = {
            "HMD-01": (1250000.0, 4800000.0),
            "HRM-01": (180000.0, 16500000.0),
            "RNS-01": (420000.0, 5200000.0),
            "TFT-01": (310000.0, 3800000.0),
            "HBNS-01": (890000.0, 2400000.0),
            "GL1Z-01": (45000.0, 9500000.0),
            "RA1K-01": (620000.0, 1100000.0),
        }
        default_rate = (250000.0, 2100000.0)

        prod_count = 0
        for fac in all_facilities:
            rate = prod_rates.get(fac.code, default_rate)
            for yr in [2022, 2023, 2024, 2025, 2026]:
                max_month = 6 if yr == 2026 else 12
                # Realistic YoY decline or expansion
                yoy_mult = 1.0 + (yr - 2024) * 0.02
                for m in range(1, max_month + 1):
                    existing = ProductionData.query.filter_by(facility_id=fac.id, year=yr, month=m).first()
                    seasonal = 1.0 + ((m % 6) - 2.5) * 0.02
                    oil_val = round(rate[0] * yoy_mult * seasonal, 2)
                    gas_val = round(rate[1] * yoy_mult * seasonal, 2)
                    
                    if not existing:
                        p = ProductionData(
                            facility_id=fac.id,
                            year=yr,
                            month=m,
                            oil_amount=oil_val,
                            gas_amount=gas_val,
                            unit="bbl",
                            oil_unit="bbl",
                            gas_unit="mscf",
                            gross_gas_mmsm3=round(gas_val * 0.0283168 / 1000.0, 4),
                            injected_gas_mmsm3=round(gas_val * 0.0283168 * 0.35 / 1000.0, 4),
                            gas_without_injected_mmsm3=round(gas_val * 0.0283168 * 0.65 / 1000.0, 4),
                            crude_oil_mmboe=round(oil_val / 1000000.0, 4),
                        )
                        db.session.add(p)
                        prod_count += 1
                    else:
                        existing.oil_amount = oil_val
                        existing.gas_amount = gas_val
                        existing.oil_unit = "bbl"
                        existing.gas_unit = "mscf"

        db.session.commit()
        print(f"Total new/updated production records: {prod_count}")

        # 3. SEED COMPREHENSIVE SCOPE 1 EMISSIONS (Combustion, Flaring, Venting, Fugitive)
        print("--- Seeding Scope 1 Verified Emissions ---")
        em_count = 0
        for fac in all_facilities:
            # We want each facility to have verified emissions across years 2023-2026
            for yr in [2023, 2024, 2025, 2026]:
                # Check if this facility already has emissions for this year
                existing_count = Emission.query.filter_by(facility_id=fac.id, year=yr, status="Verified").count()
                if existing_count >= 4:
                    continue

                # Scale emissions based on segment
                if fac.segment == "Upstream":
                    base_co2 = 28000.0 if "HMD" in fac.name else 14000.0
                    base_ch4 = 850.0 if "HMD" in fac.name else 420.0
                elif fac.segment == "Midstream":
                    base_co2 = 36000.0
                    base_ch4 = 290.0
                else:
                    base_co2 = 48000.0
                    base_ch4 = 95.0

                # 1. Fuel Gas Combustion (CO2e from the stored gas masses, N2O included: AR5 28 / 265)
                comb_co2, comb_ch4 = round(base_co2 * 0.70, 2), round(base_ch4 * 0.12, 2)
                comb_n2o = round(base_co2 * 0.0004, 2)
                db.session.add(Emission(
                    record_id=f"EM-COMB-{fac.id}-{yr}-{uuid.uuid4().hex[:6]}",
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    process_type="Combustion",
                    fuel_type="Natural Gas",
                    quantity=round(base_co2 * 0.52, 2),
                    unit="tonnes",
                    co2_emissions=comb_co2,
                    ch4_emissions=comb_ch4,
                    n2o_emissions=comb_n2o,
                    co2e_total=round(comb_co2 + comb_ch4 * 28.0 + comb_n2o * 265.0, 2),
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                    field=fac.field,
                    ogmp_level=4,
                    calc_method="ef_facility_specific",
                ))

                # 2. Operational Flaring
                flaring_ch4 = round(base_ch4 * 0.28, 2)
                flaring_co2 = round(base_co2 * 0.22, 2)
                flaring_n2o = round(flaring_co2 * 0.0002, 2)
                db.session.add(Emission(
                    record_id=f"EM-FLAR-{fac.id}-{yr}-{uuid.uuid4().hex[:6]}",
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    process_type="Flaring",
                    fuel_type="Flare Gas",
                    quantity=round(flaring_co2 * 0.45, 2),
                    unit="tonnes",
                    co2_emissions=flaring_co2,
                    ch4_emissions=flaring_ch4,
                    n2o_emissions=flaring_n2o,
                    co2e_total=round(flaring_co2 + flaring_ch4 * 28.0 + flaring_n2o * 265.0, 2),
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                    field=fac.field,
                    ogmp_level=4,
                    calc_method="direct_measurement",
                ))

                # 3. Venting
                vent_ch4 = round(base_ch4 * 0.42, 2)
                vent_co2 = round(base_co2 * 0.05, 2)
                db.session.add(Emission(
                    record_id=f"EM-VENT-{fac.id}-{yr}-{uuid.uuid4().hex[:6]}",
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    process_type="Venting",
                    fuel_type="Associated Gas",
                    quantity=round(vent_ch4 * 1.4, 2),
                    unit="tonnes",
                    co2_emissions=vent_co2,
                    ch4_emissions=vent_ch4,
                    n2o_emissions=0.0,
                    co2e_total=round(vent_co2 + (vent_ch4 * 28.0), 2),
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                    field=fac.field,
                    ogmp_level=4,
                    calc_method="ef_facility_specific",
                ))

                # 4. Fugitive Leaks
                fug_ch4 = round(base_ch4 * 0.18, 2)
                fug_co2 = round(base_co2 * 0.03, 2)
                db.session.add(Emission(
                    record_id=f"EM-FUG-{fac.id}-{yr}-{uuid.uuid4().hex[:6]}",
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    process_type="Fugitive",
                    fuel_type="Field Gas",
                    quantity=round(fug_ch4 * 1.1, 2),
                    unit="tonnes",
                    co2_emissions=fug_co2,
                    ch4_emissions=fug_ch4,
                    n2o_emissions=0.0,
                    co2e_total=round(fug_co2 + (fug_ch4 * 28.0), 2),
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                    field=fac.field,
                    ogmp_level=4,
                    calc_method="engineering_estimate",
                ))
                em_count += 4

        db.session.commit()
        print(f"Total new verified Scope 1 emission records: {em_count}")

        # 4. SEED SCOPE 2 AND SCOPE 3 VERIFIED EMISSIONS
        print("--- Seeding Scope 2 & Scope 3 Emissions ---")
        for fac in all_facilities:
            for yr in [2023, 2024, 2025, 2026]:
                # Scope 2 (Purchased Electricity)
                s2_existing = Scope2Emission.query.filter_by(facility_id=fac.id, year=yr).first()
                if not s2_existing:
                    kwh = 12000000.0 if fac.segment == "Downstream" else 4500000.0
                    ef = 0.542 # kg CO2e/kWh (Algerian national grid average)
                    co2e_s2 = round((kwh * ef) / 1000.0, 2)
                    db.session.add(Scope2Emission(
                        facility_id=fac.id,
                        year=yr,
                        month=6,
                        source_type="electricity",
                        electricity_kwh=kwh,
                        emission_factor=ef,
                        co2e=co2e_s2,
                        status="Verified",
                    ))

                # Scope 3 (Purchased Goods, Transport, Capital Goods)
                s3_existing = Scope3Emission.query.filter_by(facility_id=fac.id, year=yr).first()
                if not s3_existing:
                    db.session.add(Scope3Emission(
                        facility_id=fac.id,
                        year=yr,
                        month=6,
                        category="Category 1: Purchased Goods and Services",
                        sub_category="Chemicals, Catalysts & Drilling Mud",
                        activity_data=8500.0,
                        unit="tonnes",
                        emission_factor=1420.0,  # kg CO2e per tonne (stored per activity unit in kg)
                        co2e=round(8500.0 * 1420.0 / 1000.0, 2),
                        status="Verified",
                    ))
        db.session.commit()

        # 5. SEED EU CBAM PRODUCT EXPORTS
        print("--- Seeding EU CBAM Product Exports ---")
        # Clear old cbam exports to have consistent clean showcase
        CbamProductExport.query.delete()
        cbam_entries = [
            {
                "facility_code": "GL1Z-01",
                "product_name": "Anhydrous Ammonia (High Purity)",
                "cn_code": "2814 10 00",
                "year": 2024,
                "month": 6,
                "quantity_tonnes": 48500.0,
                "export_destination": "EU - France (Fos-sur-Mer)",
                "specific_embedded_direct": 1.7850,
                "specific_embedded_indirect": 0.1420,
                "notes": "Direct steam methane reforming with secondary heat recovery. Accredited ISO 14064 verification."
            },
            {
                "facility_code": "GL1Z-01",
                "product_name": "Liquid Nitrogen Fertilizers (UAN 32%)",
                "cn_code": "3102 80 00",
                "year": 2025,
                "month": 4,
                "quantity_tonnes": 82000.0,
                "export_destination": "EU - Spain (Valencia)",
                "specific_embedded_direct": 0.8240,
                "specific_embedded_indirect": 0.0980,
                "notes": "Low-carbon synthesis train with automated real-time N2O abatement catalyst monitoring."
            },
            {
                "facility_code": "RA1K-01",
                "product_name": "Ultra-Low Sulfur Diesel (ULSD 10 ppm)",
                "cn_code": "2710 19 43",
                "year": 2025,
                "month": 8,
                "quantity_tonnes": 145000.0,
                "export_destination": "EU - Italy (Genoa)",
                "specific_embedded_direct": 0.2650,
                "specific_embedded_indirect": 0.0480,
                "notes": "Hydrodesulfurization unit with integrated cogeneration. Benchmark compliant (< 0.30 tCO2e/t)."
            },
            {
                "facility_code": "RA1K-01",
                "product_name": "Aromatics: Pure Benzene & Paraxylene",
                "cn_code": "2902 20 00",
                "year": 2026,
                "month": 2,
                "quantity_tonnes": 34000.0,
                "export_destination": "EU - Belgium (Antwerp)",
                "specific_embedded_direct": 0.6120,
                "specific_embedded_indirect": 0.1150,
                "notes": "Continuous catalytic reforming extraction train with heat exchanger network optimization."
            },
            {
                "facility_code": "GL1Z-01",
                "product_name": "Low-Carbon Clean Hydrogen",
                "cn_code": "2804 10 00",
                "year": 2026,
                "month": 5,
                "quantity_tonnes": 12500.0,
                "export_destination": "EU - Germany (Hamburg via Rail)",
                "specific_embedded_direct": 4.1200,
                "specific_embedded_indirect": 0.3500,
                "notes": "Pilot ATR train with partial CCS readiness and certified origin guarantee."
            }
        ]

        for item in cbam_entries:
            fac = fac_obj_map.get(item["facility_code"])
            if not fac:
                fac = all_facilities[0]
            db.session.add(CbamProductExport(
                facility_id=fac.id,
                year=item["year"],
                month=item["month"],
                product_name=item["product_name"],
                cn_code=item["cn_code"],
                quantity_tonnes=item["quantity_tonnes"],
                export_destination=item["export_destination"],
                specific_embedded_direct=item["specific_embedded_direct"],
                specific_embedded_indirect=item["specific_embedded_indirect"],
                notes=item["notes"],
            ))
        db.session.commit()
        print(f"Seeded {len(cbam_entries)} realistic EU CBAM Product Exports.")

        # 6. SEED OGMP 2.0 EMPIRICAL TOP-DOWN SURVEYS
        print("--- Seeding OGMP 2.0 Empirical Surveys ---")
        OgmpSurvey.query.delete()
        ogmp_samples = [
            # Hassi Messaoud
            {
                "facility_code": "HMD-01",
                "year": 2025,
                "survey_date": "2025-04-18",
                "survey_type": "Satellite (Sentinel-5P/TROPOMI)",
                "measured_rate_kg_hr": 92.4,
                "operating_hours_year": 8760.0,
                "estimated_annual_tch4": 809.4,
                "detection_threshold": 25.0,
                "instrument_vendor": "Copernicus TROPOMI SWIR Band 7/8",
                "bottom_up_tch4": 845.0,
                "variance_pct": -4.21,
                "variance_flag": False,
                "reconciliation_status": "Reconciled",
            },
            {
                "facility_code": "HMD-01",
                "year": 2025,
                "survey_date": "2025-09-12",
                "survey_type": "Aerial LiDAR (Bridger Photonics)",
                "measured_rate_kg_hr": 95.8,
                "operating_hours_year": 8760.0,
                "estimated_annual_tch4": 839.2,
                "detection_threshold": 3.0,
                "instrument_vendor": "GasMapping LiDAR GML-4",
                "bottom_up_tch4": 845.0,
                "variance_pct": -0.69,
                "variance_flag": False,
                "reconciliation_status": "Reconciled",
            },
            # Hassi R'Mel
            {
                "facility_code": "HRM-01",
                "year": 2025,
                "survey_date": "2025-05-22",
                "survey_type": "Drone OGI (FLIR GF320)",
                "measured_rate_kg_hr": 31.5,
                "operating_hours_year": 8760.0,
                "estimated_annual_tch4": 275.9,
                "detection_threshold": 0.8,
                "instrument_vendor": "FLIR GF320 Optical Gas Imaging",
                "bottom_up_tch4": 288.4,
                "variance_pct": -4.33,
                "variance_flag": False,
                "reconciliation_status": "Reconciled",
            },
            {
                "facility_code": "HRM-01",
                "year": 2024,
                "survey_date": "2024-11-05",
                "survey_type": "Satellite (Sentinel-5P/TROPOMI)",
                "measured_rate_kg_hr": 33.2,
                "operating_hours_year": 8760.0,
                "estimated_annual_tch4": 290.8,
                "detection_threshold": 25.0,
                "instrument_vendor": "Copernicus TROPOMI SWIR Band 7/8",
                "bottom_up_tch4": 294.0,
                "variance_pct": -1.09,
                "variance_flag": False,
                "reconciliation_status": "Reconciled",
            },
            # Rhourde Nouss
            {
                "facility_code": "RNS-01",
                "year": 2025,
                "survey_date": "2025-06-14",
                "survey_type": "Continuous Monitor",
                "measured_rate_kg_hr": 46.8,
                "operating_hours_year": 8760.0,
                "estimated_annual_tch4": 409.9,
                "detection_threshold": 0.5,
                "instrument_vendor": "Sensirion Point-Sensor Laser Array",
                "bottom_up_tch4": 418.0,
                "variance_pct": -1.94,
                "variance_flag": False,
                "reconciliation_status": "Reconciled",
            },
            # Tin Fouye Tabankort
            {
                "facility_code": "TFT-01",
                "year": 2025,
                "survey_date": "2025-08-30",
                "survey_type": "Aerial LiDAR (Bridger Photonics)",
                "measured_rate_kg_hr": 43.1,
                "operating_hours_year": 8760.0,
                "estimated_annual_tch4": 377.5,
                "detection_threshold": 3.0,
                "instrument_vendor": "GasMapping LiDAR GML-4",
                "bottom_up_tch4": 395.2,
                "variance_pct": -4.48,
                "variance_flag": False,
                "reconciliation_status": "Reconciled",
            },
            # Hassi Berkine South
            {
                "facility_code": "HBNS-01",
                "year": 2025,
                "survey_date": "2025-07-19",
                "survey_type": "Satellite (Sentinel-5P/TROPOMI)",
                "measured_rate_kg_hr": 54.0,
                "operating_hours_year": 8760.0,
                "estimated_annual_tch4": 473.0,
                "detection_threshold": 25.0,
                "instrument_vendor": "Copernicus TROPOMI SWIR Band 7/8",
                "bottom_up_tch4": 462.5,
                "variance_pct": 2.27,
                "variance_flag": False,
                "reconciliation_status": "Reconciled",
            }
        ]

        for s in ogmp_samples:
            fac = fac_obj_map.get(s["facility_code"])
            if not fac:
                fac = all_facilities[0]
            db.session.add(OgmpSurvey(
                facility_id=fac.id,
                year=s["year"],
                survey_date=s["survey_date"],
                survey_type=s["survey_type"],
                measured_rate_kg_hr=s["measured_rate_kg_hr"],
                operating_hours_year=s["operating_hours_year"],
                estimated_annual_tch4=s["estimated_annual_tch4"],
                detection_threshold=s["detection_threshold"],
                instrument_vendor=s["instrument_vendor"],
                bottom_up_tch4=s["bottom_up_tch4"],
                variance_pct=s["variance_pct"],
                variance_flag=s["variance_flag"],
                reconciliation_status=s["reconciliation_status"],
            ))
        db.session.commit()
        print(f"Seeded {len(ogmp_samples)} OGMP 2.0 Gold Standard empirical surveys.")

        # 7. SEED OPERATIONAL FLARING DETAILS (Decree 21-330 compliance)
        print("--- Seeding Operational Flaring Streams ---")
        FlaringDetail.query.delete()
        flaring_samples = [
            {"facility_code": "HMD-01", "year": 2025, "routine": 240.0, "non_routine": 48.0, "safety": 18.0, "dre": 99.88},
            {"facility_code": "HRM-01", "year": 2025, "routine": 110.0, "non_routine": 32.0, "safety": 25.0, "dre": 99.94},
            {"facility_code": "RNS-01", "year": 2025, "routine": 85.0, "non_routine": 22.0, "safety": 12.0, "dre": 99.82},
            {"facility_code": "TFT-01", "year": 2025, "routine": 65.0, "non_routine": 15.0, "safety": 8.0, "dre": 99.79},
            {"facility_code": "HBNS-01", "year": 2025, "routine": 78.0, "non_routine": 18.0, "safety": 14.0, "dre": 99.90},
            {"facility_code": "GL1Z-01", "year": 2025, "routine": 42.0, "non_routine": 28.0, "safety": 35.0, "dre": 99.95},
            {"facility_code": "RA1K-01", "year": 2025, "routine": 95.0, "non_routine": 40.0, "safety": 22.0, "dre": 99.85},
            # 2024 records
            {"facility_code": "HMD-01", "year": 2024, "routine": 265.0, "non_routine": 54.0, "safety": 20.0, "dre": 99.84},
            {"facility_code": "HRM-01", "year": 2024, "routine": 125.0, "non_routine": 38.0, "safety": 28.0, "dre": 99.91},
        ]
        for fl in flaring_samples:
            fac = fac_obj_map.get(fl["facility_code"])
            if not fac:
                fac = all_facilities[0]
            tot = fl["routine"] + fl["non_routine"] + fl["safety"]
            db.session.add(FlaringDetail(
                facility_id=fac.id,
                year=fl["year"],
                month=6,
                network="CPF",
                routine_knm3=fl["routine"],
                non_routine_knm3=fl["non_routine"],
                safety_knm3=fl["safety"],
                total_knm3=tot,
                measured_dre_pct=fl["dre"],
                dre_method="VISR Infrared Optical Camera",
                status="Verified",
            ))
        db.session.commit()
        print(f"Seeded {len(flaring_samples)} operational flaring stream records.")

        # 8. CLEAR DASHBOARD CACHE
        clear_dashboard_cache()
        print("Cleared dashboard caches. All metrics and charts updated!")

if __name__ == "__main__":
    seed()
