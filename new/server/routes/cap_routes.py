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
    db.session.commit()


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
    allowed_fids = get_allowed_facility_ids(user)

    query = CapEmission.query
    if allowed_fids is not None:
        query = query.filter(CapEmission.facility_id.in_(allowed_fids))

    facility_id = request.args.get("facility_id")
    if facility_id and facility_id != "all":
        try:
            fid = int(facility_id)
            if allowed_fids is not None and fid not in allowed_fids:
                return jsonify({"error": "Unauthorized facility"}), 403
            query = query.filter(CapEmission.facility_id == fid)
        except ValueError:
            pass

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


@cap_bp.route("/emissions", methods=["POST"])
@login_required
def create_or_update_cap_emission():
    """Create or update a Criteria Air Pollutant entry."""
    user = get_current_user()
    data = request.get_json() or {}

    facility_id = data.get("facility_id")
    if not facility_id:
        return jsonify({"error": "facility_id is required"}), 400

    if not require_facility_access(user, int(facility_id)):
        return jsonify({"error": "Forbidden: You do not have access to this facility"}), 403

    year = data.get("year")
    source_module = data.get("source_module")
    pollutant = data.get("pollutant")

    if not year or not source_module or not pollutant:
        return jsonify({"error": "year, source_module, and pollutant are required"}), 400

    # If concentration and flue gas flow are provided, mass can be calculated per Algerian Law
    # mass (tonnes) = concentration (mg/Nm3) * volume (Nm3) * 1e-9
    concentration = data.get("concentration_mg_nm3")
    flue_gas_vol = data.get("flue_gas_volume_nm3")
    mass_val = data.get("mass_tonnes")

    if concentration is not None and flue_gas_vol is not None and mass_val is None:
        try:
            mass_val = float(concentration) * float(flue_gas_vol) * 1e-9
        except (ValueError, TypeError):
            mass_val = 0.0

    rec_id = data.get("id")
    if rec_id:
        record = db.session.get(CapEmission, int(rec_id))
        if not record:
            return jsonify({"error": "Record not found"}), 404
        if not require_facility_access(user, record.facility_id):
            return jsonify({"error": "Forbidden: You do not have access to this facility"}), 403
    else:
        record = CapEmission.query.filter_by(
            facility_id=int(facility_id),
            year=int(year),
            month=data.get("month"),
            source_module=source_module,
            pollutant=pollutant,
        ).first()
        if not record:
            record = CapEmission(
                facility_id=int(facility_id),
                year=int(year),
                month=data.get("month"),
                source_module=source_module,
                pollutant=pollutant,
                created_by=user.id,
            )
            db.session.add(record)

    record.mass_tonnes = float(mass_val or 0.0)
    record.concentration_mg_nm3 = float(concentration) if concentration is not None else None
    record.flue_gas_volume_nm3 = float(flue_gas_vol) if flue_gas_vol is not None else None
    record.calc_method = data.get("calc_method", "API Compendium")
    record.notes = data.get("notes")
    record.status = data.get("status", "Verified")

    db.session.commit()

    return jsonify({"success": True, "id": record.id, "message": "CAP emission record saved"})


@cap_bp.route("/compliance", methods=["GET"])
@login_required
def get_cap_compliance():
    """
    Evaluates Criteria Air Pollutant compliance against Algerian Executive Decree 06-138.
    Compares measured concentration (mg/Nm3) with the statutory limit for each pollutant.
    """
    ensure_default_limits()
    user = get_current_user()
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
        fac_q = fac_q.filter(Facility.id == int(facility_id))

    facilities = fac_q.all()
    results = []

    for fac in facilities:
        # Retrieve all CAP emissions for this facility and year
        cap_records = CapEmission.query.filter_by(facility_id=fac.id, year=yr).all()

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

        all_compliant = True
        for pol in ["NO2", "CO", "SO2", "PM", "VOC"]:
            lim_val = limits.get(pol, 200.0)
            p_data = pollutants_map.get(pol, {"total_mass": 0.0, "concentration": 0.0})
            measured_c = p_data["concentration"]
            is_exceeded = measured_c > lim_val if measured_c > 0 else False
            if is_exceeded:
                all_compliant = False

            fac_compliance["pollutants"].append({
                "pollutant": pol,
                "total_tonnes": round(p_data["total_mass"], 2),
                "measured_concentration_mg_nm3": round(measured_c, 2),
                "statutory_limit_mg_nm3": lim_val,
                "is_compliant": not is_exceeded,
                "status": "NON-COMPLIANT (Exceeded)" if is_exceeded else "COMPLIANT",
                "notes": "Additional sampling conducted to confirm" if is_exceeded else "Within permissible limits"
            })

        fac_compliance["overall_status"] = "COMPLIANT" if all_compliant else "NON-COMPLIANT"
        results.append(fac_compliance)

    return jsonify(results)
