import json
import logging
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, session
from extensions import db
from models import User, Facility, OgmpSurvey, Emission, ActivityLog
from routes.auth import login_required
from services.sentinel5p import sentinel5p_service

logger = logging.getLogger(__name__)

satellite_bp = Blueprint("satellite", __name__)


def _get_user_copernicus_credentials(user_id: int = None):
    """Extracts Copernicus credentials from current user preferences or system-configured accounts."""
    if user_id:
        user = db.session.get(User, user_id)
        if user and user.preferences:
            try:
                prefs = (
                    json.loads(user.preferences)
                    if isinstance(user.preferences, str)
                    else user.preferences
                )
                if prefs.get("copernicus_username") or prefs.get(
                    "copernicus_client_id"
                ):
                    return {
                        "copernicus_username": prefs.get("copernicus_username"),
                        "copernicus_password": prefs.get("copernicus_password"),
                        "copernicus_client_id": prefs.get("copernicus_client_id"),
                        "copernicus_client_secret": prefs.get(
                            "copernicus_client_secret"
                        ),
                        "copernicus_qa_threshold": float(
                            prefs.get("copernicus_qa_threshold", 0.5)
                        ),
                    }
            except Exception as e:
                logger.warning(
                    f"Error parsing user preferences for Copernicus credentials: {e}"
                )

    # Fallback: check any user who saved valid Copernicus credentials
    try:
        configured_users = User.query.filter(User.preferences.isnot(None)).all()
        for u in configured_users:
            p = (
                json.loads(u.preferences)
                if isinstance(u.preferences, str)
                else u.preferences
            )
            if p.get("copernicus_username") or p.get("copernicus_client_id"):
                return {
                    "copernicus_username": p.get("copernicus_username"),
                    "copernicus_password": p.get("copernicus_password"),
                    "copernicus_client_id": p.get("copernicus_client_id"),
                    "copernicus_client_secret": p.get("copernicus_client_secret"),
                    "copernicus_qa_threshold": float(
                        p.get("copernicus_qa_threshold", 0.5)
                    ),
                }
    except Exception as e:
        logger.warning(f"Fallback check for Copernicus credentials failed: {e}")

    return {}


@satellite_bp.route("/sentinel5p/test-connection", methods=["POST"])
@login_required
def test_copernicus_connection():
    """
    Tests connection to the Copernicus Data Space Ecosystem (CDSE)
    using either request payload or saved user preferences.
    """
    user_id = session.get("user_id")
    data = request.get_json() or {}

    username = data.get("username") or data.get("copernicus_username")
    password = data.get("password") or data.get("copernicus_password")
    client_id = data.get("client_id") or data.get("copernicus_client_id")
    client_secret = data.get("client_secret") or data.get("copernicus_client_secret")

    # Fallback to saved user preferences if none passed in payload
    if not username and not client_id and user_id:
        saved_creds = _get_user_copernicus_credentials(user_id)
        username = saved_creds.get("copernicus_username")
        password = saved_creds.get("copernicus_password")
        client_id = saved_creds.get("copernicus_client_id")
        client_secret = saved_creds.get("copernicus_client_secret")

    result = sentinel5p_service.test_connection(
        username=username,
        password=password,
        client_id=client_id,
        client_secret=client_secret,
    )

    return jsonify(result), 200


@satellite_bp.route("/sentinel5p/layer-config", methods=["GET"])
@login_required
def get_satellite_layer_config():
    """
    Returns layer metadata, color scale intervals, and connection status for the frontend map.
    """
    user_id = session.get("user_id")
    creds = _get_user_copernicus_credentials(user_id) if user_id else {}
    config = sentinel5p_service.get_layer_config(credentials=creds)
    return jsonify(config), 200


@satellite_bp.route("/sentinel5p/query", methods=["GET", "POST"])
@satellite_bp.route("/sentinel5p/facility-timeseries", methods=["GET", "POST"])
@login_required
def get_facility_satellite_data():
    """
    Queries real Sentinel-5P observations for a facility or bounding box.
    Supports GET (query string) and POST (JSON body).
    """
    user_id = session.get("user_id")
    body = request.get_json(silent=True) or {}

    facility_id = body.get("facility_id") or request.args.get("facility_id", type=int)
    lat = body.get("latitude") or request.args.get("latitude", type=float)
    lon = body.get("longitude") or request.args.get("longitude", type=float)
    start_date = body.get("start_date") or request.args.get("start_date", default=None)
    end_date = body.get("end_date") or request.args.get("end_date", default=None)
    qa_threshold = body.get("qa_threshold") or request.args.get(
        "qa_threshold", default=0.5, type=float
    )

    if facility_id:
        facility = db.session.get(Facility, int(facility_id))
        if facility and facility.latitude and facility.longitude:
            lat = facility.latitude
            lon = facility.longitude

    if lat is None or lon is None:
        return (
            jsonify(
                {
                    "status": "missing_coordinates",
                    "message": "Valid facility latitude and longitude are required to query satellite column data.",
                }
            ),
            400,
        )

    creds = _get_user_copernicus_credentials(user_id) if user_id else {}
    result = sentinel5p_service.query_satellite_observations(
        lat=float(lat),
        lon=float(lon),
        start_date=str(start_date) if start_date else None,
        end_date=str(end_date) if end_date else None,
        credentials=creds,
        qa_threshold=float(qa_threshold),
    )

    return jsonify(result), 200


