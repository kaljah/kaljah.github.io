from flask import Blueprint, request, jsonify, session, current_app
from models import User, Scope2Emission, Facility
from extensions import db
from sqlalchemy import func
from electricity_factors import GRID_FACTORS, grid_entry, grid_factor_kg_co2e_per_kwh
from routes.auth import login_required
from calculations.uncertainty import propagate_uncertainty, Tier
from utils import facility_access_error, get_current_user, get_allowed_facility_ids, require_facility_access, initial_record_status, log_activity_and_notify
from input_validation import ValidationError, parse_number, parse_year, parse_month, require_plausible_co2e
from services.scope2_gases import gas_split
import datetime

scope2_bp = Blueprint("scope2", __name__)

# Default emission factor for natural-gas-fired boilers (indirect steam)
# Per EPA AP-42 / API Compendium: ~53.06 kg CO2/MMBtu for natural gas
_DEFAULT_BOILER_EF_KG_PER_MMBTU = 53.06
MMBTU_PER_MWH = 3.412142
# Upper bound for a supplier-specific grid factor; the most carbon-intensive grids are ~1.2 kg CO2e/kWh.
MAX_GRID_EF_KG_PER_KWH = 2.0


def resolve_electricity_factor(grid_region, supplied_ef):
    """One Scope 2 electricity factor policy for manual, JSON-import and file-bulk paths (BUG-099).

    - Known grid region: the location-based grid factor; a client factor is ignored.
    - Otherwise: an explicit supplier / contractual factor (market-based instrument, e.g. a
      renewable PPA at 0) within [0, MAX_GRID_EF_KG_PER_KWH] kg CO2e/kWh.
    Returns (factor_kg_per_kwh, resolved_grid_region). Raises ValidationError otherwise.
    """
    from input_validation import ValidationError, parse_number

    name = str(grid_region or "").strip()
    canonical, entry = grid_entry(name) if name else (name, None)
    if entry is not None:
        # CO2 / CH4 / N2O of the grid (API Compendium Tables 8-2 / 8-6) with the active GWP set
        return grid_factor_kg_co2e_per_kwh(entry), canonical
    ef = parse_number(supplied_ef, "emission_factor", required=False, min_value=0, max_value=MAX_GRID_EF_KG_PER_KWH)
    if ef is None:
        raise ValidationError(
            f"Unknown grid region '{name}'. Select a known grid or provide a supplier emission factor (kg CO2e/kWh).",
            "grid_region",
        )
    return ef, name or None


def default_scope2_uncertainty(co2e):
    """Default Scope 2 uncertainty (5 % factor, 2 % activity -> ~5.4 % combined), 1-sigma fraction."""
    return propagate_uncertainty(
        co2e, ef_uncertainty=0.05, activity_uncertainty=0.02, tier=Tier.T2, process_category="scope2", gas="co2",
    )["relative_uncertainty"]


def _calc_indirect_steam(data):
    """Calculate tCO2e for indirect steam / heat entry."""
    amount = float(data.get("amount") or data.get("heat_mmbtu") or 0)
    unit = (data.get("unit") or "mmbtu").lower().replace(" ", "")
    ci = data.get("calc_inputs", {}).get("indirect_steam", {})
    raw_be = data.get("boiler_efficiency") or ci.get("boiler_eff") or 0.80
    boiler_eff = float(str(raw_be).replace("%", "").strip())
    if boiler_eff > 1.0 or "%" in str(raw_be):
        # 85 is 85 %, as in the file upload (no boiler runs at 1 %); it was used as 85 x, so the
        # manual form booked 1/100 of the emissions
        boiler_eff /= 100.0
    if not 0 < boiler_eff <= 1.0:
        raise ValidationError(f"Boiler efficiency must be above 0 and at most 100 % (got {raw_be})", "boiler_eff")
    trans_loss = float(ci.get("trans_loss", 0.0) or 0.0)
    if not 0 <= trans_loss < 1.0:
        raise ValidationError(f"Transmission loss is a fraction from 0 to below 1 (got {trans_loss}; 5 % is 0.05)",
                              "trans_loss")
    ef_co2 = float(ci.get("ef_co2", _DEFAULT_BOILER_EF_KG_PER_MMBTU))
    if 0 < ef_co2 < 1.0:
        ef_co2 = ef_co2 * 1000.0

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
    elif unit in ["ton", "us_ton", "short_ton"]:
        # Saturated steam: 1 US ton (~2000 lb) = 2.0 MMBtu (or specific enthalpy)
        enthalpy = float(ci.get("steam_enthalpy") or 2.0)
        energy_mmbtu = amount * enthalpy
    elif unit in ["tonne", "metric_ton", "mt"]:
        # 1 metric tonne = 2.20462 MMBtu (or specific enthalpy)
        enthalpy = float(ci.get("steam_enthalpy") or 2.20462)
        energy_mmbtu = amount * enthalpy
    elif unit in ["mlb", "klb", "thousand_lbs"]:
        # 1,000 lbs steam = 1.0 MMBtu
        energy_mmbtu = amount * 1.0
    elif unit in ["lb", "lbs", "pound", "pounds"]:
        energy_mmbtu = amount * 0.001
    elif unit in ["kg", "kilogram"]:
        energy_mmbtu = amount * 0.00220462
    elif unit in ["mmbtu", "mm_btu", "mmbtus"]:
        energy_mmbtu = amount
    else:
        # an unknown unit was booked as MMBtu (the file upload refuses it)
        raise ValidationError(f"Unknown unit '{data.get('unit')}' for indirect steam (MMBtu, GJ, MJ, kWh, MWh, "
                              "short_ton, tonne, klb, lb or kg)", "unit")

    net_eff = boiler_eff * (1.0 - trans_loss)
    if net_eff <= 0:
        raise ValueError(
            f"Net efficiency must be greater than 0 (got {net_eff:.4f}). "
            f"Check boiler efficiency ({boiler_eff}) and transmission loss ({trans_loss})."
        )
    fuel_mmbtu = energy_mmbtu / net_eff
    co2_kg = fuel_mmbtu * ef_co2
    if ef_co2 == _DEFAULT_BOILER_EF_KG_PER_MMBTU:
        # natural-gas boiler: CH4 / N2O of API Compendium Table 4-6 (1.0E-03 / 1.0E-04 kg per MMBtu of
        # fuel), the basis of EPA Emission Factors Hub Table 7 (1.25 / 0.125 g per MMBtu of steam at 80 %)
        from calculations.constants import get_active_gwp
        gwp = get_active_gwp()
        co2_kg += fuel_mmbtu * (0.001 * float(gwp["CH4"]) + 0.0001 * float(gwp["N2O"]))
    return co2_kg / 1000.0, energy_mmbtu, ef_co2


