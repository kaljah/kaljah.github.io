import sys
import os
import json
import uuid

# Add server directory to path
sys.path.insert(0, os.path.abspath("."))

from app import app
from extensions import db
from models import User, Facility, Emission
from calculations import compute_emissions
from emission_factors import API_FACTORS, EQUIPMENT_FACTORS


def run_all_scenarios():
    with app.app_context():
        # Ensure database tables exist
        db.create_all()

        user = User.query.filter_by(email="aze@aze").first()
        if not user:
            print("Error: aze@aze user not found.")
            return

        facility = Facility.query.first()
        if not facility:
            facility = Facility(
                name="Hassi Messaoud Production Center",
                location="Ouargla",
                activity="Upstream Oil & Gas",
                division="Exploration & Production",
                region="South",
                field="OF",
                code="HMD-01",
                segment="Upstream",
                created_by=user.id,
            )
            db.session.add(facility)
            db.session.commit()

        # Clean existing test records for fresh clean state
        Emission.query.filter_by(created_by=user.id).delete()
        db.session.commit()

        scenarios = [
            # 1. PNEUMATIC DEVICES
            {
                "name": "Pneumatics (Tier 1 Default)",
                "process_type": "pneumatic",
                "factor_source": "default",
                "fuel": "Pneumatic Controller - High Bleed (>6 scfh)",
                "quantity": 100,
                "unit": "devices",
                "year": 2026,
                "month": 1,
                "calc_inputs": {},
            },
            {
                "name": "Pneumatics (Tier 3 Specific)",
                "process_type": "pneumatic",
                "factor_source": "specific",
                "quantity": 100,
                "unit": "devices",
                "year": 2026,
                "month": 1,
                "calc_inputs": {
                    "pneumatic": {
                        "pneu_count": 100,
                        "pneu_bleed_rate": 15.4,
                        "pneu_bleed_unit": "scf",
                        "pneu_hours": 8760,
                        "pneu_ch4_content": 85.0,
                    }
                },
            },
            # 2. STATIONARY COMBUSTION
            {
                "name": "Combustion (Tier 1 Default)",
                "process_type": "combustion",
                "factor_source": "default",
                "fuel": "Natural Gas",
                "quantity": 10000,
                "unit": "MMBtu",
                "year": 2026,
                "month": 2,
                "calc_inputs": {},
            },
            {
                "name": "Combustion (Tier 3 Specific)",
                "process_type": "combustion",
                "factor_source": "specific",
                "quantity": 500000,
                "unit": "m3",
                "year": 2026,
                "month": 2,
                "calc_inputs": {
                    "combustion": {
                        "amount": 500000,
                        "unit": "m3",
                        "hhv": 1020,
                        "c1": 85.0,
                        "c2": 8.0,
                        "c3": 4.0,
                        "c4": 1.5,
                        "c5": 0.5,
                        "co2_mol": 1.0,
                        "n2": 0.0,
                        "combustion_efficiency": 99.5,
                    }
                },
            },
            # 3. FLARING
            {
                "name": "Flaring (Tier 1 Default)",
                "process_type": "flaring",
                "factor_source": "default",
                "fuel": "Natural Gas (Flaring - Elevated)",
                "quantity": 50000,
                "unit": "m3",
                "year": 2026,
                "month": 3,
                "calc_inputs": {},
            },
            {
                "name": "Flaring (Tier 3 Specific)",
                "process_type": "flaring",
                "factor_source": "specific",
                "quantity": 100000,
                "unit": "m3",
                "year": 2026,
                "month": 3,
                "calc_inputs": {
                    "flaring": {
                        "gas_volume": 100000,
                        "unit": "m3",
                        "flare_type": "elevated",
                        "flare_ch4_content": 80.0,
                        "c1": 80.0,
                        "c2": 10.0,
                        "c3": 5.0,
                        "co2_content": 3.0,
                        "n2": 2.0,
                        "combustion_efficiency": 98.0,
                    }
                },
            },
            # 4. DRILLING / MUD DEGASSING
            {
                "name": "Drilling (Tier 1 Default)",
                "process_type": "drilling",
                "factor_source": "default",
                "fuel": "Drilling - Mud Degassing (Water Based)",
                "quantity": 1000,
                "unit": "m3",
                "year": 2026,
                "month": 4,
                "calc_inputs": {},
            },
            {
                "name": "Drilling (Tier 3 Specific)",
                "process_type": "drilling",
                "factor_source": "specific",
                "quantity": 2500,
                "unit": "m3",
                "year": 2026,
                "month": 4,
                "calc_inputs": {"drilling": {"mud_vol": 2500, "mud_type": "oil_based"}},
            },
            # 5. WELL COMPLETIONS FLOWBACK
            {
                "name": "Completions (Tier 1 Default)",
                "process_type": "completions",
                "factor_source": "default",
                "fuel": "Natural Gas (Venting/Blowdown)",
                "quantity": 10000,
                "unit": "m3",
                "year": 2026,
                "month": 5,
                "calc_inputs": {},
            },
            {
                "name": "Completions (Tier 3 Specific)",
                "process_type": "completions",
                "factor_source": "specific",
                "quantity": 25000,
                "unit": "m3",
                "year": 2026,
                "month": 5,
                "calc_inputs": {
                    "completions": {
                        "flowback_volume": 25000,
                        "comp_ch4_content": 85.0,
                        "co2_content": 2.0,
                        "comp_control_eff": 95.0,
                    }
                },
            },
            # 6. LIQUIDS UNLOADING
            {
                "name": "Unloading (Tier 1 Default)",
                "process_type": "liquids_unloading",
                "factor_source": "default",
                "fuel": "Natural Gas (Venting/Blowdown)",
                "quantity": 5000,
                "unit": "m3",
                "year": 2026,
                "month": 6,
                "calc_inputs": {},
            },
            {
                "name": "Unloading (Tier 3 Specific)",
                "process_type": "liquids_unloading",
                "factor_source": "specific",
                "quantity": 12,
                "unit": "events",
                "year": 2026,
                "month": 6,
                "calc_inputs": {
                    "liquids_unloading": {
                        "well_depth": 8000,
                        "unload_depth": 8000,
                        "casing_diameter": 4.5,
                        "unload_diam": 4.5,
                        "shut_in_pressure": 250,
                        "unload_press": 250,
                        "unloading_events": 12,
                        "unload_events": 12,
                        "unload_ch4_content": 88.0,
                        "ch4_content": 88.0,
                        "co2_content": 2.0,
                    }
                },
            },
            # 7. BLOWDOWN / VENTING
            {
                "name": "Blowdown (Tier 1 Default)",
                "process_type": "blowdown",
                "factor_source": "default",
                "fuel": "Natural Gas (Venting/Blowdown)",
                "quantity": 50000,
                "unit": "m3",
                "year": 2026,
                "month": 7,
                "calc_inputs": {},
            },
            {
                "name": "Blowdown (Tier 3 Specific)",
                "process_type": "blowdown",
                "factor_source": "specific",
                "quantity": 8,
                "unit": "events",
                "year": 2026,
                "month": 7,
                "calc_inputs": {
                    "blowdown": {
                        "blowdown_volume": 150,
                        "blowdown_pressure": 600,
                        "blowdown_events": 8,
                        "ch4_content": 82.0,
                        "co2_content": 3.0,
                    }
                },
            },
            # 8. STORAGE TANKS
            {
                "name": "Tanks (Tier 1 Default)",
                "process_type": "storage_tanks",
                "factor_source": "default",
                "fuel": "Tank - Crude Oil (Large, >10 bbl/d)",
                "quantity": 50000,
                "unit": "bbl",
                "year": 2026,
                "month": 8,
                "calc_inputs": {},
            },
            {
                "name": "Tanks (Tier 3 Specific)",
                "process_type": "storage_tanks",
                "factor_source": "specific",
                "quantity": 100000,
                "unit": "bbl",
                "year": 2026,
                "month": 8,
                "calc_inputs": {
                    "storage_tanks": {
                        "amount": 100000,
                        "tank_gor": 45.0,
                        "tank_ch4_content": 75.0,
                        "tank_control_eff": 98.0,
                    }
                },
            },
            # 9. ACID GAS REMOVAL (AGR)
            {
                "name": "AGR (Tier 1 Default)",
                "process_type": "agr",
                "factor_source": "default",
                "fuel": "Gathering - AGRU",
                "quantity": 10,
                "unit": "units",
                "year": 2026,
                "month": 9,
                "calc_inputs": {},
            },
            {
                "name": "AGR (Tier 3 Specific)",
                "process_type": "agr",
                "factor_source": "specific",
                "quantity": 10000000,
                "unit": "m3",
                "year": 2026,
                "month": 9,
                "calc_inputs": {
                    "agr": {
                        "agr_feed_rate": 10000000,
                        "agr_co2_in": 8.0,
                        "agr_co2_out": 1.5,
                        "agr_ch4_content": 0.5,
                        "agr_control_eff": 98.0,
                    }
                },
            },
            # 10. GLYCOL DEHYDRATORS
            {
                "name": "Dehydrator (Tier 1 Default)",
                "process_type": "dehydrator",
                "factor_source": "default",
                "fuel": "Dehydrator - Glycol (Uncontrolled)",
                "quantity": 5,
                "unit": "units",
                "year": 2026,
                "month": 10,
                "calc_inputs": {},
            },
            {
                "name": "Dehydrator (Tier 3 Specific)",
                "process_type": "dehydrator",
                "factor_source": "specific",
                "quantity": 5000000,
                "unit": "m3",
                "year": 2026,
                "month": 10,
                "calc_inputs": {
                    "dehydrator": {
                        "dehy_throughput": 5000000,
                        "dehy_pump_rate": 4.5,
                        "dehy_hours": 8760,
                        "dehy_ch4_content": 85.0,
                        "dehy_control_eff": 95.0,
                    }
                },
            },
            # 11. FUGITIVES
            {
                "name": "Fugitives (Tier 1 Default)",
                "process_type": "fugitive",
                "factor_source": "default",
                "fuel": "Component - Control Valve",
                "quantity": 500,
                "unit": "count",
                "year": 2026,
                "month": 11,
                "calc_inputs": {},
            },
            {
                "name": "Fugitives (Tier 3 Specific)",
                "process_type": "fugitive",
                "factor_source": "specific",
                "quantity": 250,
                "unit": "count",
                "year": 2026,
                "month": 11,
                "calc_inputs": {
                    "fugitive": {
                        "fugitive_type": "equipment_level",
                        "equipment_type": "wellhead",
                        "component_count": 250,
                        "operating_hours": 8760,
                        "gas_ch4_content": 85.0,
                        "control_efficiency": 0.0,
                    }
                },
            },
        ]

        print(
            f"Executing {len(scenarios)} Tier 1 and Tier 3 scenarios across all process categories..."
        )
        print("=" * 110)

        results_summary = []

        for s in scenarios:
            data = {
                "process_type": s["process_type"],
                "fuel": s.get("fuel"),
                "quantity": s["quantity"],
                "unit": s["unit"],
                "year": s["year"],
                "month": s["month"],
                "facility_id": facility.id,
                "factor_source": s["factor_source"],
                "calc_inputs": s.get("calc_inputs", {}),
            }

            fuel_name = s.get("fuel")
            factor_data = {}
            if fuel_name:
                factor_data = (
                    API_FACTORS.get(fuel_name) or EQUIPMENT_FACTORS.get(fuel_name) or {}
                )

            try:
                em_result, method = compute_emissions(data, factor_data)

                co2_t = float(em_result.get("co2") or 0.0)
                ch4_t = float(em_result.get("ch4") or 0.0)
                n2o_t = float(em_result.get("n2o") or 0.0)
                total_co2e = float(em_result.get("totalCo2e") or 0.0)

                # Save record in DB for UI display
                em = Emission(
                    record_id=f"SCEN-{uuid.uuid4().hex[:8].upper()}",
                    created_by=user.id,
                    facility_id=facility.id,
                    company_name="Sonatrach",
                    group_name="Scope 1 Verification Suite",
                    equipment_id=s["name"],
                    process_type=s["process_type"],
                    fuel_type=s.get("fuel") or "-",
                    quantity=s["quantity"],
                    unit=s["unit"],
                    co2_emissions=co2_t,
                    ch4_emissions=ch4_t,
                    n2o_emissions=n2o_t,
                    co2e_total=total_co2e,
                    calc_method=s["factor_source"].capitalize(),
                    factor_source=s["factor_source"],
                    source_payload=json.dumps(data),
                    activity=facility.activity,
                    division=facility.division,
                    region=facility.region,
                    field=facility.field,
                    year=s["year"],
                    month=s["month"],
                )
                db.session.add(em)

                results_summary.append(
                    {
                        "name": s["name"],
                        "tier": (
                            "Tier 3 (Specific)"
                            if s["factor_source"] == "specific"
                            else "Tier 1 (Default)"
                        ),
                        "process": s["process_type"],
                        "co2_t": co2_t,
                        "ch4_t": ch4_t,
                        "n2o_t": n2o_t,
                        "total_co2e": total_co2e,
                        "status": "SUCCESS",
                    }
                )
                print(
                    f"[OK] {s['name']:<35} | CO2: {co2_t:>10.3f} T | CH4: {ch4_t:>10.3f} T | N2O: {n2o_t:>8.4f} T | Total CO2e: {total_co2e:>12.3f} T"
                )
            except Exception as e:
                print(f"[FAILED] {s['name']:<35} | Error: {e}")
                results_summary.append(
                    {"name": s["name"], "status": "FAILED", "error": str(e)}
                )

        db.session.commit()
        print("=" * 110)
        print(
            f"Successfully processed {len(results_summary)} scenarios ({len([r for r in results_summary if r.get('status') == 'SUCCESS'])} OK, {len([r for r in results_summary if r.get('status') == 'FAILED'])} Failed)."
        )


if __name__ == "__main__":
    run_all_scenarios()