@satellite_bp.route("/sentinel5p/export-to-ogmp", methods=["POST"])
@login_required
def export_satellite_to_ogmp():
    """
    Exports a verified Sentinel-5P observation anomaly into an OGMP Level 4/5 Top-Down Survey record.
    """
    user_id = session.get("user_id")
    data = request.get_json() or {}

    facility_id = data.get("facility_id")
    if not facility_id:
        return jsonify({"error": "facility_id is required"}), 400

    facility = db.session.get(Facility, facility_id)
    if not facility:
        return jsonify({"error": "Facility not found"}), 404

    survey_date = data.get("survey_date") or datetime.now(timezone.utc).strftime(
        "%Y-%m-%d"
    )
    year = int(survey_date.split("-")[0])

    delta_ppb = float(data.get("delta_ch4_ppb") or 0.0)
    wind_speed = float(data.get("wind_speed_m_s") or 3.5)
    pbl_height = float(data.get("pbl_height_m") or 1200.0)
    operator_notes = (
        data.get("operator_notes")
        or "Top-down Sentinel-5P TROPOMI column anomaly flux estimation"
    )

    # Compute emission rate (kg/hr) using physical mass-balance formula
    measured_rate_kg_hr = sentinel5p_service.estimate_emission_rate_from_anomaly(
        delta_ch4_ppb=delta_ppb, wind_speed_m_s=wind_speed, pbl_height_m=pbl_height
    )
    operating_hours = float(data.get("operating_hours") or 8760.0)
    estimated_annual_tch4 = (measured_rate_kg_hr * operating_hours) / 1000.0

    # Retrieve bottom-up Scope 1 methane total for reconciliation comparison
    bottom_up_emissions = (
        db.session.query(db.func.sum(Emission.ch4_emissions))
        .filter(Emission.facility_id == facility_id, Emission.year == year)
        .scalar()
        or 0.0
    )

    variance_pct = 0.0
    if bottom_up_emissions > 0:
        variance_pct = round(
            ((estimated_annual_tch4 - bottom_up_emissions) / bottom_up_emissions)
            * 100.0,
            2,
        )

    thresh = facility.reconciliation_threshold or 20.0
    variance_flag = abs(variance_pct) > thresh

    survey = OgmpSurvey(
        facility_id=facility_id,
        year=year,
        survey_date=survey_date,
        survey_type="Satellite (Sentinel-5P / TROPOMI)",
        measured_rate_kg_hr=measured_rate_kg_hr,
        operating_hours_year=operating_hours,
        estimated_annual_tch4=round(estimated_annual_tch4, 3),
        detection_threshold=50.0,  # ~50 kg/hr regional detection threshold for S5P
        instrument_vendor="ESA Copernicus TROPOMI (Offline L3)",
        bottom_up_tch4=round(float(bottom_up_emissions), 3),
        variance_pct=variance_pct,
        variance_flag=variance_flag,
        reconciliation_status="Discrepancy Flagged" if variance_flag else "Reconciled",
        status="reviewed",
        operator_notes=operator_notes,
        created_by=user_id,
    )

    db.session.add(survey)

    # Activity logging
    log = ActivityLog(
        action="CREATE_OGMP_SATELLITE_SURVEY",
        entity="OgmpSurvey",
        entity_id=str(facility_id),
        user_id=user_id,
        details=f"Created Sentinel-5P satellite survey for facility '{facility.name}' (Measured: {estimated_annual_tch4:.2f} tCH4, Variance: {variance_pct}%)",
        metadata_json=json.dumps(
            {
                "delta_ch4_ppb": delta_ppb,
                "measured_rate_kg_hr": measured_rate_kg_hr,
                "variance_pct": variance_pct,
            }
        ),
    )
    db.session.add(log)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Sentinel-5P satellite survey recorded in OGMP ledger successfully",
                "id": survey.id,
                "estimated_annual_tch4": estimated_annual_tch4,
                "variance_pct": variance_pct,
                "variance_flag": variance_flag,
            }
        ),
        201,
    )