_STEAM_MASS_UNITS = {"ton", "tons", "tonne", "tonnes", "mt", "metric_ton", "us_ton", "short_ton", "mlb", "klb",
                     "thousand_lbs", "lb", "lbs", "pound", "pounds", "kg", "kilogram"}


def _steam_fuel_factor_kg_per_mmbtu(ef_co2):
    """kg CO2e per MMBtu of boiler fuel as _calc_indirect_steam applies it (CO2, plus the Table 4-6
    CH4 / N2O of the default natural-gas boiler)."""
    ef = float(ef_co2 or _DEFAULT_BOILER_EF_KG_PER_MMBTU)
    if 0 < ef < 1.0:
        ef *= 1000.0
    if ef == _DEFAULT_BOILER_EF_KG_PER_MMBTU:
        from calculations.constants import get_active_gwp
        gwp = get_active_gwp()
        ef += 0.001 * float(gwp["CH4"]) + 0.0001 * float(gwp["N2O"])
    return ef


def _recalc_indirect_steam(emission, data, factor, old_heat, old_co2e, old_ef, old_tons=None):
    """(co2e t, delivered heat MMBtu) of an edited steam record.

    The delivered energy is the stored heat_mmbtu, or the edited steam tonnage converted in the
    unit given. Boiler efficiency and transmission loss are not stored: unless the edit gives them,
    the record keeps the net efficiency it was calculated with (derived from its stored energy,
    factor and co2e) instead of falling back to 80 %.
    """
    tons = parse_number(data.get("steam_ton"), "steam_ton", required=False, min_value=0, default=0.0) \
        if "steam_ton" in data else 0.0
    ci = dict((data.get("calc_inputs") or {}).get("indirect_steam") or {})
    if data.get("steam_enthalpy") not in (None, ""):
        ci["steam_enthalpy"] = data["steam_enthalpy"]
    if tons > 0 and not data.get("unit") and not ci.get("steam_enthalpy") and old_tons and old_heat:
        # same steam as before: the record's own MMBtu per ton (its unit is not stored)
        heat = tons * float(old_heat) / float(old_tons)
    elif tons > 0:
        unit = str(data.get("unit") or "ton").lower().replace(" ", "")
        _, heat, _ = _calc_indirect_steam({"amount": tons, "unit": unit, "boiler_efficiency": 1.0,
                                           "calc_inputs": {"indirect_steam": ci}})
    else:
        heat = float(emission.heat_mmbtu or 0.0)
    given = any(data.get(k) not in (None, "") for k in ("boiler_eff", "boiler_efficiency", "trans_loss")) \
        or any(k in ci for k in ("boiler_eff", "trans_loss"))
    if not given and old_heat and old_co2e and float(old_heat) > 0 and float(old_co2e) > 0:
        net_eff = float(old_heat) * _steam_fuel_factor_kg_per_mmbtu(old_ef) / (float(old_co2e) * 1000.0)
        return round(heat / net_eff * _steam_fuel_factor_kg_per_mmbtu(factor) / 1000.0, 4), heat
    ci.setdefault("boiler_eff", float(data.get("boiler_eff") or data.get("boiler_efficiency") or 0.80))
    ci.setdefault("trans_loss", float(data.get("trans_loss") or 0.0))
    ci["ef_co2"] = factor or _DEFAULT_BOILER_EF_KG_PER_MMBTU
    co2e, _, _ = _calc_indirect_steam({"amount": heat, "unit": "mmbtu", "calc_inputs": {"indirect_steam": ci}})
    return round(co2e, 4), heat


