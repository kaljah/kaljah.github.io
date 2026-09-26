"""
Seed script for Groupement Berkine (HBNS & El Merk) 2021-2025 Historical Data.
Populates:
1. HBNS and El Merk facilities with 51% Sonatrach equity share
2. Joint Venture Partners (Sonatrach, Occidental, Eni, TotalEnergies, Pertamina, Repsol)
3. Facility equity share percentages
4. Granular Production Data (2021-2025)
5. Flaring Stream Details & VISR camera measured DRE (2021-2025)
6. Scope 1 & Scope 2 Emissions records (combustion, routine/non-routine/safety flaring, venting, fugitives)
7. Criteria Air Pollutants (CAP) emissions and stack concentrations under Decree 06-138
"""

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from extensions import db
from models import (
    Facility,
    ProductionData,
    Emission,
    Scope2Emission,
    FlaringDetail,
    JvPartner,
    FacilityEquityShare,
    CapEmission,
    CapRegulatoryLimit,
)


def seed_berkine():
    with app.app_context():
        print("--- Seeding Groupement Berkine 2021-2025 Data ---")

        # 1. Seed or Get Facilities
        hbns = Facility.query.filter_by(code="HBNS").first()
        if not hbns:
            hbns = Facility(
                name="HBNS (Hassi Berkine South)",
                code="HBNS",
                activity="Upstream",
                division="Berkine Basin",
                region="HBNS",
                field="Hassi Berkine South",
                segment="Upstream",
                boundary_type="Equity Share",
                equity_share_pct=51.0,
                operator_status="operated",
                country="Algeria",
                description="HBNS Central Processing Facility and satellite fields in Block 404a",
            )
            db.session.add(hbns)
            db.session.flush()
            print(f"Created HBNS facility with ID {hbns.id}")
        else:
            hbns.equity_share_pct = 51.0
            hbns.boundary_type = "Equity Share"

        elm = Facility.query.filter_by(code="ELM").first()
        if not elm:
            elm = Facility(
                name="El Merk",
                code="ELM",
                activity="Upstream",
                division="Berkine Basin",
                region="El Merk",
                field="Block 208",
                segment="Upstream",
                boundary_type="Equity Share",
                equity_share_pct=51.0,
                operator_status="operated",
                country="Algeria",
                description="El Merk Central Processing Facility in Block 208",
            )
            db.session.add(elm)
            db.session.flush()
            print(f"Created El Merk facility with ID {elm.id}")
        else:
            elm.equity_share_pct = 51.0
            elm.boundary_type = "Equity Share"

        db.session.commit()

        # 2. Seed JV Partners
        partners_def = [
            {"name": "Sonatrach", "code": "SH", "country": "Algeria", "is_operator": True},
            {"name": "Occidental", "code": "OXY", "country": "United States", "is_operator": False},
            {"name": "Eni", "code": "ENI", "country": "Italy", "is_operator": False},
            {"name": "TotalEnergies", "code": "TTE", "country": "France", "is_operator": False},
            {"name": "Pertamina", "code": "PER", "country": "Indonesia", "is_operator": False},
            {"name": "Repsol", "code": "REP", "country": "Spain", "is_operator": False},
        ]
        partner_objs = {}
        for p in partners_def:
            part = JvPartner.query.filter_by(name=p["name"]).first()
            if not part:
                part = JvPartner(
                    name=p["name"],
                    code=p["code"],
                    country=p["country"],
                    is_operator=p["is_operator"],
                )
                db.session.add(part)
                db.session.flush()
            partner_objs[p["name"]] = part
        db.session.commit()

        # 3. Seed Facility Equity Shares
        # HBNS shares
        hbns_shares = [
            ("Sonatrach", 51.00),
            ("Occidental", 24.50),
            ("TotalEnergies", 12.25),
            ("Eni", 12.25),
        ]
        for pname, pct in hbns_shares:
            p_obj = partner_objs[pname]
            share = FacilityEquityShare.query.filter_by(facility_id=hbns.id, partner_id=p_obj.id).first()
            if not share:
                share = FacilityEquityShare(
                    facility_id=hbns.id,
                    partner_id=p_obj.id,
                    equity_share_pct=pct,
                    effective_start_date="2021-01-01",
                    agreement_reference="Block 404a Association Contract",
                )
                db.session.add(share)
            else:
                share.equity_share_pct = pct

        # ELM shares
        elm_shares = [
            ("Sonatrach", 51.00),
            ("Occidental", 12.25),
            ("Eni", 12.25),
            ("TotalEnergies", 12.25),
            ("Pertamina", 8.00),
            ("Repsol", 4.25),
        ]
        for pname, pct in elm_shares:
            p_obj = partner_objs[pname]
            share = FacilityEquityShare.query.filter_by(facility_id=elm.id, partner_id=p_obj.id).first()
            if not share:
                share = FacilityEquityShare(
                    facility_id=elm.id,
                    partner_id=p_obj.id,
                    equity_share_pct=pct,
                    effective_start_date="2021-01-01",
                    agreement_reference="Block 208 Association Contract",
                )
                db.session.add(share)
            else:
                share.equity_share_pct = pct
        db.session.commit()

        # 4. Seed Granular Production Data (2021-2025)
        hbns_prod = {
            2021: {"gross_gas": 5088.03, "gas_wo_inj": 765.51, "crude": 24.85, "total": 67.11, "total_wo": 31.21, "saleable": 28.36},
            2022: {"gross_gas": 5497.26, "gas_wo_inj": 808.06, "crude": 26.56, "total": 72.18, "total_wo": 33.27, "saleable": 30.45},
            2023: {"gross_gas": 5541.74, "gas_wo_inj": 772.85, "crude": 24.98, "total": 71.15, "total_wo": 31.42, "saleable": 28.77},
            2024: {"gross_gas": 5723.88, "gas_wo_inj": 544.06, "crude": 22.17, "total": 69.85, "total_wo": 26.70, "saleable": 24.50},
            2025: {"gross_gas": 5517.62, "gas_wo_inj": 392.69, "crude": 24.20, "total": 70.16, "total_wo": 27.47, "saleable": 25.44},
        }

        elm_prod = {
            2021: {"gross_gas": 3655.66, "gas_wo_inj": 338.35, "crude": 32.92, "total": 59.19, "total_wo": 35.35, "saleable": 32.92},
            2022: {"gross_gas": 3964.74, "gas_wo_inj": 380.95, "crude": 32.60, "total": 60.71, "total_wo": 35.32, "saleable": 32.60},
            2023: {"gross_gas": 4244.53, "gas_wo_inj": 369.26, "crude": 34.99, "total": 64.74, "total_wo": 37.58, "saleable": 34.99},
            2024: {"gross_gas": 4353.68, "gas_wo_inj": 369.25, "crude": 33.97, "total": 64.43, "total_wo": 36.56, "saleable": 33.97},
            2025: {"gross_gas": 4239.89, "gas_wo_inj": 374.81, "crude": 31.18, "total": 60.77, "total_wo": 33.80, "saleable": 31.18},
        }

        for yr, val in hbns_prod.items():
            p = ProductionData.query.filter_by(facility_id=hbns.id, year=yr).first()
            if not p:
                p = ProductionData(facility_id=hbns.id, year=yr, month=12)
                db.session.add(p)
            p.gross_gas_mmsm3 = val["gross_gas"]
            p.gas_without_injected_mmsm3 = val["gas_wo_inj"]
            p.injected_gas_mmsm3 = round(val["gross_gas"] - val["gas_wo_inj"], 2)
            p.crude_oil_mmboe = val["crude"]
            p.total_production_mmboe = val["total"]
            p.total_production_no_injected_mmboe = val["total_wo"]
            p.saleable_production_mmboe = val["saleable"]
            p.oil_amount = val["crude"] * 1e6  # legacy fallback
            p.gas_amount = val["gross_gas"] * 35.3147  # MMSCF legacy fallback
            p.oil_unit = "bbl"
            p.gas_unit = "mmscf"

        for yr, val in elm_prod.items():
            p = ProductionData.query.filter_by(facility_id=elm.id, year=yr).first()
            if not p:
                p = ProductionData(facility_id=elm.id, year=yr, month=12)
                db.session.add(p)
            p.gross_gas_mmsm3 = val["gross_gas"]
            p.gas_without_injected_mmsm3 = val["gas_wo_inj"]
            p.injected_gas_mmsm3 = round(val["gross_gas"] - val["gas_wo_inj"], 2)
            p.crude_oil_mmboe = val["crude"]
            p.total_production_mmboe = val["total"]
            p.total_production_no_injected_mmboe = val["total_wo"]
            p.saleable_production_mmboe = val["saleable"]
            p.oil_amount = val["crude"] * 1e6
            p.gas_amount = val["gross_gas"] * 35.3147
            p.oil_unit = "bbl"
            p.gas_unit = "mmscf"

        db.session.commit()

        # 5. Seed Flaring Details & Measured DRE (2021-2025)
        hbns_flaring = {
            2021: {"total": 89680.0, "routine": 50125.0, "non_routine": 344.0, "safety": 39211.0, "dre": 99.85},
            2022: {"total": 63440.0, "routine": 46300.0, "non_routine": 289.0, "safety": 16851.0, "dre": 99.87},
            2023: {"total": 63590.0, "routine": 38192.0, "non_routine": 291.0, "safety": 25107.0, "dre": 99.85},
            2024: {"total": 50660.0, "routine": 27904.0, "non_routine": 20745.0, "safety": 2011.0, "dre": 99.88},
            2025: {"total": 47750.0, "routine": 26740.0, "non_routine": 19100.0, "safety": 1910.0, "dre": 99.89},
        }

        elm_flaring = {
            2021: {"total": 101682.0, "routine": 50271.0, "non_routine": 3026.0, "safety": 48385.0, "dre": 99.74},
            2022: {"total": 129575.0, "routine": 37066.0, "non_routine": 2393.0, "safety": 90116.0, "dre": 99.78},
            2023: {"total": 75558.0, "routine": 43579.0, "non_routine": 3134.0, "safety": 28845.0, "dre": 99.80},
            2024: {"total": 63344.0, "routine": 49387.0, "non_routine": 9262.0, "safety": 4695.0, "dre": 99.82},
            2025: {"total": 70148.0, "routine": 47246.0, "non_routine": 17269.0, "safety": 5633.0, "dre": 99.85},
        }

        for yr, val in hbns_flaring.items():
            fd = FlaringDetail.query.filter_by(facility_id=hbns.id, year=yr).first()
            if not fd:
                fd = FlaringDetail(facility_id=hbns.id, year=yr)
                db.session.add(fd)
            fd.total_knm3 = val["total"]
            fd.routine_knm3 = val["routine"]
            fd.non_routine_knm3 = val["non_routine"]
            fd.safety_knm3 = val["safety"]
            fd.measured_dre_pct = val["dre"]
            fd.dre_method = "VISR Camera"

        for yr, val in elm_flaring.items():
            fd = FlaringDetail.query.filter_by(facility_id=elm.id, year=yr).first()
            if not fd:
                fd = FlaringDetail(facility_id=elm.id, year=yr)
                db.session.add(fd)
            fd.total_knm3 = val["total"]
            fd.routine_knm3 = val["routine"]
            fd.non_routine_knm3 = val["non_routine"]
            fd.safety_knm3 = val["safety"]
            fd.measured_dre_pct = val["dre"]
            fd.dre_method = "VISR Camera"

        db.session.commit()

        # 6. Seed Detailed Emissions (Scope 1 and Scope 2)
        # Clear existing Berkine emissions to avoid duplicate historical accumulation
        Emission.query.filter(Emission.facility_id.in_([hbns.id, elm.id])).delete(synchronize_session=False)
        Scope2Emission.query.filter(Scope2Emission.facility_id.in_([hbns.id, elm.id])).delete(synchronize_session=False)

        hbns_emissions = {
            2021: {"combustion": 743000, "flare": 285000, "venting": 3000, "fugitive": 1000, "scope2": 85000, "ch4": 2866},
            2022: {"combustion": 756000, "flare": 244000, "venting": 3500, "fugitive": 1200, "scope2": 89000, "ch4": 2769},
            2023: {"combustion": 772000, "flare": 176000, "venting": 2800, "fugitive": 1100, "scope2": 91000, "ch4": 2589},
            2024: {"combustion": 551000, "flare": 203000, "venting": 2000, "fugitive": 800, "scope2": 76000, "ch4": 1362},
            2025: {"combustion": 569000, "flare": 138000, "venting": 1800, "fugitive": 700, "scope2": 75000, "ch4": 792},
        }

        elm_emissions = {
            2021: {"combustion": 634000, "flare": 281000, "venting": 2500, "fugitive": 1500, "scope2": 172000, "ch4": 4223},
            2022: {"combustion": 665000, "flare": 342000, "venting": 2600, "fugitive": 1400, "scope2": 215000, "ch4": 4652},
            2023: {"combustion": 804000, "flare": 196000, "venting": 2400, "fugitive": 1600, "scope2": 245000, "ch4": 4233},
            2024: {"combustion": 712000, "flare": 167000, "venting": 2200, "fugitive": 1800, "scope2": 250000, "ch4": 1343},
            2025: {"combustion": 714000, "flare": 168000, "venting": 2300, "fugitive": 1700, "scope2": 239000, "ch4": 874},
        }

        for fac, data_dict in [(hbns, hbns_emissions), (elm, elm_emissions)]:
            for yr, vals in data_dict.items():
                date_str = f"{yr}-06-15"
                # Stationary Combustion
                db.session.add(Emission(
                    record_id=f"{fac.code}-{yr}-combustion",
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    process_type="fuel_gas",
                    fuel_type="natural_gas",
                    quantity=vals["combustion"] / 2.2,
                    unit="m3",
                    co2e_total=vals["combustion"],
                    co2_emissions=vals["combustion"] * 0.98,
                    ch4_emissions=vals["ch4"] * 0.25,
                    n2o_emissions=vals["combustion"] * 0.0001,
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                ))

                # Split flaring into routine, non-routine, safety
                total_flare = vals["flare"]
                r_flare = total_flare * 0.56
                nr_flare = total_flare * 0.40
                s_flare = total_flare * 0.04

                db.session.add(Emission(
                    record_id=f"{fac.code}-{yr}-routine-flare",
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    process_type="routine_flaring",
                    fuel_type="natural_gas",
                    quantity=(r_flare / 2.5) * 1000.0,
                    unit="m3",
                    co2e_total=r_flare,
                    co2_emissions=r_flare * 0.98,
                    ch4_emissions=vals["ch4"] * 0.35,
                    n2o_emissions=r_flare * 0.0001,
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                ))
                db.session.add(Emission(
                    record_id=f"{fac.code}-{yr}-non-routine-flare",
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    process_type="non_routine_flaring",
                    fuel_type="natural_gas",
                    quantity=(nr_flare / 2.5) * 1000.0,
                    unit="m3",
                    co2e_total=nr_flare,
                    co2_emissions=nr_flare * 0.98,
                    ch4_emissions=vals["ch4"] * 0.25,
                    n2o_emissions=nr_flare * 0.0001,
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                ))
                db.session.add(Emission(
                    record_id=f"{fac.code}-{yr}-safety-flare",
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    process_type="safety_flaring",
                    fuel_type="natural_gas",
                    quantity=(s_flare / 2.5) * 1000.0,
                    unit="m3",
                    co2e_total=s_flare,
                    co2_emissions=s_flare * 0.98,
                    ch4_emissions=vals["ch4"] * 0.05,
                    n2o_emissions=s_flare * 0.0001,
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                ))

                # Venting & Fugitives
                db.session.add(Emission(
                    record_id=f"{fac.code}-{yr}-venting",
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    process_type="tank_venting",
                    fuel_type="natural_gas",
                    quantity=vals["venting"],
                    unit="m3",
                    co2e_total=vals["venting"],
                    co2_emissions=0.0,
                    ch4_emissions=vals["ch4"] * 0.08,
                    n2o_emissions=0.0,
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                ))
                db.session.add(Emission(
                    record_id=f"{fac.code}-{yr}-fugitive",
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    process_type="equipment_leaks",
                    fuel_type="natural_gas",
                    quantity=vals["fugitive"],
                    unit="m3",
                    co2e_total=vals["fugitive"],
                    co2_emissions=0.0,
                    ch4_emissions=vals["ch4"] * 0.02,
                    n2o_emissions=0.0,
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                ))

                # Scope 2 (Grid electricity / imported power)
                db.session.add(Scope2Emission(
                    facility_id=fac.id,
                    year=yr,
                    month=6,
                    source_type="electricity",
                    electricity_kwh=vals["scope2"] / 0.58,  # kWh
                    emission_factor=0.58,
                    co2e=vals["scope2"],
                    status="Verified",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                ))

        db.session.commit()

        # 7. Seed Criteria Air Pollutants (CAP) Records (2021-2025)
        CapEmission.query.filter(CapEmission.facility_id.in_([hbns.id, elm.id])).delete(synchronize_session=False)

        # Pre-seed Decree 06-138 Regulatory Limits
        limits_def = [
            ("NO2", 200.0, "mg/Nm3", "Decree 06-138: Nitrogen Dioxide limit"),
            ("CO", 150.0, "mg/Nm3", "Decree 06-138: Carbon Monoxide limit"),
            ("SO2", 800.0, "mg/Nm3", "Decree 06-138: Sulfur Dioxide limit"),
            ("PM", 30.0, "mg/Nm3", "Decree 06-138: Particulate Matter limit"),
            ("VOC", 150.0, "mg/Nm3", "Decree 06-138: Volatile Organic Compounds limit"),
        ]
        for pol, lim, u, notes in limits_def:
            l_obj = CapRegulatoryLimit.query.filter_by(standard_name="Executive Decree 06-138", pollutant=pol).first()
            if not l_obj:
                l_obj = CapRegulatoryLimit(
                    standard_name="Executive Decree 06-138",
                    pollutant=pol,
                    limit_mg_nm3=lim,
                    unit=u,
                    notes=notes,
                )
                db.session.add(l_obj)
        db.session.commit()

        # HBNS CAP data
        hbns_cap = {
            2021: {"NO2": 1715.19, "CO": 1049.93, "SO2": 9.17, "PM": 285.98, "VOC": 1669.18},
            2022: {"NO2": 1601.31, "CO": 966.06, "SO2": 4.84, "PM": 247.05, "VOC": 1596.27},
            2023: {"NO2": 1637.60, "CO": 844.64, "SO2": 9.22, "PM": 193.42, "VOC": 1332.28},
            2024: {"NO2": 1418.91, "CO": 781.55, "SO2": 6.61, "PM": 203.14, "VOC": 696.62},
            2025: {"NO2": 1414.70, "CO": 668.58, "SO2": 6.35, "PM": 156.91, "VOC": 406.37},
        }
        hbns_concentrations_2025 = {
            "NO2": 788.0,
            "CO": 7.50,
            "SO2": 0.0,
            "PM": 0.0,
            "VOC": 11.13,
        }

        # ELM CAP data
        elm_cap = {
            2021: {"NO2": 1444.73, "CO": 968.06, "SO2": 11.11, "PM": 279.06, "VOC": 815.64},
            2022: {"NO2": 1593.60, "CO": 1112.90, "SO2": 11.87, "PM": 333.15, "VOC": 672.28},
            2023: {"NO2": 1823.75, "CO": 908.59, "SO2": 12.31, "PM": 212.42, "VOC": 736.86},
            2024: {"NO2": 1749.53, "CO": 830.40, "SO2": 12.18, "PM": 184.66, "VOC": 257.19},
            2025: {"NO2": 1760.78, "CO": 875.66, "SO2": 14.08, "PM": 204.26, "VOC": 130.45},
        }
        elm_concentrations_2025 = {
            "NO2": 980.77,
            "CO": 9.84,
            "SO2": 0.0,
            "PM": 0.0,
            "VOC": 3.41,
        }

        for yr, p_dict in hbns_cap.items():
            for pol, mass in p_dict.items():
                conc = hbns_concentrations_2025.get(pol) if yr == 2025 else None
                db.session.add(CapEmission(
                    facility_id=hbns.id,
                    year=yr,
                    source_module="Stationary Combustion",
                    pollutant=pol,
                    mass_tonnes=mass,
                    concentration_mg_nm3=conc,
                    flue_gas_volume_nm3=1800000.0 if conc else None,
                    calc_method="API Compendium & Stack Sampling",
                    status="Verified",
                ))

        for yr, p_dict in elm_cap.items():
            for pol, mass in p_dict.items():
                conc = elm_concentrations_2025.get(pol) if yr == 2025 else None
                db.session.add(CapEmission(
                    facility_id=elm.id,
                    year=yr,
                    source_module="Stationary Combustion",
                    pollutant=pol,
                    mass_tonnes=mass,
                    concentration_mg_nm3=conc,
                    flue_gas_volume_nm3=1800000.0 if conc else None,
                    calc_method="API Compendium & Stack Sampling",
                    status="Verified",
                ))

        db.session.commit()
        print("--- Berkine Historical Data Seeding Completed Successfully! ---")


if __name__ == "__main__":
    seed_berkine()
