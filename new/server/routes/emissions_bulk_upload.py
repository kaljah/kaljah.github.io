"""Synchronous bulk-upload route for Scope 1 emissions.

Split out of routes/emissions.py unchanged (hardening plan, task 5.3). The routes are
registered on the same ``emissions_bp`` blueprint, so URLs and endpoint names are the same.
"""
import json
import uuid
from calculations import calculate_co2e, compute_emissions
from emission_factors import API_FACTORS
from extensions import db, limiter
from flask import jsonify, request
from models import CustomFactor, Emission, Facility, Notification, User
from process_categories import NON_COMBUSTION_PROCESSES
from routes.auth import login_required
from services.ogmp import ogmp_level_for
from utils import get_allowed_facility_ids, get_current_user, internal_error, log_activity_and_notify
from . import emissions_bp
from routes.emissions import _lookup_api_factor, resolve_gwp_dict, resolve_gwp_standard


@emissions_bp.route("/bulk-upload", methods=["POST"])
@limiter.limit("20 per minute")
@login_required
def add_bulk_upload():
    from datetime import datetime

    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401
    if user.role in ["it_admin", "it_manager", "it"]:
        return jsonify({"error": "IT personnel do not have access to upload emission data"}), 403

    data = request.get_json()
    records = data.get("records", [])
    date_format = data.get("date_format", "YYYY-MM-DD")
    global_factor_type = data.get("global_factor_type", "auto")
    confirm = data.get("confirm", False)

    allowed_facilities = get_allowed_facility_ids(user)

    # Map frontend date format strings to strptime formats
    fmt_map = {
        "YYYY-MM-DD": "%Y-%m-%d",
        "MM/DD/YYYY": "%m/%d/%Y",
        "DD/MM/YYYY": "%d/%m/%Y",
        "YYYY-MM": "%Y-%m",
        "MM/YYYY": "%m/%Y",
        "YYYY": "%Y",
    }
    py_fmt = fmt_map.get(date_format, "%Y-%m-%d")

    # Pre-fetch facilities and custom factors for resolution
    all_facilities = Facility.query.all()
    from utils import build_name_map

    fac_name_map = build_name_map(all_facilities)

    # Pre-fetch custom factors
    custom_factors = CustomFactor.query.filter(CustomFactor.is_archived.is_(False)).all()
    cf_name_map = build_name_map(custom_factors)

    valid_records = []
    errors = []
    duplicates = []
    new_emissions = []

    for idx, row in enumerate(records):
        row_num = idx + 1
        row_errors = []

        # 1. Parse Date
        date_str = row.get("date")
        if date_str:
            try:
                dt = datetime.strptime(str(date_str).strip(), py_fmt)
                year = dt.year
                month = dt.month
            except ValueError:
                row_errors.append(
                    f"Invalid date format: {date_str} does not match {date_format}."
                )
                year, month = None, None
        else:
            year_val = row.get("year")
            month_val = row.get("month")
            if year_val and month_val:
                try:
                    year = int(year_val)
                    month = int(month_val)
                except ValueError:
                    row_errors.append(f"Invalid year/month: {year_val}/{month_val}")
                    year, month = None, None
            else:
                row_errors.append("Missing date or year/month.")
                year, month = None, None

        # 2. Resolve Facility
        fac_name = row.get("facility_name", row.get("facility_id", "")).strip()
        facility = None
        if fac_name:
            # Check ID match first if they provided a number
            if fac_name.isdigit():
                facility = next(
                    (f for f in all_facilities if str(f.id) == fac_name), None
                )
            # If not ID or not found, try name match
            if not facility:
                facility = fac_name_map.get(fac_name.lower())

            if not facility:
                row_errors.append(f"Facility not found: '{fac_name}'")
            elif (
                allowed_facilities is not None and facility.id not in allowed_facilities
            ):
                row_errors.append(
                    f"You do not have permission to add data for facility: '{fac_name}'"
                )
        else:
            row_errors.append("Missing facility.")

        # 3. Handle Quantity/Amount
        amount_raw = row.get("quantity", row.get("amount"))
        try:
            amount = float(amount_raw)
        except (ValueError, TypeError):
            row_errors.append(f"Invalid quantity: {amount_raw}")
            amount = 0

        process_type = row.get("process", row.get("process_type", row.get("type", "")))
        fuel = row.get("fuel", row.get("fuel_type", ""))
        unit = row.get("unit", "")

        proc_clean = str(process_type).strip().lower()
        factor_type_raw = str(row.get("factor_type", "")).lower()
        if global_factor_type and global_factor_type != "auto":
            factor_type = global_factor_type
        else:
            factor_type = factor_type_raw

        is_tier3_factor = factor_type in [
            "specific", "site_specific", "site-specific", "engineering", "tier3", "tier_3", "t3", "cems"
        ]
        is_non_comb = proc_clean in NON_COMBUSTION_PROCESSES or is_tier3_factor

        if not process_type:
            row_errors.append("Missing process type.")
        if not fuel and not is_non_comb:
            row_errors.append("Missing fuel/activity.")

        # 4. Resolve Factor (Standard vs Custom vs Sparse Engineering)
        factor_data = {}

        if process_type == "Flaring":
            # Option B: Sparse columns
            try:
                factor_data = {
                    "c1": float(row.get("c1", 0)),
                    "c2": float(row.get("c2", 0)),
                    "c3": float(row.get("c3", 0)),
                    "c4": float(row.get("c4", 0)),
                    "c5": float(row.get("c5", 0)),
                    "c6": float(row.get("c6", 0)),
                    "co2": float(row.get("co2_mol", 0)),
                    "n2": float(row.get("n2_mol", 0)),
                }
            except ValueError:
                row_errors.append("Invalid engineering calculation inputs for Flaring.")
        elif factor_type == "custom":
            cf = cf_name_map.get(fuel.strip().lower())
            if fuel.strip().lower() in cf_name_map.ambiguous:
                row_errors.append(f"Custom factor name '{fuel}' is not unique; rename the duplicates first.")
            elif not cf:
                row_errors.append(
                    f"Custom factor not found for fuel: '{fuel}'. Please save it in the app first."
                )
            else:
                factor_data = {
                    "co2": cf.co2_factor,
                    "ch4": cf.ch4_factor,
                    "n2o": cf.n2o_factor,
                    "co": cf.co_factor,
                    "unit": cf.unit,
                    "hhv": cf.hhv_factor,
                    "type": "custom",
                    "name": cf.name,
                }
                if cf.co2_uncertainty or cf.ch4_uncertainty or cf.n2o_uncertainty:
                    factor_data["uncertainty"] = {
                        "co2": float(
                            getattr(cf, "co2_uncertainty", None)
                            or getattr(cf, "uncertainty", 0)
                            or 0
                        )
                        / 100.0,
                        "ch4": float(
                            getattr(cf, "ch4_uncertainty", None)
                            or getattr(cf, "uncertainty", 0)
                            or 0
                        )
                        / 100.0,
                        "n2o": float(
                            getattr(cf, "n2o_uncertainty", None)
                            or getattr(cf, "uncertainty", 0)
                            or 0
                        )
                        / 100.0,
                    }
                elif cf.uncertainty and cf.uncertainty > 0:
                    factor_data["uncertainty"] = {
                        "co2": float(cf.uncertainty or 0) / 100.0,
                        "ch4": float(cf.uncertainty or 0) / 100.0,
                        "n2o": float(cf.uncertainty or 0) / 100.0,
                    }
                elif cf.parent_fuel:
                    parent_factor = _lookup_api_factor(cf.parent_fuel)
                    if "uncertainty" in parent_factor:
                        factor_data["uncertainty"] = parent_factor["uncertainty"]
        elif is_non_comb or is_tier3_factor:
            factor_data = API_FACTORS.get(fuel, {})
        else:
            factor_data = API_FACTORS.get(fuel, {})
            if (
                not factor_data
                and not row_errors
            ):
                row_errors.append(f"Standard emission factor not found for: '{fuel}'")

        # 5. Check if row is clean to compute
        if row_errors:
            errors.append({"row": row_num, "reasons": row_errors, "original": row})
            continue

        # Base calc_data
        calc_data = {
            "year": year,
            "month": month,
            "facility_id": facility.id,
            "process_type": process_type,
            "fuel": fuel,
            "amount": amount,
            "unit": unit,
        }

        # Inject all other optional variables dynamically
        has_specific = False
        specific_keys = {
            "c1",
            "c2",
            "c3",
            "c4",
            "c5",
            "c6",
            "c7",
            "c8",
            "c9",
            "c10",
            "n2_mol",
            "co2_mol",
            "n2",
            "co2_comp",
            "h2s",
            "flare_type",
            "control_efficiency",
            "ch4_content",
            "co2_content",
            "combustion_efficiency",
            "operating_temperature",
            "temp_unit",
            "operating_pressure",
            "press_unit",
            "z_factor",
            "mud_type",
            "mud_unit",
            "comp_method",
            "comp_rate",
            "comp_duration",
            "comp_liquid_bbl",
            "comp_gor",
            "comp_flare_eff",
            "comp_choke_size",
            "comp_whp",
            "gor",
            "flowback_days",
            "unload_depth",
            "unload_diam",
            "unload_press",
            "unload_freq",
            "unload_flare_eff",
            "unload_temp",
            "blowdown_volume",
            "blowdown_pressure",
            "blowdown_events",
            "blowdown_unit",
            "blowdown_temp",
            "blowdown_temp_unit",
            "blowdown_press_unit",
            "blowdown_ch4",
            "tank_gor",
            "tank_press",
            "tank_temp",
            "tank_flare_eff",
            "tank_ch4_content",
            "tank_control_eff",
            "tank_unit",
            "tank_api_gravity",
            "pneumatic_type",
            "pneumatic_count",
            "pneumatic_hours",
            "pneu_count",
            "pneu_bleed_rate",
            "pneu_bleed_unit",
            "pneu_hours",
            "pneu_ch4_content",
            "agr_co2_in",
            "agr_co2_out",
            "agr_ch4_in",
            "agr_unit",
            "agr_ch4_slip",
            "agr_control_eff",
            "dehy_pump_rate",
            "dehy_pump_unit",
            "dehy_hours",
            "dehy_eff",
            "dehy_ch4_content",
            "dehy_press",
            "dehy_press_unit",
            "dehy_temp",
            "dehy_temp_unit",
            "dehy_has_flash",
            "dehy_flash_eff",
            "dehy_still_type",
            "hhv",
            "ef_unit",
            "fuel_type",
            "boiler_eff",
            "trans_loss",
            "heat_unit",
            "total_emissions",
            "heat_output",
            "power_output",
            "allocation_method",
            "carbon_content",
            "molecular_weight",
            "fugitive_method",
            "fugitive_ppm",
        }

        for k, v in row.items():
            if k not in calc_data and v is not None:
                val = str(v).strip()
                if val:  # only include non-empty values
                    calc_data[k] = val
                    if k in specific_keys:
                        has_specific = True

        if is_tier3_factor or has_specific:
            calc_data["factor_source"] = "specific"
        elif factor_type in ["custom", "regional", "tier2", "tier_2", "t2"]:
            calc_data["factor_source"] = "custom"
        elif factor_type == "default":
            calc_data["factor_source"] = "default"


        # 6. Compute
        gwp_dict = resolve_gwp_dict(user)
        gwp_std = resolve_gwp_standard(user)
        try:
            em_result, method = compute_emissions(
                calc_data, factor_data, gwp_dict=gwp_dict
            )
        except Exception as e:
            errors.append(
                {
                    "row": row_num,
                    "reasons": [f"Calculation failed: {str(e)}"],
                    "original": row,
                }
            )
            continue

        # Fallback GWP CO2e if missing
        if not em_result.get("totalCo2e") or em_result.get("totalCo2e") == 0:
            co2_val = em_result.get("co2", 0)
            ch4_val = em_result.get("ch4", 0)
            n2o_val = em_result.get("n2o", 0)
            em_result["totalCo2e"] = calculate_co2e(
                co2_val, ch4_val, n2o_val, gwp_dict=gwp_dict
            )

        # Uncertainty
        api_res = em_result.get("_full_api_res")
        if api_res:
            uncertainty = {
                "co2": (
                    api_res["results"]["co2"].get("uncertainty")
                    if isinstance(api_res["results"]["co2"], dict)
                    else 0.05
                ),
                "ch4": (
                    api_res["results"]["ch4"].get("uncertainty")
                    if isinstance(api_res["results"]["ch4"], dict)
                    else 0.15
                ),
                "n2o": (
                    api_res["results"]["n2o"].get("uncertainty")
                    if isinstance(api_res["results"]["n2o"], dict)
                    else 0.15
                ),
            }
        else:
            uncertainty = factor_data.get("uncertainty", {})

        # Prepare Record — all bulk upload paths queue as Pending per Decision D-04
        rec_id = str(uuid.uuid4())
        bulk_status = "Pending"
        emission_obj = Emission(
            record_id=rec_id,
            year=year,
            month=month,
            facility_id=facility.id,
            group_name=row.get("group", ""),
            activity=row.get("activity", facility.activity),
            division=row.get("division", facility.division),
            field=row.get("field", facility.field),
            process_type=process_type,
            fuel_type=fuel,
            quantity=amount,
            unit=unit,
            equipment_id=row.get("equipment", ""),
            co2_emissions=em_result["co2"],
            ch4_emissions=em_result["ch4"],
            n2o_emissions=em_result["n2o"],
            co_emissions=em_result.get("co", 0),
            co2e_total=em_result["totalCo2e"],
            calc_method=method,
            gwp_version=gwp_std,
            source_payload=json.dumps(calc_data),
            created_by=user.id,
            uncertainty=(
                uncertainty.get("co2", None)
                if isinstance(uncertainty, dict)
                else (uncertainty or None)
            ),
            uncertainty_ch4=(
                uncertainty.get("ch4", None)
                if isinstance(uncertainty, dict)
                else (uncertainty or None)
            ),
            uncertainty_n2o=(
                uncertainty.get("n2o", None)
                if isinstance(uncertainty, dict)
                else (uncertainty or None)
            ),
            status=bulk_status,
            approved_by=user.id if bulk_status == "Verified" else None,
            approved_at=datetime.datetime.now(datetime.timezone.utc) if bulk_status == "Verified" else None,
            factor_source=calc_data.get("factor_source", "default"),
        )
        emission_obj.ogmp_level = ogmp_level_for(emission_obj)


        # 7. Check for Duplicates
        duplicate = Emission.query.filter_by(
            year=year,
            month=month,
            facility_id=facility.id,
            process_type=process_type,
            equipment_id=row.get("equipment", ""),
        ).first()

        preview_data = {
            "row": row_num,
            "year": year,
            "month": month,
            "facility": facility.name,
            "process": process_type,
            "fuel": fuel,
            "amount": amount,
            "unit": unit,
            "co2e": round(em_result["totalCo2e"], 2),
        }

        if duplicate:
            duplicates.append(preview_data)
            # If confirm=True and they chose to overwrite, we'd update.
            # For simplicity, if we are confirming and hit a duplicate, we can delete the old one and insert new.
            if confirm:
                # overwrite through the maker-checker (back to Pending, old and new values in the
                # audit trail), never by deleting the reviewed record
                from background_processor import _S1_RESULT_FIELDS, _bulk_overwrite

                _bulk_overwrite(duplicate, {f: getattr(emission_obj, f) for f in _S1_RESULT_FIELDS
                                            if f not in ("qa_flag",)}, user.id, "Scope 1")
        else:
            valid_records.append(preview_data)
            if confirm:
                new_emissions.append(emission_obj)

    # 8. Finalize Database changes if confirming
    if confirm:
        if new_emissions:
            db.session.add_all(new_emissions)
            try:
                # If records are pending approval, notify all admins
                if bulk_status in ("Pending", "Pending Approval"):
                    admins = User.query.filter_by(role="admin", status="active").all()
                    for admin in admins:
                        Notification.create(
                            user_id=admin.id,
                            type="audit",
                            title="Scope 1 Bulk Upload Pending Review",
                            message=f"{len(new_emissions)} new Scope 1 emission records were uploaded by {user.fullName} and are awaiting your approval.",
                        )
                log_activity_and_notify(
                    action="BULK_IMPORT",
                    record_id=f"count:{len(new_emissions)}",
                    user=user,
                    request=request,
                    entity="Emission",
                    details=f"Bulk uploaded {len(new_emissions)} Scope 1 records (Status: {bulk_status})",
                )
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                return internal_error(e, "Failed to save to database")

        return jsonify(
            {"status": "success", "imported": len(new_emissions), "errors": errors}
        )

    # If preview
    return jsonify(
        {
            "status": "preview",
            "valid_count": len(valid_records),
            "valid_records": valid_records,
            "duplicate_count": len(duplicates),
            "duplicates": duplicates,
            "errors": errors,
        }
    )