def _calc_cogen_allocation(data):
    """Calculate heat-allocated tCO2e for CHP / cogeneration entry."""
    val = float(data.get("amount", 0) or data.get("co2e", 0) or data.get("total_emissions", 0))
    ci = data.get("calc_inputs", {}).get("cogen_allocation", {})
    total_emissions = float(data.get("total_emissions") or ci.get("total_emissions", val))
    if total_emissions == 0 and data.get("fuel_consumed_mmbtu"):
        # Calculate facility emissions from fuel consumed (e.g. 53.06 kg CO2/MMBtu)
        # natural gas: CO2 plus the Table 4-6 CH4 / N2O, as for the default steam boiler
        total_emissions = (float(data["fuel_consumed_mmbtu"]) * _steam_fuel_factor_kg_per_mmbtu(None)) / 1000.0
    heat_output = float(data.get("heat_output_mmbtu") or ci.get("heat_output", 0))
    power_output = float(data.get("power_output_mwh") or ci.get("power_output", 0))
    method = data.get("allocation_method") or ci.get("allocation_method", "wri_efficiency")
    if total_emissions <= 0 or (heat_output + power_output) <= 0:
        return 0.0
    # One allocation formula: calculations.indirect.CogenAllocationCalculator. Power output is
    # entered in MWh (BUG-097) and converted there.
    from calculations.indirect import CogenAllocationCalculator

    res = CogenAllocationCalculator().calculate(
        total_emissions=total_emissions, heat_output=heat_output, power_output=power_output,
        method="wri_efficiency" if method == "wri_efficiency" else "energy_content", power_unit="mwh",
        heat_efficiency=data.get("heat_efficiency") or ci.get("heat_efficiency"),
        power_efficiency=data.get("power_efficiency") or ci.get("power_efficiency"),
    )
    return res["metadata"]["allocated_heat_tonnes"]



def _page_args():
    """(limit, offset) when the caller asks for a page, else None (full list, the old contract)."""
    if request.args.get("limit") in (None, ""):
        return None
    try:
        limit = max(1, min(500, int(request.args.get("limit"))))
        offset = max(0, int(request.args.get("offset") or 0))
    except ValueError:
        return None
    return limit, offset

@scope2_bp.route("", methods=["GET"])
@login_required
def get_scope2_emissions():
    """Get all Scope 2 emissions, scoped to the requesting user's allowed facilities."""
    try:
        user = get_current_user()
        if user and user.role in ["it_admin", "it_manager", "it"]:
            return jsonify({"error": "IT personnel do not have access to emission data"}), 403

        allowed_fids = get_allowed_facility_ids(user)

        query = Scope2Emission.query
        # Apply facility-based RLS (same pattern as Scope 1 / Dashboard)
        if allowed_fids is not None:
            query = query.filter(Scope2Emission.facility_id.in_(allowed_fids))

        # Optional query-string filters
        year_arg = request.args.get("year")
        facility_arg = request.args.get("facilityId") or request.args.get("facility_id")
        if year_arg and year_arg != "all":
            try:
                query = query.filter(Scope2Emission.year == int(year_arg))
            except ValueError:
                pass
        if facility_arg and facility_arg != "all":
            try:
                query = query.filter(Scope2Emission.facility_id == int(facility_arg))
            except ValueError:
                pass

        # optional server-side paging (limit / offset): the tables used to download every record on
        # every page change (4 MB at 10,000 records) to show 10 rows
        query = query.order_by(Scope2Emission.created_at.desc(), Scope2Emission.id.desc())
        page_args = _page_args()
        total = query.count() if page_args else None
        if page_args:
            query = query.offset(page_args[1]).limit(page_args[0])
        emissions = query.all()
        rows = (
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
                    **gas_split(e),  # ADM-14: grid electricity split into CO2 / CH4 / N2O
                    "co2e_location_based": float(e.co2e_location_based if e.co2e_location_based is not None else (e.co2e or 0)),
                    "co2e_market_based": float(e.co2e_market_based if e.co2e_market_based is not None else (e.co2e or 0)),
                    "market_instrument_type": e.market_instrument_type,
                    "market_emission_factor": float(e.market_emission_factor) if e.market_emission_factor is not None else None,
                    "location": e.location,
                    "grid_region": e.grid_region,
                    "activity": e.activity,
                    "division": e.division,
                    "field": e.field,
                    # stored with the record; the table showed "—" without it (browser test)
                    "uncertainty": getattr(e, "uncertainty", None),
                    "status": getattr(e, "status", None),
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in emissions
            ]
        )
        if page_args:
            return jsonify({"data": rows, "total": total, "limit": page_args[0], "offset": page_args[1]})
        return jsonify(rows)
    except Exception as e:
        current_app.logger.exception(f"Failed to list Scope 2 emissions: {e}")
        return jsonify({"error": "Failed to load Scope 2 emissions"}), 500