@satellite_bp.route("/sentinel5p/poll-new-passes", methods=["POST"])
@login_required
def poll_new_satellite_passes():
    """
    Called periodically by the frontend to check whether new Sentinel-5P NRTI
    passes have been published to the ESA Copernicus catalog for facilities
    with known coordinates.  If a new product is detected (product_id not seen
    before for this user), a Notification is created in the DB so it is
    delivered via the existing SSE notification stream.

    Returns a list of newly-detected facilities and the notification count.
    """
    from models import Notification
    from datetime import timedelta

    user_id = session.get("user_id")
    creds = _get_user_copernicus_credentials(user_id)
    if not creds or not (
        creds.get("copernicus_username") or creds.get("copernicus_client_id")
    ):
        return jsonify({"new_passes": 0, "message": "Copernicus not configured"}), 200

    # Read set of already-seen product IDs from user preferences
    user = db.session.get(User, user_id)
    prefs = {}
    try:
        prefs = json.loads(user.preferences) if user and user.preferences else {}
    except Exception:
        pass
    seen_ids = set(prefs.get("s5p_seen_product_ids", []))

    # Only query facilities that have coordinates (top 10 to keep response fast)
    facilities_to_check = (
        Facility.query.filter(
            Facility.latitude.isnot(None), Facility.longitude.isnot(None)
        )
        .order_by(Facility.id)
        .limit(10)
        .all()
    )

    new_detections = []
    for fac in facilities_to_check:
        try:
            result = sentinel5p_service.query_satellite_observations(
                lat=float(fac.latitude),
                lon=float(fac.longitude),
                start_date=None,
                end_date=None,
                credentials=creds,
                qa_threshold=float(creds.get("copernicus_qa_threshold", 0.5)),
            )
            if result.get("status") != "success":
                continue

            observations = result.get("observations", [])
            if not observations:
                continue

            # Check the most recent product
            latest_obs = observations[0]
            prod_id = latest_obs.get("product_id")
            prod_name = latest_obs.get("product_name", "")
            sensing_time = latest_obs.get("sensing_time", "")
            summary = result.get("summary", {})

            if not prod_id or prod_id in seen_ids:
                continue

            # New pass detected — mark as seen
            seen_ids.add(prod_id)

            # Determine stream type and anomaly severity
            is_nrti = "NRTI" in prod_name
            anomaly = summary.get("max_anomaly_ppb", 0.0)
            emission_rate = summary.get("estimated_emission_rate_kg_hr", 0.0)
            pass_date = sensing_time[:10] if sensing_time else "Unknown"
            pass_time = sensing_time[11:16] + " UTC" if len(sensing_time) >= 16 else ""

            if anomaly >= 30.0:
                notif_type = "critical"
                title = f"⚠ High CH₄ Anomaly Detected — {fac.name}"
                message = (
                    f"New Sentinel-5P {'NRTI' if is_nrti else 'OFFL'} overpass on {pass_date} {pass_time} "
                    f"detected a CH₄ column anomaly of +{anomaly:.1f} ppb above background at {fac.name}. "
                    f"Estimated flux: {emission_rate:.0f} kg/hr. Reconcile in OGMP Level 5 Ledger."
                )
            elif anomaly >= 10.0:
                notif_type = "warning"
                title = f"New S5P Pass — {fac.name}"
                message = (
                    f"Sentinel-5P overpass on {pass_date} {pass_time} at {fac.name}: "
                    f"CH₄ anomaly +{anomaly:.1f} ppb, estimated {emission_rate:.0f} kg/hr."
                )
            else:
                notif_type = "info"
                title = f"New Satellite Pass — {fac.name}"
                message = (
                    f"New Sentinel-5P overpass ({pass_date} {pass_time}) for {fac.name}. "
                    f"Mean CH₄ column: {summary.get('mean_ch4_column_ppb', 0):.1f} ppb (background baseline)."
                )

            # Deduplication: skip if identical unread notification exists within 12 hours
            cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
                hours=12
            )
            existing = Notification.query.filter(
                Notification.user_id == user_id,
                Notification.title == title,
                Notification.is_read == False,
                Notification.created_at >= cutoff,
            ).first()
            if not existing:
                Notification.create(
                    title=title, message=message, type=notif_type, user_id=user_id
                )
                new_detections.append(
                    {
                        "facility_id": fac.id,
                        "facility_name": fac.name,
                        "pass_date": pass_date,
                        "pass_time": pass_time,
                        "anomaly_ppb": anomaly,
                        "emission_rate_kg_hr": emission_rate,
                        "stream_type": "NRTI" if is_nrti else "OFFL",
                        "product_id": prod_id,
                    }
                )

        except Exception as exc:
            logger.warning(f"[PollPasses] Error querying facility {fac.name}: {exc}")
            continue

    # Persist updated seen product IDs back to user preferences
    if new_detections and user:
        try:
            prefs["s5p_seen_product_ids"] = list(seen_ids)[-200:]  # cap list at 200
            user.preferences = json.dumps(prefs)
            db.session.commit()
        except Exception as exc:
            logger.warning(f"[PollPasses] Could not persist seen product IDs: {exc}")

    return (
        jsonify({"new_passes": len(new_detections), "detections": new_detections}),
        200,
    )
