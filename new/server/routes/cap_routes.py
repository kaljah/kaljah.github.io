from flask import Blueprint, jsonify, request, current_app
from extensions import db
from models import CapEmission, CapRegulatoryLimit, Facility
from routes.auth import login_required
from utils import get_current_user, get_allowed_facility_ids, require_facility_access

cap_bp = Blueprint("cap", __name__)

DEFAULT_DECREE_06_138_LIMITS = [
    {"pollutant": "NO2", "limit_mg_nm3": 200.0, "unit": "mg/Nm3", "notes": "Nitrogen Dioxide limit under Decree 06-138"},
    {"pollutant": "CO", "limit_mg_nm3": 150.0, "unit": "mg/Nm3", "notes": "Carbon Monoxide limit under Decree 06-138"},
    {"pollutant": "SO2", "limit_mg_nm3": 800.0, "unit": "mg/Nm3", "notes": "Sulfur Dioxide limit under Decree 06-138"},
    {"pollutant": "PM", "limit_mg_nm3": 30.0, "unit": "mg/Nm3", "notes": "Particulate Matter limit under Decree 06-138"},
    {"pollutant": "VOC", "limit_mg_nm3": 150.0, "unit": "mg/Nm3", "notes": "Volatile Organic Compounds limit under Decree 06-138"},
]


def ensure_default_limits():
    """Ensure Algerian Executive Decree 06-138 limits are populated."""
    added = False
    for item in DEFAULT_DECREE_06_138_LIMITS:
        exists = CapRegulatoryLimit.query.filter_by(
            standard_name="Executive Decree 06-138", pollutant=item["pollutant"]
        ).first()
        if not exists:
            lim = CapRegulatoryLimit(
                standard_name="Executive Decree 06-138",
                pollutant=item["pollutant"],
                limit_mg_nm3=item["limit_mg_nm3"],
                unit=item["unit"],
                notes=item["notes"],
            )
            db.session.add(lim)
            added = True
    if added:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()


@cap_bp.route("/limits", methods=["GET"])
@login_required
def get_regulatory_limits():
    """Retrieve atmospheric pollutant emission limit values under Decree 06-138."""
    ensure_default_limits()
    limits = CapRegulatoryLimit.query.filter_by(standard_name="Executive Decree 06-138").all()
    return jsonify([
        {
            "id": l.id,
            "standard_name": l.standard_name,
            "pollutant": l.pollutant,
            "limit_mg_nm3": l.limit_mg_nm3,
            "unit": l.unit,
            "notes": l.notes,
        }
        for l in limits
    ])


@cap_bp.route("/emissions", methods=["GET"])
@login_required
def get_cap_emissions():
    """Retrieve Criteria Air Pollutant records filtered by facility, year, or source module."""
    user = get_current_user()
    if user and user.role in ["it", "it_admin", "it_manager"]:
        return jsonify({"error": "Forbidden: IT personnel cannot access operational CAP emission data"}), 403
    allowed_fids = get_allowed_facility_ids(user)

    query = CapEmission.query
    if allowed_fids is not None:
        query = query.filter(CapEmission.facility_id.in_(allowed_fids))

    facility_id = request.args.get("facility_id")
    if facility_id and facility_id != "all":
        try:
            fid = int(facility_id)
        except (ValueError, TypeError):
            return jsonify({"error": "facility_id must be a valid integer"}), 422
        if allowed_fids is not None and fid not in allowed_fids:
            return jsonify({"error": "Unauthorized facility"}), 403
        query = query.filter(CapEmission.facility_id == fid)

    year = request.args.get("year")
    if year and year != "all":
        try:
            query = query.filter(CapEmission.year == int(year))
        except ValueError:
            pass

    source_module = request.args.get("source_module")
    if source_module and source_module != "all":
        query = query.filter(CapEmission.source_module == source_module)

    pollutant = request.args.get("pollutant")
    if pollutant and pollutant != "all":
        query = query.filter(CapEmission.pollutant == pollutant)

    records = query.order_by(CapEmission.year.desc(), CapEmission.facility_id, CapEmission.pollutant).all()

    fac_map = {f.id: f.name for f in Facility.query.all()}

    return jsonify([
        {
            "id": r.id,
            "facility_id": r.facility_id,
            "facility_name": fac_map.get(r.facility_id, "Unknown"),
            "year": r.year,
            "month": r.month,
            "source_module": r.source_module,
            "pollutant": r.pollutant,
            "mass_tonnes": r.mass_tonnes,
            "concentration_mg_nm3": r.concentration_mg_nm3,
            "flue_gas_volume_nm3": r.flue_gas_volume_nm3,
            "calc_method": r.calc_method,
            "notes": r.notes,
            "status": r.status,
        }
        for r in records
    ])