@scope2_bp.route("", methods=["POST"])
@login_required
def create_scope2_emission():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["auditor", "it_admin", "it_manager", "it"]:
        return jsonify({"error": "Read-only or administrative role cannot create emission records"}), 403

    data = request.get_json() or {}
    facility_id = data.get("facility_id")
    if not facility_id:
        return jsonify({"error": "Missing facility_id"}), 422
    try:
        facility_id_int = int(facility_id)
    except (ValueError, TypeError):
        return jsonify({"error": "facility_id must be a valid integer"}), 422

    allowed_fids = get_allowed_facility_ids(user)
    if allowed_fids is not None and facility_id_int not in allowed_fids:
        return jsonify({"error": "Unauthorized for this facility"}), 403

    user_id = user.id
    source_type = data.get("source_type", "electricity")
    if source_type not in ("electricity", "indirect_steam", "cogen_allocation"):
        return jsonify({"error": f"Unsupported source_type '{source_type}'"}), 400

    # BUG-073: year/month are required and range-checked (a NULL year broke every dashboard).
    year_val = parse_year(data.get("year"))
    month_val = parse_month(data.get("month"))

    # BUG-099: CO2e is always computed server-side; a client-supplied co2e is ignored.
    co2e = 0.0
    co2e_location = 0.0
    co2e_market = 0.0
    emission_factor = 0.0
    market_ef = None
    market_instrument_type = (data.get("market_instrument_type") or "").strip() or None
    electricity_kwh = 0.0
    heat_mmbtu = 0.0

    if source_type == "electricity":
        electricity_kwh = parse_number(data.get("electricity_kwh"), "electricity_kwh", required=False, min_value=0, default=0.0)
        if electricity_kwh == 0 and data.get("amount") not in (None, ""):
            raw_amt = parse_number(data.get("amount"), "amount", min_value=0)
            raw_unit = str(data.get("unit") or "kwh").lower().strip()
            if raw_unit in ["mwh", "mw-hr", "megawatthour"]:
                electricity_kwh = raw_amt * 1000.0
            elif raw_unit in ["gwh", "gw-hr", "gigawatthour"]:
                electricity_kwh = raw_amt * 1_000_000.0
            elif raw_unit in ["kwh", "kw-hr", "kilowatthour"]:
                electricity_kwh = raw_amt
            else:
                return jsonify({"error": f"Unsupported electricity unit '{raw_unit}'"}), 400
        if electricity_kwh <= 0:
            return jsonify({"error": "'electricity_kwh' must be greater than 0"}), 400

        grid_region = data.get("grid_region") or data.get("location")
        location_ef, _ = resolve_electricity_factor(grid_region, data.get("emission_factor"))
        co2e_location = (electricity_kwh * location_ef) / 1000.0

        # Market-based calculation (GHG Protocol Scope 2 Guidance)
        raw_mkt_ef = data.get("market_emission_factor")
        if raw_mkt_ef not in (None, ""):
            market_ef = parse_number(raw_mkt_ef, "market_emission_factor", required=False, min_value=0, max_value=MAX_GRID_EF_KG_PER_KWH)
        elif market_instrument_type and market_instrument_type.lower() in ("rec", "ppa_zero", "go_zero", "renewable_ppa", "green_tariff_zero"):
            market_ef = 0.0
        elif data.get("emission_factor") is not None and market_instrument_type:
            market_ef = parse_number(data.get("emission_factor"), "emission_factor", required=False, min_value=0, max_value=MAX_GRID_EF_KG_PER_KWH)
        else:
            market_ef = location_ef

        co2e_market = (electricity_kwh * market_ef) / 1000.0
        co2e = co2e_location
        emission_factor = location_ef

    elif source_type == "indirect_steam":
        try:
            co2e, heat_mmbtu, emission_factor = _calc_indirect_steam(data)
            co2e_location = co2e
            co2e_market = co2e
            market_ef = emission_factor
        except ValidationError:
            raise
        except Exception as exc:
            current_app.logger.warning(f"Indirect steam calculation failed: {exc}")
            return jsonify({"error": "Indirect steam calculation failed: check the amount, unit and inputs"}), 422

    elif source_type == "cogen_allocation":
        try:
            co2e = _calc_cogen_allocation(data)
            co2e_location = co2e
            co2e_market = co2e
            # the allocated heat output, as the file upload stores it
            heat_mmbtu = parse_number(data.get("heat_output_mmbtu") or ((data.get("calc_inputs") or {}).get(
                "cogen_allocation") or {}).get("heat_output"), "heat_output", required=False, min_value=0, default=0.0)
        except ValidationError:
            raise
        except Exception as exc:
            current_app.logger.warning(f"CHP allocation calculation failed: {exc}")
            return jsonify({"error": "CHP allocation calculation failed: check the inputs"}), 422

    if co2e < 0:
        return jsonify({"error": "Calculated emissions cannot be negative"}), 400

    # Calculate uncertainty (BUG-043: stored as a 1-sigma fraction, 0..2)
    provided_uncertainty = data.get("uncertainty")
    if provided_uncertainty not in (None, ""):
        final_uncertainty = parse_number(provided_uncertainty, "uncertainty", min_value=0, max_value=2)
    else:
        final_uncertainty = default_scope2_uncertainty(co2e)

    # BUG-060: one maker-checker policy for every scope (only admins are auto-Verified).
    initial_status = initial_record_status(user, data.get("status"))

    # Map amount to steam_ton / cooling_ton if source_type or unit indicates steam or cooling
    steam_ton_val = parse_number(data.get("steam_ton") or data.get("stream_ton"), "steam_ton", required=False, min_value=0, default=0.0)
    cooling_ton_val = parse_number(data.get("cooling_ton"), "cooling_ton", required=False, min_value=0, default=0.0)
    raw_amt = parse_number(data.get("amount"), "amount", required=False, min_value=0, default=0.0)
    raw_unit = str(data.get("unit") or "").lower().strip()

    # only a mass of steam is a steam tonnage: 5,000 MMBtu of steam is not 5,000 t (it was stored as
    # such, and an edit then recalculated the record from 5,000 short tons = 10,000 MMBtu)
    if steam_ton_val == 0 and raw_unit in _STEAM_MASS_UNITS:
        if raw_amt > 0:
            steam_ton_val = raw_amt

    if cooling_ton_val == 0 and ("cooling" in source_type.lower() or raw_unit in ["cooling_ton", "ton_hour", "ton_cooling"]):
        if raw_amt > 0:
            cooling_ton_val = raw_amt

    require_plausible_co2e(co2e, co2e_location, co2e_market)
    emission = Scope2Emission(
        facility_id=data.get("facility_id"),
        year=year_val,
        month=month_val,
        source_type=source_type,
        electricity_kwh=electricity_kwh,
        steam_ton=steam_ton_val,
        heat_mmbtu=heat_mmbtu,
        cooling_ton=cooling_ton_val,
        emission_factor=emission_factor,
        co2e=co2e,
        co2e_location_based=co2e_location,
        co2e_market_based=co2e_market,
        market_instrument_type=market_instrument_type,
        market_emission_factor=market_ef,
        uncertainty=final_uncertainty,
        location=data.get("location") or data.get("grid_region"),
        grid_region=data.get("grid_region") or data.get("location"),
        activity=data.get("activity"),
        division=data.get("division"),
        field=data.get("field"),
        created_by=user_id,
        status=initial_status,
        approved_by=user.id if initial_status == "Verified" and user else None,
        approved_at=datetime.datetime.now(datetime.timezone.utc) if initial_status == "Verified" else None,
    )

    try:
        db.session.add(emission)
        db.session.flush()
        emission_id_val = emission.id

        if user:
            from utils import log_activity_and_notify
            log_activity_and_notify(
                action="CREATE",
                record_id=str(emission_id_val),
                user=user,
                request=request,
                entity="Scope2Emission",
                entity_id=str(emission_id_val),
                facility_id=emission.facility_id,
                details=f"Created Scope 2 emission: {source_type} ({co2e:.2f} tCO2e, Status: {initial_status})",
            )
            from status import PENDING_STATUS_SET
            if initial_status in PENDING_STATUS_SET:
                from models import Notification, User
                admins = User.query.filter_by(role="admin", status="active").all()
                for admin in admins:
                    Notification.create(
                        user_id=admin.id,
                        type="audit",
                        title="New Scope 2 Emission Pending Review",
                        message=f"A new Scope 2 emission record ({source_type}) was submitted by {user.fullName} and is awaiting your approval.",
                    )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to create Scope 2 emission: {e}")
        return jsonify({"error": "Failed to create Scope 2 emission"}), 500

    from routes.dashboard import clear_dashboard_cache
    clear_dashboard_cache()

    return (
        jsonify(
            {
                "message": "Scope 2 emission created",
                "id": emission_id_val,
                "co2e": co2e,
                "status": initial_status,
                "emissions": {
                    "totalCo2e": co2e,
                    **gas_split(emission),
                    "uncertainty": final_uncertainty,
                },
                "record": {
                    "id": emission_id_val,
                    "year": emission.year,
                    "month": emission.month,
                    "facility_id": emission.facility_id,
                    "source_type": emission.source_type,
                    "electricity_kwh": electricity_kwh,
                    "heat_mmbtu": heat_mmbtu,
                    "amount": electricity_kwh if source_type == "electricity" else (heat_mmbtu or emission.steam_ton or emission.cooling_ton),
                    "unit": "kWh" if source_type == "electricity" else (data.get("unit") or "MMBtu"),
                    "emission_factor": emission.emission_factor,
                    "co2e": co2e,
                    "co2e_location_based": co2e_location,
                    "co2e_market_based": co2e_market,
                    "market_instrument_type": market_instrument_type,
                    "market_emission_factor": market_ef,
                    "uncertainty": final_uncertainty,
                    "location": emission.location or emission.grid_region,
                    "status": emission.status,
                },
                "calculation_method": f"Scope 2 {source_type.replace('_', ' ').title()}",
            }
        ),
        201,
    )


