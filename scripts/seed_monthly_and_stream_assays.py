"""
Seed authentic monthly ProductionData (Jan-Dec 2022) and multi-stream gas assays (CustomFactors)
for HBNS (37) and El Merk (38) directly into ghg_app.db.
"""
import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'new', 'server'))
from app import app
from extensions import db
from models import ProductionData, CustomFactor, Facility

# HBNS 2022 Monthly Data (From Tables B-2b and B-2c)
# Units: oil (bbl), gas (10^3 scf), boe (BOE), co2e (tonne)
hbns_months_2022 = [
    {"m": 1, "oil": 2283670.0, "gas_mscf": 2426621.0, "boe": 2856219.0, "co2": 86851.92, "ch4": 225.29, "n2o": 1.35, "co2e": 92887.56, "energy_hhv": 1178501.33},
    {"m": 2, "oil": 2067587.0, "gas_mscf": 2008081.0, "boe": 2541383.0, "co2": 78489.94, "ch4": 219.82, "n2o": 1.21, "co2e": 84347.31, "energy_hhv": 1054686.77},
    {"m": 3, "oil": 2158103.0, "gas_mscf": 2400611.0, "boe": 2724515.0, "co2": 84069.69, "ch4": 217.10, "n2o": 1.31, "co2e": 89887.25, "energy_hhv": 1167044.43},
    {"m": 4, "oil": 2242328.0, "gas_mscf": 2415140.0, "boe": 2812168.0, "co2": 80071.98, "ch4": 201.96, "n2o": 1.26, "co2e": 85497.22, "energy_hhv": 1174234.86},
    {"m": 5, "oil": 2437609.0, "gas_mscf": 2476272.0, "boe": 3021873.0, "co2": 81431.13, "ch4": 199.30, "n2o": 1.29, "co2e": 86799.03, "energy_hhv": 1214123.94},
    {"m": 6, "oil": 2143683.0, "gas_mscf": 2326535.0, "boe": 2692617.0, "co2": 80109.11, "ch4": 215.82, "n2o": 1.25, "co2e": 85877.57, "energy_hhv": 1105732.47},
    {"m": 7, "oil": 2305494.0, "gas_mscf": 2484862.0, "boe": 2891785.0, "co2": 82669.59, "ch4": 210.32, "n2o": 1.30, "co2e": 88315.29, "energy_hhv": 1179461.43},
    {"m": 8, "oil": 2400299.0, "gas_mscf": 2545954.0, "boe": 3001004.0, "co2": 86063.67, "ch4": 217.70, "n2o": 1.35, "co2e": 91909.89, "energy_hhv": 1200273.50},
    {"m": 9, "oil": 1630620.0, "gas_mscf": 1939635.0, "boe": 2088267.0, "co2": 68140.98, "ch4": 224.19, "n2o": 1.04, "co2e": 74056.69, "energy_hhv": 846242.41},
    {"m": 10, "oil": 2287347.0, "gas_mscf": 2641257.0, "boe": 2910538.0, "co2": 94232.94, "ch4": 263.26, "n2o": 1.45, "co2e": 101246.35, "energy_hhv": 1110315.64},
    {"m": 11, "oil": 2300704.0, "gas_mscf": 2399583.0, "boe": 2866873.0, "co2": 83950.85, "ch4": 217.29, "n2o": 1.33, "co2e": 89778.48, "energy_hhv": 1168249.92},
    {"m": 12, "oil": 2305802.0, "gas_mscf": 2472189.0, "boe": 2889102.0, "co2": 85523.82, "ch4": 217.71, "n2o": 1.34, "co2e": 91365.98, "energy_hhv": 1192675.56},
]

