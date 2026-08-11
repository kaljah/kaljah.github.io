from flask import Blueprint, request, jsonify, session
from models import User, Scope2Emission, Facility
from extensions import db
from sqlalchemy import func
from electricity_factors import GRID_FACTORS
from routes.auth import login_required
from calculations.uncertainty import propagate_uncertainty, Tier

scope2_bp = Blueprint("scope2", __name__)

# Default emission factor for natural-gas-fired boilers (indirect steam)
# Per EPA AP-42 / API Compendium: ~53.06 kg CO2/MMBtu for natural gas
_DEFAULT_BOILER_EF_KG_PER_MMBTU = 53.06


def _calc_indirect_steam(data):
    """Calculate tCO2e for indirect steam / heat entry."""
    amount = float(data.get("amount", 0))
    unit = (data.get("unit") or "mmbtu").lower().replace(" ", "")
    ci = data.get("calc_inputs", {}).get("indirect_steam", {})
    boiler_eff = float(ci.get("boiler_eff", 0.80))
    trans_loss = float(ci.get("trans_loss", 0.0))
    ef_co2 = float(ci.get("ef_co2", _DEFAULT_BOILER_EF_KG_PER_MMBTU))

    # Normalise input to MMBtu
    # Conversion factors:
    #   1 BTU  = 1/1,000,000 MMBtu
    #   1 MJ   = 947.817 BTU  → 0.000947817 MMBtu
    #   1 GJ   = 1,000 MJ     → 0.947817 MMBtu  (= 1/1.05505585)
    #   1 kWh  = 3,412.142 BTU → 0.003412142 MMBtu
    #   1 MWh  = 3,412,142 BTU → 3.412142 MMBtu
    if unit in ["btu"]:
        energy_mmbtu = amount / 1_000_000.0
    elif unit in ["mj", "megajoule", "mega_joule"]:
        energy_mmbtu = amount * 0.000947817  # 1 MJ = 0.000947817 MMBtu
    elif unit in ["gj", "gigajoule"]:
        energy_mmbtu = amount * 0.947817  # 1 GJ = 0.947817 MMBtu
    elif unit in ["kwh", "kw-hr", "kilowatthour"]:
        energy_mmbtu = amount * 0.003412142
    elif unit in ["mwh", "mw-hr"]:
        energy_mmbtu = amount * 3.412142
    else:  # assume already in MMBtu
        energy_mmbtu = amount

    net_eff = (boiler_eff - trans_loss) if (boiler_eff - trans_loss) > 0 else 0.80
    co2_kg = (energy_mmbtu * ef_co2) / net_eff
    return co2_kg / 1000.0, energy_mmbtu, ef_co2


def _calc_cogen_allocation(data):
    """Calculate heat-allocated tCO2e for CHP / cogeneration entry."""
    val = float(data.get("amount", 0))  # total facility emissions in tCO2e
    ci = data.get("calc_inputs", {}).get("cogen_allocation", {})
    total_emissions = float(ci.get("total_emissions", val))
    heat_output = float(ci.get("heat_output", 0))
    power_output = float(ci.get("power_output", 0))
    method = ci.get("allocation_method", "wri_efficiency")

    if method == "wri_efficiency":
        e_h, e_p = 0.8, 0.33
        denom = (heat_output / e_h) + (power_output / e_p)
        allocated = ((heat_output / e_h) / denom) * total_emissions if denom else 0
    else:
        denom = heat_output + power_output
        allocated = (heat_output / denom) * total_emissions if denom else 0
    return allocated