@scope2_bp.route("/<int:emission_id>", methods=["PUT"])
@login_required
def update_scope2_emission(emission_id):
    """Update a Scope 2 emission record"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["auditor", "it_admin", "it_manager", "it"]:
        return jsonify({"error": "Read-only or administrative role cannot modify emission records"}), 403

    emission = db.session.get(Scope2Emission, emission_id)
    if not emission:
        return jsonify({"error": "Emission not found"}), 404

    if not require_facility_access(user, emission.facility_id):
        return jsonify({"error": "Unauthorized: Outside your region"}), 403

    # Enforce creator ownership for standard user role
    if user.role == "user" and emission.created_by is not None and emission.created_by != user.id:
        return jsonify({"error": "Unauthorized: You may only modify records you created"}), 403

    data = request.get_json() or {}

    # BUG-067/RC-2: record the last maker; non-admin edits of decided records go back to review.
    from services.maker_checker import on_edit

    on_edit(emission, user)

    # Strip status and co2e from direct client overwrite
    data.pop("status", None)
    data.pop("approved_by", None)
    data.pop("approved_at", None)
    data.pop("co2e", None)

    if "facility_id" in data:
        denied = facility_access_error(user, data["facility_id"])
        if denied:
            return denied
        emission.facility_id = int(data["facility_id"])
    if "year" in data:
        emission.year = parse_year(data["year"])
    if "month" in data:
        emission.month = parse_month(data["month"])
    if "source_type" in data:
        emission.source_type = data["source_type"]

    old_heat, old_co2e, old_ef, old_tons = emission.heat_mmbtu, emission.co2e, emission.emission_factor, emission.steam_ton

    # Check for recalculation trigger (L9)
    activity_changed = any(
        k in data
        for k in [
            "electricity_kwh",
            "steam_ton",
            "heat_mmbtu",
            "cooling_ton",
            "emission_factor",
        ]
    )
    for fld in ("electricity_kwh", "steam_ton", "heat_mmbtu", "cooling_ton"):
        if fld in data:
            setattr(emission, fld, parse_number(data[fld], fld, required=False, min_value=0, default=0.0))
    if "grid_region" in data or "location" in data:
        emission.grid_region = data.get("grid_region") or data.get("location") or emission.grid_region
        activity_changed = True
    st_now = (emission.source_type or "").strip().lower()
    _grid = grid_entry(emission.grid_region)[1] if ("electric" in st_now) else None
    if _grid is not None:
        # BUG-099: a known grid always uses the server factor, never the client's.
        emission.emission_factor = grid_factor_kg_co2e_per_kwh(_grid)
    elif "emission_factor" in data:
        max_ef = MAX_GRID_EF_KG_PER_KWH if "electric" in st_now else None
        emission.emission_factor = parse_number(data["emission_factor"], "emission_factor", min_value=0, max_value=max_ef)

    st_cogen = (emission.source_type or "").strip().lower() in ("cogen_allocation", "cogen", "chp")
    cogen_ci = (data.get("calc_inputs") or {}).get("cogen_allocation") or {}
    cogen_given = bool(cogen_ci) or any(data.get(k) not in (None, "") for k in (
        "total_emissions", "fuel_consumed_mmbtu", "heat_output_mmbtu", "power_output_mwh"))
    if st_cogen and (activity_changed or cogen_given):
        # the allocation inputs (facility total, heat and power output) are not stored: an edit of the
        # heat alone changed heat_mmbtu and left the allocated co2e as it was (deep-dive audit)
        total_in = cogen_ci.get("total_emissions") or data.get("total_emissions") or data.get("fuel_consumed_mmbtu")
        heat_in = cogen_ci.get("heat_output") or data.get("heat_output_mmbtu")
        power_in = cogen_ci.get("power_output") if cogen_ci.get("power_output") not in (None, "") else data.get("power_output_mwh")
        if total_in in (None, "") or heat_in in (None, "") or power_in in (None, ""):
            db.session.rollback()
            return jsonify({"error": "A CHP allocation is recalculated from the facility total emissions (or fuel "
                                     "consumed), heat output and power output: give all three"}), 422
        emission.co2e = round(_calc_cogen_allocation(data), 4)
        emission.co2e_location_based = emission.co2e
        emission.co2e_market_based = emission.co2e
        emission.heat_mmbtu = parse_number(heat_in, "heat_output", min_value=0)
        activity_changed = False

    if "market_instrument_type" in data:
        emission.market_instrument_type = str(data["market_instrument_type"] or "").strip() or None
        activity_changed = True
    if "market_emission_factor" in data:
        raw_m_ef = data["market_emission_factor"]
        emission.market_emission_factor = parse_number(raw_m_ef, "market_emission_factor", required=False, min_value=0, max_value=MAX_GRID_EF_KG_PER_KWH) if raw_m_ef not in (None, "") else None
        activity_changed = True

    if activity_changed:
        factor = emission.emission_factor or 0.0
        st = (emission.source_type or "").strip().lower()
        if st in ["electricity"] or "electric" in st:
            emission.co2e_location_based = round((emission.electricity_kwh * factor) / 1000.0, 4)
            m_ef = emission.market_emission_factor if emission.market_emission_factor is not None else factor
            if emission.market_instrument_type and emission.market_instrument_type.lower() in ("rec", "ppa_zero", "go_zero", "renewable_ppa", "green_tariff_zero"):
                m_ef = 0.0
            emission.co2e_market_based = round((emission.electricity_kwh * m_ef) / 1000.0, 4)
            emission.co2e = emission.co2e_location_based
        elif st in ["steam", "indirect_steam"] or "steam" in st:
            emission.co2e, emission.heat_mmbtu = _recalc_indirect_steam(
                emission, data, factor, old_heat, old_co2e, old_ef, old_tons)
            emission.co2e_location_based = emission.co2e
            emission.co2e_market_based = emission.co2e
        elif st in ["heat"] or "heat" in st:
            emission.co2e = round((emission.heat_mmbtu * factor) / 1000.0, 4)
            emission.co2e_location_based = emission.co2e
            emission.co2e_market_based = emission.co2e
        elif st in ["cooling"] or "cool" in st:
            emission.co2e = round((emission.cooling_ton * factor) / 1000.0, 4)
            emission.co2e_location_based = emission.co2e
            emission.co2e_market_based = emission.co2e

    if "uncertainty" in data:
        emission.uncertainty = parse_number(data["uncertainty"], "uncertainty", required=False, min_value=0, max_value=2)
    if "location" in data:
        emission.location = data["location"]
    require_plausible_co2e(emission.co2e, emission.co2e_location_based, emission.co2e_market_based)
    try:
        from utils import log_activity_and_notify
        log_activity_and_notify(
            action="UPDATE",
            record_id=str(emission.id),
            user=user,
            request=request,
            entity="Scope2Emission",
            entity_id=str(emission.id),
            details=f"Updated Scope 2 emission #{emission.id}: {emission.source_type} ({float(emission.co2e or 0):.2f} tCO2e)",
            facility_id=emission.facility_id,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to update Scope 2 emission: {e}")
        return jsonify({"error": "Failed to update Scope 2 emission"}), 500

    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()

    return jsonify({"message": "Scope 2 emission updated"})


@scope2_bp.route("/<int:emission_id>", methods=["DELETE"])
@login_required
def delete_scope2_emission(emission_id):
    """Delete a Scope 2 emission record"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to emission data"}), 403

    if user.role in ["auditor"]:
        return jsonify({"error": "Forbidden: Read-only accounts cannot delete emission records"}), 403

    emission = db.session.get(Scope2Emission, emission_id)
    if not emission:
        return jsonify({"error": "Emission not found"}), 404

    from services.maker_checker import delete_denied_reason

    denied = delete_denied_reason(user, emission)
    if denied:
        return jsonify({"error": denied}), 403
    fac_id_for_log = emission.facility_id

    log_details = f"Deleted Scope 2 emission: {emission.source_type} ({emission.co2e:.2f} tCO2e, facility #{emission.facility_id})"

    db.session.delete(emission)
    try:
        from utils import log_activity_and_notify
        log_activity_and_notify(
            action="DELETE",
            record_id=str(emission_id),
            user=user,
            request=request,
            entity="Scope2Emission",
            details=log_details,
            facility_id=fac_id_for_log,
        )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to delete Scope 2 emission: {e}")
        return jsonify({"error": "Failed to delete Scope 2 record"}), 500

    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()

    return jsonify({"message": "Scope 2 emission deleted"})