CAP_POLLUTANTS = ("NO2", "CO", "SO2", "PM", "VOC")


@cap_bp.route("/emissions", methods=["POST"])
@login_required
def create_or_update_cap_emission():
    """Create or update a Criteria Air Pollutant entry.

    BUG-053: status is decided by the server (maker-checker), never taken from the payload,
    and every numeric input must be finite and non-negative.
    """
    from input_validation import parse_month, parse_number, parse_year, require_text
    from services.maker_checker import on_edit
    from utils import initial_record_status, log_activity_and_notify, user_label

    user = get_current_user()
    if not user or user.role in ("auditor", "it_admin", "it_manager", "it"):
        return jsonify({"error": "Forbidden: this account cannot record CAP emissions"}), 403
    data = request.get_json() or {}

    facility_id = int(parse_number(data.get("facility_id"), "facility_id", min_value=1))
    if not require_facility_access(user, facility_id):
        return jsonify({"error": "Forbidden: You do not have access to this facility"}), 403

    year = parse_year(data.get("year"))
    month = parse_month(data.get("month"))
    source_module = require_text(data.get("source_module"), "source_module")
    pollutant = require_text(data.get("pollutant"), "pollutant").upper()
    if pollutant not in CAP_POLLUTANTS:
        return jsonify({"error": f"pollutant must be one of {', '.join(CAP_POLLUTANTS)}", "field": "pollutant"}), 400

    concentration = parse_number(data.get("concentration_mg_nm3"), "concentration_mg_nm3", required=False, min_value=0)
    flue_gas_vol = parse_number(data.get("flue_gas_volume_nm3"), "flue_gas_volume_nm3", required=False, min_value=0)
    mass_val = parse_number(data.get("mass_tonnes"), "mass_tonnes", required=False, min_value=0)
    if mass_val is None:
        if concentration is None or flue_gas_vol is None:
            return jsonify({"error": "Provide mass_tonnes, or both concentration_mg_nm3 and flue_gas_volume_nm3"}), 400
        # mass (t) = concentration (mg/Nm3) x volume (Nm3) x 1e-9 (mg -> t)
        mass_val = concentration * flue_gas_vol * 1e-9

    rec_id = data.get("id")
    if rec_id:
        try:
            rec_id = int(rec_id)
        except (ValueError, TypeError):
            return jsonify({"error": "id must be an integer", "field": "id"}), 400
        record = db.session.get(CapEmission, rec_id)
        if not record:
            return jsonify({"error": "Record not found"}), 404
        if not require_facility_access(user, record.facility_id):
            return jsonify({"error": "Forbidden: You do not have access to this facility"}), 403
    else:
        record = CapEmission.query.filter_by(
            facility_id=facility_id, year=year, month=month, source_module=source_module, pollutant=pollutant,
        ).first()

    if record is None:
        status = initial_record_status(user, data.get("status"))
        record = CapEmission(
            facility_id=facility_id, year=year, month=month, source_module=source_module, pollutant=pollutant,
            created_by=user.id, created_by_name=user_label(user), status=status,
        )
        if status == "Verified":
            import datetime as _dt

            record.approved_by = user.id
            record.approved_at = _dt.datetime.now(_dt.timezone.utc)
            record.approved_by_name = user_label(user)
        db.session.add(record)
        action = "CREATE"
    else:
        if user.role == "user" and record.created_by not in (None, user.id):
            return jsonify({"error": "Unauthorized: You may only modify records you created"}), 403
        on_edit(record, user)
        action = "UPDATE"

    record.mass_tonnes = mass_val
    record.concentration_mg_nm3 = concentration
    record.flue_gas_volume_nm3 = flue_gas_vol
    record.calc_method = data.get("calc_method") or "API Compendium"
    record.notes = data.get("notes")
    db.session.flush()
    log_activity_and_notify(action=action, record_id=str(record.id), user=user, request=request, entity="CapEmission",
                            facility_id=record.facility_id,
                            details=f"CAP {pollutant} {source_module} {year}/{month or '-'}: {mass_val:.6g} t (status {record.status})")
    db.session.commit()

    return jsonify({"success": True, "id": record.id, "status": record.status, "message": "CAP emission record saved"})