@scope2_bp.route("", methods=["GET"])
@login_required
def get_scope2_emissions():
    """Get all Scope 2 emissions"""
    # Standard error handling
    try:
        user = User.query.get(session.get("user_id"))
        if user and user.role != "admin":
            emissions = Scope2Emission.query.filter(
                Scope2Emission.created_by == user.id
            ).all()
        else:
            emissions = Scope2Emission.query.all()
        return jsonify(
            [
                {
                    "id": e.id,
                    "facility_id": e.facility_id,
                    "year": e.year,
                    "month": e.month,
                    "source_type": e.source_type,
                    "electricity_kwh": float(e.electricity_kwh or 0),
                    "steam_ton": float(e.steam_ton or 0),
                    "heat_mmbtu": float(e.heat_mmbtu or 0),
                    "cooling_ton": float(e.cooling_ton or 0),
                    "emission_factor": float(e.emission_factor or 0),
                    "co2e": float(e.co2e or 0),
                    "location": e.location,
                    "grid_region": e.grid_region,
                    "activity": e.activity,
                    "division": e.division,
                    "field": e.field,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in emissions
            ]
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@scope2_bp.route("", methods=["POST"])
@login_required
def create_scope2_emission():
    """Create a new Scope 2 emission record"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    source_type = data.get("source_type", "electricity")

    # --- Run calculation for non-electricity types ---
    co2e = float(data.get("co2e", 0))
    emission_factor = float(data.get("emission_factor", 0))
    electricity_kwh = float(data.get("electricity_kwh", 0))
    heat_mmbtu = 0.0

    if source_type == "indirect_steam":
        try:
            co2e, heat_mmbtu, emission_factor = _calc_indirect_steam(data)
        except Exception as exc:
            return jsonify({"error": f"Indirect steam calculation failed: {exc}"}), 422

    elif source_type == "cogen_allocation":
        try:
            co2e = _calc_cogen_allocation(data)
        except Exception as exc:
            return jsonify({"error": f"CHP allocation calculation failed: {exc}"}), 422

    # Calculate uncertainty
    provided_uncertainty = data.get("uncertainty")
    if provided_uncertainty is not None:
        final_uncertainty = float(provided_uncertainty)
    else:
        # Default Scope 2 uncertainty (5% EF, 2% AD -> ~5.4% combined)
        u_res = propagate_uncertainty(
            co2e,
            ef_uncertainty=0.05,
            activity_uncertainty=0.02,
            tier=Tier.T2,
            process_category="scope2",
            gas="co2",
        )
        final_uncertainty = u_res["relative_uncertainty"]

    emission = Scope2Emission(
        facility_id=data.get("facility_id"),
        year=data.get("year"),
        month=data.get("month"),
        source_type=source_type,
        electricity_kwh=electricity_kwh,
        steam_ton=data.get("steam_ton") or data.get("stream_ton", 0),
        heat_mmbtu=heat_mmbtu,
        cooling_ton=data.get("cooling_ton", 0),
        emission_factor=emission_factor,
        co2e=co2e,
        uncertainty=final_uncertainty,
        location=data.get("location"),
        grid_region=data.get("grid_region"),
        activity=data.get("activity"),
        division=data.get("division"),
        field=data.get("field"),
        created_by=user_id,
    )

    db.session.add(emission)
    db.session.commit()

    return (
        jsonify(
            {"message": "Scope 2 emission created", "id": emission.id, "co2e": co2e}
        ),
        201,
    )


@scope2_bp.route("/<int:emission_id>", methods=["PUT"])
@login_required
def update_scope2_emission(emission_id):
    """Update a Scope 2 emission record"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    emission = Scope2Emission.query.get(emission_id)
    user = User.query.get(session.get("user_id"))
    if user and user.role != "admin" and emission and emission.created_by != user.id:
        return jsonify({"error": "Unauthorized"}), 403
    if not emission:
        return jsonify({"error": "Emission not found"}), 404

    data = request.get_json()

    if "facility_id" in data:
        emission.facility_id = data["facility_id"]
    if "year" in data:
        emission.year = data["year"]
    if "month" in data:
        emission.month = data["month"]
    if "source_type" in data:
        emission.source_type = data["source_type"]
    if "electricity_kwh" in data:
        emission.electricity_kwh = data["electricity_kwh"]
    if "steam_ton" in data:
        emission.steam_ton = data["steam_ton"]
    if "heat_mmbtu" in data:
        emission.heat_mmbtu = data["heat_mmbtu"]
    if "cooling_ton" in data:
        emission.cooling_ton = data["cooling_ton"]
    if "emission_factor" in data:
        emission.emission_factor = data["emission_factor"]
    if "co2e" in data:
        emission.co2e = data["co2e"]
    if "uncertainty" in data:
        emission.uncertainty = data["uncertainty"]
    if "location" in data:
        emission.location = data["location"]
    if "grid_region" in data:
        emission.grid_region = data["grid_region"]

    db.session.commit()

    return jsonify({"message": "Scope 2 emission updated"})


@scope2_bp.route("/<int:emission_id>", methods=["DELETE"])
@login_required
def delete_scope2_emission(emission_id):
    """Delete a Scope 2 emission record"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    emission = Scope2Emission.query.get(emission_id)
    user = User.query.get(session.get("user_id"))
    if user and user.role != "admin" and emission and emission.created_by != user.id:
        return jsonify({"error": "Unauthorized"}), 403
    if not emission:
        return jsonify({"error": "Emission not found"}), 404

    db.session.delete(emission)
    db.session.commit()

    return jsonify({"message": "Scope 2 emission deleted"})


@scope2_bp.route("/bulk-import", methods=["POST"])
@login_required
def bulk_import_scope2():
    """Import Scope 2 emissions from CSV data"""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json()
    records = data.get("records", [])
    if not records:
        return jsonify({"error": "No records provided"}), 400

    imported_count = 0
    errors = []
    facility_cache = {}

    for i, rec in enumerate(records):
        try:
            # 1. Resolve facility
            f_val = rec.get("facility_id")
            facility = None
            if isinstance(f_val, str) and not str(f_val).isdigit():
                f_name_clean = f_val.strip()
                if f_name_clean.lower() in facility_cache:
                    facility = facility_cache[f_name_clean.lower()]
                else:
                    facility = Facility.query.filter(
                        func.lower(Facility.name) == f_name_clean.lower()
                    ).first()
                    facility_cache[f_name_clean.lower()] = facility
            else:
                try:
                    fid = int(f_val) if f_val else None
                    if fid in facility_cache:
                        facility = facility_cache[fid]
                    else:
                        facility = Facility.query.get(fid)
                        facility_cache[fid] = facility
                except (ValueError, TypeError):
                    facility = None

            if not facility:
                errors.append(f"Row {i}: Facility '{f_val}' not found")
                continue

            # 2. Get Factor and Calculate
            grid_region = rec.get("grid_region")
            factor_info = GRID_FACTORS.get(grid_region)
            if not factor_info:
                errors.append(f"Row {i}: Grid Region '{grid_region}' not found")
                continue

            ef = factor_info["factor"]
            # consumption in payload might be kwh, mwh, gwh. BulkImportModal uses 'consumption' and 'unit'
            val = float(rec.get("consumption") or 0)
            unit = rec.get("unit", "kWh")

            kwh = val
            if unit == "MWh":
                kwh = val * 1000
            elif unit == "GWh":
                kwh = val * 1000000

            co2e_val = (kwh * ef) / 1000

            # Default Scope 2 uncertainty
            u_res = propagate_uncertainty(
                co2e_val,
                ef_uncertainty=0.05,
                activity_uncertainty=0.02,
                tier=Tier.T2,
                process_category="scope2",
                gas="co2",
            )
            final_uncertainty = u_res["relative_uncertainty"]

            emission = Scope2Emission(
                facility_id=facility.id,
                year=int(rec.get("year", 2024)),
                month=int(rec.get("month", 1)),
                source_type="electricity",
                electricity_kwh=kwh,
                emission_factor=ef,
                co2e=co2e_val,
                uncertainty=final_uncertainty,
                grid_region=grid_region,
                location=grid_region,
                activity=rec.get("activity") or facility.activity,
                division=rec.get("division") or facility.division,
                field=rec.get("field") or facility.field,
                created_by=user_id,
            )
            db.session.add(emission)
            imported_count += 1
        except Exception as e:
            errors.append(f"Row {i}: {str(e)}")

    db.session.commit()
    return jsonify(
        {"message": f"Successfully imported {imported_count} records", "errors": errors}
    ), (200 if not errors else 207)


@scope2_bp.route("/emission-factors", methods=["GET"])
@login_required
def get_emission_factors():
    """Get emission factors by grid region"""
    factors = []
    for region, info in GRID_FACTORS.items():
        factors.append(
            {
                "region": region,
                "factor": info["factor"],
                "unit": info["unit"],
                "description": info["description"],
            }
        )

    return jsonify(factors)