@scope2_bp.route("/bulk-import", methods=["POST"])
@login_required
def bulk_import_scope2():
    """Import Scope 2 emissions from CSV data"""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Not authenticated"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to upload emission data"}), 403

    allowed_fids = get_allowed_facility_ids(user)
    data = request.get_json() or {}
    records = data.get("records", [])
    if not records:
        return jsonify({"error": "No records provided"}), 400

    MAX_SYNCHRONOUS_IMPORT = 2500
    if len(records) > MAX_SYNCHRONOUS_IMPORT:
        return jsonify({"error": f"Payload exceeds maximum synchronous limit of {MAX_SYNCHRONOUS_IMPORT} rows. "
                                 "Please split the batch."}), 413

    # BUG-060/RC-2: every bulk import is Pending until an approver reviews it (same as Scope 1/3).
    bulk_status = initial_record_status(user, channel="bulk")
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
                        facility = db.session.get(Facility, fid)
                        facility_cache[fid] = facility
                except (ValueError, TypeError):
                    facility = None

            if not facility:
                errors.append(f"Row {i}: Facility '{f_val}' not found")
                continue

            if allowed_fids is not None and facility.id not in allowed_fids:
                errors.append(f"Row {i}: Unauthorized for facility '{facility.name}'")
                continue

            # 2. Get Factor and Calculate
            grid_region = rec.get("grid_region")
            try:
                ef, grid_region = resolve_electricity_factor(grid_region, rec.get("emission_factor") or rec.get("factor"))
            except ValidationError as err:
                errors.append(f"Row {i}: {err.message}")
                continue
            # consumption in payload might be kwh, mwh, gwh. BulkImportModal uses 'consumption' and 'unit'
            val = parse_number(rec.get("consumption"), "consumption", min_value=0)
            if val <= 0:
                raise ValidationError("'consumption' must be greater than 0", "consumption")
            unit = str(rec.get("unit") or "").lower().strip()
            if not unit:
                raise ValidationError("'unit' is required", "unit")

            if unit in ["mwh", "mw-hr", "megawatthour"]:
                kwh = val * 1000.0
            elif unit in ["gwh", "gw-hr", "gigawatthour"]:
                kwh = val * 1_000_000.0
            elif unit in ["kwh", "kw-hr", "kilowatthour"]:
                kwh = val
            else:
                raise ValidationError(f"Unsupported electricity unit '{unit}'", "unit")
            row_year = parse_year(rec.get("year"))
            row_month = parse_month(rec.get("month"), required=True)

            co2e_val = (kwh * ef) / 1000

            # Market-based calculation for bulk import
            mkt_inst = (rec.get("market_instrument_type") or "").strip() or None
            mkt_ef_raw = rec.get("market_emission_factor")
            if mkt_ef_raw not in (None, ""):
                mkt_ef = parse_number(mkt_ef_raw, "market_emission_factor", required=False, min_value=0, max_value=MAX_GRID_EF_KG_PER_KWH)
            elif mkt_inst and mkt_inst.lower() in ("rec", "ppa_zero", "go_zero", "renewable_ppa", "green_tariff_zero"):
                mkt_ef = 0.0
            else:
                mkt_ef = ef
            co2e_mkt_val = (kwh * mkt_ef) / 1000.0

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

            require_plausible_co2e(co2e_val, co2e_mkt_val)
            emission = Scope2Emission(
                facility_id=facility.id,
                year=row_year,
                month=row_month,
                source_type="electricity",
                electricity_kwh=kwh,
                emission_factor=ef,
                co2e=co2e_val,
                co2e_location_based=co2e_val,
                co2e_market_based=co2e_mkt_val,
                market_instrument_type=mkt_inst,
                market_emission_factor=mkt_ef,
                uncertainty=final_uncertainty,
                grid_region=grid_region,
                location=grid_region,
                activity=rec.get("activity") or facility.activity,
                division=rec.get("division") or facility.division,
                field=rec.get("field") or facility.field,
                created_by=user.id,
                status=bulk_status,
                approved_by=user.id if bulk_status == "Verified" else None,
                approved_at=datetime.datetime.now(datetime.timezone.utc) if bulk_status == "Verified" else None,
            )
            db.session.add(emission)
            imported_count += 1
        except ValidationError as e:
            errors.append(f"Row {i}: {e.message}")
        except Exception as e:
            current_app.logger.warning(f"Scope 2 bulk row {i} failed: {e}")
            errors.append(f"Row {i}: invalid row")

    try:
        if imported_count > 0:
            log_activity_and_notify(
                "IMPORT",
                str(imported_count),
                f"Bulk imported {imported_count} Scope 2 records",
                user=user,
                request=request,
                entity="Scope2Emission",
            )
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to bulk import Scope 2 emissions: {e}")
        return jsonify({"error": "Failed to bulk import Scope 2 emissions"}), 500

    from routes.dashboard import clear_dashboard_cache

    clear_dashboard_cache()
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
                "factor": round(grid_factor_kg_co2e_per_kwh(info), 6),
                "unit": info["unit"],
                "description": info["description"],
                "source": info.get("source"),
                "verified": info.get("verified", True),
            }
        )

    return jsonify(factors)