@cap_bp.route("/compliance", methods=["GET"])
@login_required
def get_cap_compliance():
    """
    Evaluates Criteria Air Pollutant compliance against Algerian Executive Decree 06-138.
    Compares measured concentration (mg/Nm3) with the statutory limit for each pollutant.
    """
    ensure_default_limits()
    user = get_current_user()
    if user and user.role in ["it", "it_admin", "it_manager"]:
        return jsonify({"error": "Forbidden: IT personnel cannot access operational CAP compliance data"}), 403
    allowed_fids = get_allowed_facility_ids(user)

    year = request.args.get("year", 2025)
    try:
        yr = int(year)
    except ValueError:
        yr = 2025

    limits = {l.pollutant: l.limit_mg_nm3 for l in CapRegulatoryLimit.query.all()}

    fac_q = Facility.query
    if allowed_fids is not None:
        fac_q = fac_q.filter(Facility.id.in_(allowed_fids))

    facility_id = request.args.get("facility_id")
    if facility_id and facility_id != "all":
        try:
            fid = int(facility_id)
        except (ValueError, TypeError):
            return jsonify({"error": "facility_id must be a valid integer"}), 422
        if allowed_fids is not None and fid not in allowed_fids:
            return jsonify({"error": "Unauthorized facility"}), 403
        fac_q = fac_q.filter(Facility.id == fid)

    facilities = fac_q.all()
    results = []

    for fac in facilities:
        # Retrieve all CAP emissions for this facility and year
        # BUG-053: compliance is assessed on approved (Verified) records only
        cap_records = CapEmission.query.filter_by(facility_id=fac.id, year=yr, status="Verified").all()

        pollutants_map = {}
        for r in cap_records:
            pol = r.pollutant
            if pol not in pollutants_map:
                pollutants_map[pol] = {"total_mass": 0.0, "concentration": 0.0, "count": 0}
            pollutants_map[pol]["total_mass"] += float(r.mass_tonnes or 0.0)
            if r.concentration_mg_nm3 is not None:
                # Store latest or peak measured concentration
                pollutants_map[pol]["concentration"] = max(pollutants_map[pol]["concentration"], float(r.concentration_mg_nm3))

        fac_compliance = {
            "facility_id": fac.id,
            "facility_name": fac.name,
            "year": yr,
            "decree": "Executive Decree 06-138",
            "pollutants": []
        }

        any_exceeded = False
        any_measured = False
        for pol in ["NO2", "CO", "SO2", "PM", "VOC"]:
            lim_val = limits.get(pol, 200.0)
            p_data = pollutants_map.get(pol, {"total_mass": 0.0, "concentration": 0.0})
            measured_c = p_data["concentration"]
            # compliance with a concentration limit can only be stated from a measured concentration;
            # no verified measurement is "not measured", never "compliant"
            measured = measured_c > 0
            is_exceeded = measured and measured_c > lim_val
            any_measured = any_measured or measured
            any_exceeded = any_exceeded or is_exceeded

            fac_compliance["pollutants"].append({
                "pollutant": pol,
                "total_tonnes": round(p_data["total_mass"], 2),
                "measured_concentration_mg_nm3": round(measured_c, 2),
                "statutory_limit_mg_nm3": lim_val,
                "is_compliant": (not is_exceeded) if measured else None,
                "status": ("NON-COMPLIANT (Exceeded)" if is_exceeded else "COMPLIANT") if measured else "NOT MEASURED",
                "notes": ("Measured concentration above the statutory limit" if is_exceeded else "Within permissible limits")
                if measured else "No verified concentration measurement",
            })

        fac_compliance["overall_status"] = (
            "NON-COMPLIANT" if any_exceeded else "COMPLIANT" if any_measured else "NOT ASSESSED"
        )
        results.append(fac_compliance)

    return jsonify(results)