# El Merk 2022 Monthly Data (From Tables B-4b and B-4c)
elm_months_2022 = [
    {"m": 1, "oil": 1969265.0, "gas_mscf": 803068.0, "boe": 2128783.0, "co2": 65300.50, "ch4": 373.84, "n2o": 1.03, "co2e": 74952.50, "energy_hhv": 672716.20},
    {"m": 2, "oil": 0.0, "gas_mscf": 15477.0, "boe": 3114.0, "co2": 2750.77, "ch4": 275.27, "n2o": 0.04, "co2e": 9644.16, "energy_hhv": 15565.52},
    {"m": 3, "oil": 2087902.0, "gas_mscf": 2178622.0, "boe": 2535080.0, "co2": 157772.55, "ch4": 791.85, "n2o": 2.29, "co2e": 178252.73, "energy_hhv": 543159.57},
    {"m": 4, "oil": 3047675.0, "gas_mscf": 1134761.0, "boe": 3299464.0, "co2": 93825.86, "ch4": 380.66, "n2o": 1.44, "co2e": 103772.58, "energy_hhv": 1063474.93},
    {"m": 5, "oil": 3342353.0, "gas_mscf": 1236198.0, "boe": 3587301.0, "co2": 93100.10, "ch4": 354.89, "n2o": 1.57, "co2e": 102438.72, "energy_hhv": 1220531.23},
    {"m": 6, "oil": 3212131.0, "gas_mscf": 1264997.0, "boe": 3461445.0, "co2": 94987.61, "ch4": 384.02, "n2o": 1.55, "co2e": 105048.98, "energy_hhv": 1123828.95},
    {"m": 7, "oil": 3321987.0, "gas_mscf": 1105973.0, "boe": 3547090.0, "co2": 89216.51, "ch4": 342.97, "n2o": 1.47, "co2e": 98227.87, "energy_hhv": 1185208.06},
    {"m": 8, "oil": 3269765.0, "gas_mscf": 1220519.0, "boe": 3510410.0, "co2": 89923.02, "ch4": 354.03, "n2o": 1.49, "co2e": 99217.18, "energy_hhv": 1162949.75},
    {"m": 9, "oil": 3067459.0, "gas_mscf": 1147656.0, "boe": 3295592.0, "co2": 85496.94, "ch4": 339.33, "n2o": 1.44, "co2e": 94409.09, "energy_hhv": 1157607.82},
    {"m": 10, "oil": 3201482.0, "gas_mscf": 1148593.0, "boe": 3429885.0, "co2": 85250.77, "ch4": 330.92, "n2o": 1.43, "co2e": 93950.59, "energy_hhv": 1182043.49},
    {"m": 11, "oil": 3046889.0, "gas_mscf": 1021664.0, "boe": 3249658.0, "co2": 80423.74, "ch4": 322.66, "n2o": 1.36, "co2e": 88896.55, "energy_hhv": 1134854.65},
    {"m": 12, "oil": 3038068.0, "gas_mscf": 1175858.0, "boe": 3269574.0, "co2": 94445.16, "ch4": 379.28, "n2o": 1.57, "co2e": 104394.89, "energy_hhv": 1156632.26},
]

# Multi-stream Gas Assays (From Table 6 and Table 13)
stream_assays = [
    # HBNS (Table 6)
    {
        "facility_id": 37,
        "name": "HBNS Fuel Gas Stream Assay",
        "stream_type": "Fuel Gas",
        "carbon_content": 0.771,
        "c1": 0.684, "c2": 0.172, "c3": 0.101, "c4": 0.023, "c5": 0.005,
        "c6": 0.002, "c7": 0.001, "c8": 0.001, "co2": 0.006,
        "hhv_btu_scf": 1362.97, "mw": 23.01
    },
    # El Merk (Table 13 - 7 streams)
    {
        "facility_id": 38,
        "name": "El Merk Fuel Gas / Flare AP Assay",
        "stream_type": "Fuel Gas / Flare AP",
        "carbon_content": 0.745,
        "c1": 0.781, "c2": 0.171, "c3": 0.020, "c4": 0.005, "c5": 0.002,
        "c6": 0.001, "c7": 0.000, "c8": 0.000, "co2": 0.014,
        "hhv_btu_scf": 1167.69, "mw": 19.82
    },
    {
        "facility_id": 38,
        "name": "El Merk Flare HP Stream Assay",
        "stream_type": "Flare HP",
        "carbon_content": 0.752,
        "c1": 0.752, "c2": 0.167, "c3": 0.038, "c4": 0.012, "c5": 0.004,
        "c6": 0.004, "c7": 0.002, "c8": 0.001, "co2": 0.014,
        "hhv_btu_scf": 1241.39, "mw": 21.25
    },
    {
        "facility_id": 38,
        "name": "El Merk Flare HPLT Stream Assay",
        "stream_type": "Flare HPLT",
        "carbon_content": 0.745,
        "c1": 0.777, "c2": 0.176, "c3": 0.019, "c4": 0.004, "c5": 0.002,
        "c6": 0.001, "c7": 0.001, "c8": 0.000, "co2": 0.016,
        "hhv_btu_scf": 1173.95, "mw": 19.96
    },
    {
        "facility_id": 38,
        "name": "El Merk Flare LP Stream Assay",
        "stream_type": "Flare LP",
        "carbon_content": 0.745,
        "c1": 0.781, "c2": 0.171, "c3": 0.020, "c4": 0.005, "c5": 0.002,
        "c6": 0.001, "c7": 0.000, "c8": 0.000, "co2": 0.015,
        "hhv_btu_scf": 1167.02, "mw": 19.81
    },
    {
        "facility_id": 38,
        "name": "El Merk Flare NGL Stream Assay",
        "stream_type": "Flare NGL",
        "carbon_content": 0.755,
        "c1": 0.736, "c2": 0.170, "c3": 0.045, "c4": 0.017, "c5": 0.005,
        "c6": 0.003, "c7": 0.001, "c8": 0.001, "co2": 0.014,
        "hhv_btu_scf": 1259.71, "mw": 21.55
    },
    {
        "facility_id": 38,
        "name": "El Merk Flare OT1 Stream Assay",
        "stream_type": "Flare OT1",
        "carbon_content": 0.754,
        "c1": 0.708, "c2": 0.200, "c3": 0.046, "c4": 0.014, "c5": 0.005,
        "c6": 0.005, "c7": 0.001, "c8": 0.001, "co2": 0.015,
        "hhv_btu_scf": 1279.91, "mw": 22.10
    },
    {
        "facility_id": 38,
        "name": "El Merk Flare OT2 Stream Assay",
        "stream_type": "Flare OT2",
        "carbon_content": 0.753,
        "c1": 0.708, "c2": 0.200, "c3": 0.046, "c4": 0.014, "c5": 0.005,
        "c6": 0.004, "c7": 0.001, "c8": 0.001, "co2": 0.021,
        "hhv_btu_scf": 1278.04, "mw": 22.06
    }
]


def seed():
    with app.app_context():
        # 1. Seed Monthly ProductionData for HBNS
        print("Seeding monthly ProductionData for HBNS (37)...")
        for row in hbns_months_2022:
            existing = ProductionData.query.filter_by(facility_id=37, year=2022, month=row["m"]).first()
            if not existing:
                existing = ProductionData(facility_id=37, year=2022, month=row["m"])
                db.session.add(existing)
            existing.oil_amount = row["oil"]
            existing.gas_amount = row["gas_mscf"]
            existing.oil_unit = "bbl"
            existing.gas_unit = "mscf"
            # Gross gas mmsm3 approx conversion
            existing.gross_gas_mmsm3 = row["gas_mscf"] * 0.0283168 / 1000.0 * 2.3
            existing.gas_without_injected_mmsm3 = row["gas_mscf"] * 0.0283168 / 1000.0
            existing.injected_gas_mmsm3 = existing.gross_gas_mmsm3 - existing.gas_without_injected_mmsm3

        # 2. Seed Monthly ProductionData for El Merk
        print("Seeding monthly ProductionData for El Merk (38)...")
        for row in elm_months_2022:
            existing = ProductionData.query.filter_by(facility_id=38, year=2022, month=row["m"]).first()
            if not existing:
                existing = ProductionData(facility_id=38, year=2022, month=row["m"])
                db.session.add(existing)
            existing.oil_amount = row["oil"]
            existing.gas_amount = row["gas_mscf"]
            existing.oil_unit = "bbl"
            existing.gas_unit = "mscf"
            existing.gross_gas_mmsm3 = row["gas_mscf"] * 0.0283168 / 1000.0 * 2.8
            existing.gas_without_injected_mmsm3 = row["gas_mscf"] * 0.0283168 / 1000.0
            existing.injected_gas_mmsm3 = existing.gross_gas_mmsm3 - existing.gas_without_injected_mmsm3

        # 3. Seed Multi-stream Gas Assays in CustomFactor
        print("Seeding multi-stream gas assays in CustomFactor...")
        for assay in stream_assays:
            comp_dict = {
                "stream_type": assay["stream_type"],
                "carbon_content": assay["carbon_content"],
                "c1": assay["c1"],
                "c2": assay["c2"],
                "c3": assay["c3"],
                "c4": assay["c4"],
                "c5": assay["c5"],
                "c6": assay["c6"],
                "c7": assay["c7"],
                "c8": assay["c8"],
                "co2": assay["co2"],
                "hhv_btu_scf": assay["hhv_btu_scf"],
                "mw_kg_mole": assay["mw"]
            }
            cf = CustomFactor.query.filter_by(facility_id=assay["facility_id"], name=assay["name"]).first()
            if not cf:
                cf = CustomFactor(
                    facility_id=assay["facility_id"],
                    name=assay["name"],
                    parent_fuel="natural_gas",
                    source="Gas Chromatography Laboratory Assay",
                    unit="m3",
                    hhv_factor=assay["hhv_btu_scf"],
                    status="Approved"
                )
                db.session.add(cf)
            cf.gas_composition_json = json.dumps(comp_dict)
            cf.hhv_factor = assay["hhv_btu_scf"]
            cf.description = f"MW={assay['mw']}, Carbon Frac={assay['carbon_content']}, Stream={assay['stream_type']}"

        db.session.commit()
        print("Seeding completed successfully!")


if __name__ == "__main__":
    seed()
