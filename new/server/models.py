from extensions import db
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    fullName = db.Column(db.String(120), nullable=False)
    orgName = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    sector = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, index=True)
    jobTitle = db.Column(db.String(100))
    department = db.Column(db.String(100))
    phone = db.Column(db.String(20))
    location = db.Column(db.String(100))
    bio = db.Column(db.Text)
    profilePic = db.Column(db.String(255))
    consolidationApproach = db.Column(db.String(50))
    role = db.Column(db.String(20), default="user")
    status = db.Column(db.String(20), default="active")
    password_updated_at = db.Column(db.DateTime, default=utc_now)
    last_login = db.Column(db.DateTime)
    preferences = db.Column(
        db.Text
    )  # JSON string for user settings (theme, language, etc.)
    created_at = db.Column(db.DateTime, default=utc_now)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Facility(db.Model):
    __tablename__ = "facilities"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    location = db.Column(db.String(120))
    description = db.Column(db.Text)
    boundary_notes = db.Column(db.Text)
    boundary_type = db.Column(db.String(100), default="Operational Control")
    boundary_detail = db.Column(db.Text)
    activity = db.Column(db.String(100))
    division = db.Column(db.String(100))
    region = db.Column(db.String(100))
    field = db.Column(db.String(100))  # OF / GF / GNL / GPL / Raffinerie / Pétrochimie
    code = db.Column(db.String(50), unique=True)
    external_id = db.Column(db.String(50))
    segment = db.Column(db.String(20))  # Upstream, Midstream, Downstream
    operator_status = db.Column(
        db.String(20), default="operated"
    )  # operated, non_operated
    country = db.Column(db.String(100), default="Algeria")
    ogmp_membership_year = db.Column(db.Integer, default=2023)
    reconciliation_threshold = db.Column(
        db.Float, default=20.0
    )  # % threshold for variance flagging
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, onupdate=utc_now)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Cascading Deletes
    emissions = db.relationship(
        "Emission", backref="facility_parent", cascade="all, delete-orphan", lazy=True
    )
    production_data = db.relationship(
        "ProductionData",
        backref="facility_parent",
        cascade="all, delete-orphan",
        lazy=True,
    )
    emission_sources = db.relationship(
        "EmissionSource",
        backref="facility_parent",
        cascade="all, delete-orphan",
        lazy=True,
    )
    scope2_emissions = db.relationship(
        "Scope2Emission",
        backref="facility_parent",
        cascade="all, delete-orphan",
        lazy=True,
    )
    scope3_emissions = db.relationship(
        "Scope3Emission",
        backref="facility_parent",
        cascade="all, delete-orphan",
        lazy=True,
    )
    mitigation_projects = db.relationship(
        "MitigationProject",
        backref="facility_parent",
        cascade="all, delete-orphan",
        lazy=True,
    )
    cbam_exports = db.relationship(
        "CbamProductExport",
        backref="facility_parent",
        cascade="all, delete-orphan",
        lazy=True,
    )
    ogmp_surveys = db.relationship(
        "OgmpSurvey", backref="facility_parent", cascade="all, delete-orphan", lazy=True
    )


class Emission(db.Model):
    __tablename__ = "emissions"
    id = db.Column(db.Integer, primary_key=True)
    record_id = db.Column(db.String(50), unique=True, index=True)
    year = db.Column(db.Integer, index=True)
    month = db.Column(db.Integer)
    company_name = db.Column(db.String(120))
    group_name = db.Column(db.String(120), index=True)
    equipment_id = db.Column(db.String(50))
    process_type = db.Column(db.String(50), index=True)
    fuel_type = db.Column(db.String(50))
    quantity = db.Column(db.Float)
    unit = db.Column(db.String(20))
    factor_source = db.Column(db.String(50))

    # EF Used
    ef_used_co2 = db.Column(db.Float)
    ef_used_ch4 = db.Column(db.Float)
    ef_used_n2o = db.Column(db.Float)
    ef_used_co = db.Column(db.Float, default=0)

    # Calculated Emissions
    co2_emissions = db.Column(db.Float)
    ch4_emissions = db.Column(db.Float)
    n2o_emissions = db.Column(db.Float)
    co_emissions = db.Column(db.Float, default=0)
    co2e_total = db.Column(db.Float)
    co2_biogenic = db.Column(db.Float, default=0)

    combustion_efficiency = db.Column(db.Float, default=0)
    # Per-GHG relative uncertainties (e.g. 0.05 = ±5%).
    # Only populated for default (API-catalogue) factors;
    # NULL for custom or specific (measurement-based) factors.
    uncertainty = db.Column(db.Float, nullable=True)  # CO₂ uncertainty
    uncertainty_ch4 = db.Column(db.Float, nullable=True)  # CH₄ uncertainty
    uncertainty_n2o = db.Column(db.Float, nullable=True)  # N₂O uncertainty
    uncertainty_pct = db.Column(db.Float, nullable=True)  # Overall combined uncertainty percentage
    qa_flag = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="Verified", index=True)

    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), index=True)
    facility = db.relationship("Facility", overlaps="emissions,facility_parent")

    activity = db.Column(db.String(100), index=True)
    division = db.Column(db.String(100), index=True)
    region = db.Column(db.String(100))
    field = db.Column(db.String(100))  # OF / GF / GNL / GPL / Raffinerie / Pétrochimie

    calc_method = db.Column(
        db.String(50)
    )  # ef_generic, ef_facility_specific, direct_measurement, engineering_estimate
    calc_version = db.Column(db.String(20))
    factor_version = db.Column(db.String(50))
    ogmp_level = db.Column(db.Integer, default=3)  # 1 to 5
    source_type_code = db.Column(db.String(50))  # Link to MethaneSourceType code
    data_source_ref = db.Column(db.String(120))  # Survey ID, sensor ID, or EF table ref
    gwp_version = db.Column(db.String(20))
    source_payload = db.Column(db.Text)  # JSON string

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, onupdate=utc_now)
    timestamp = db.Column(db.DateTime, default=utc_now, index=True)
    # Maker-Checker Approval
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_emissions_fac_yr_status", "facility_id", "year", "status"),
        db.Index("ix_emissions_act_div", "activity", "division"),
    )


class ProductionData(db.Model):
    __tablename__ = "production_data"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(
        db.Integer, db.ForeignKey("facilities.id"), nullable=False, index=True
    )
    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False, index=True)
    oil_amount = db.Column(db.Float, default=0)
    gas_amount = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20), default="bbl")  # Legacy
    oil_unit = db.Column(db.String(20), default="bbl")
    gas_unit = db.Column(db.String(20), default="mscf")

    activity = db.Column(db.String(100), index=True)
    division = db.Column(db.String(100), index=True)
    region = db.Column(db.String(100))
    field = db.Column(db.String(100))  # OF / GF / GNL / GPL / Raffinerie / Pétrochimie

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, onupdate=utc_now)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.UniqueConstraint(
            "facility_id", "month", "year", name="_facility_month_year_uc"
        ),
    )


class EmissionSource(db.Model):
    __tablename__ = "emission_sources"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"))
    name = db.Column(db.String(120))
    type = db.Column(db.String(50))
    equipment_id = db.Column(db.String(50))
    fuel_type = db.Column(db.String(50))
    design_capacity = db.Column(db.String(50))
    installation_date = db.Column(db.String(20))
    status = db.Column(db.String(20), default="Active")
    description = db.Column(db.Text)

    activity = db.Column(db.String(100))
    division = db.Column(db.String(100))
    region = db.Column(db.String(100))
    field = db.Column(db.String(100))  # OF / GF / GNL / GPL / Raffinerie / Pétrochimie
    code = db.Column(db.String(50), unique=True)
    external_id = db.Column(db.String(50))

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, onupdate=utc_now)
    created_at = db.Column(db.DateTime, default=utc_now)


class CustomFactor(db.Model):
    __tablename__ = "custom_factors"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), index=True)
    co2_factor = db.Column(db.Float)
    ch4_factor = db.Column(db.Float)
    n2o_factor = db.Column(db.Float)
    co_factor = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20))
    hhv_factor = db.Column(db.Float)
    usage = db.Column(db.String(100))  # stored as stringified list or CSV
    parent_fuel = db.Column(db.String(50))
    source = db.Column(db.String(100))
    version = db.Column(db.String(20))
    uncertainty = db.Column(db.Float)  # legacy fallback
    co2_uncertainty = db.Column(db.Float)
    ch4_uncertainty = db.Column(db.Float)
    n2o_uncertainty = db.Column(db.Float)
    uncertainty_pct = db.Column(db.Float, nullable=True)  # Overall combined uncertainty percentage
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, onupdate=utc_now)
    created_at = db.Column(db.DateTime, default=utc_now)


class ActivityLog(db.Model):
    __tablename__ = "activity_log"
    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(50), index=True)  # DB-03 FIX: add index
    record_id = db.Column(db.String(50))
    user_name = db.Column(db.String(120))
    details = db.Column(db.Text)
    old_values = db.Column(db.Text, nullable=True)  # JSON before-state diff
    new_values = db.Column(db.Text, nullable=True)  # JSON after-state diff
    ip_address = db.Column(db.String(50))
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), index=True
    )  # DB-03 FIX: add index
    entity = db.Column(db.String(50), index=True)  # DB-03 FIX: add index
    entity_id = db.Column(db.String(50))
    metadata_json = db.Column("metadata", db.Text)
    timestamp = db.Column(db.DateTime, default=utc_now, index=True)



class Goal(db.Model):
    __tablename__ = "goals"
    year = db.Column(db.Integer, primary_key=True)
    target_amount = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=utc_now)


class BaseYear(db.Model):
    __tablename__ = "base_year"
    id = db.Column(
        db.Integer, primary_key=True
    )  # DB-02 FIX: enforced singleton via CheckConstraint below
    year = db.Column(db.Integer, nullable=False)
    locked = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=utc_now)

    # DB-02 FIX: Only one row is ever allowed (id must equal 1)
    __table_args__ = (db.CheckConstraint("id = 1", name="base_year_singleton"),)


class MitigationRecord(db.Model):
    __tablename__ = "mitigation_records"
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, index=True)
    type = db.Column(db.String(50))
    subtype = db.Column(db.String(50))
    quantity_tco2e = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    reference_id = db.Column(db.String(50))
    date_added = db.Column(db.DateTime, default=utc_now)


class Scope3Data(db.Model):
    __tablename__ = "scope3_data"
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, index=True)
    category = db.Column(db.String(100), default="Category 11")
    method = db.Column(db.String(50))
    product_type = db.Column(db.String(50))
    volume = db.Column(db.Float, default=0)
    unit = db.Column(db.String(20))
    emission_factor = db.Column(db.Float, default=0)
    emissions_tco2e = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=utc_now)


class Scope2Emission(db.Model):
    __tablename__ = "scope2_emissions"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), index=True)
    facility = db.relationship("Facility", overlaps="facility_parent,scope2_emissions")
    year = db.Column(db.Integer, index=True)
    month = db.Column(db.Integer)
    source_type = db.Column(db.String(50))  # electricity, steam, heat, cooling
    electricity_kwh = db.Column(db.Float, default=0)
    steam_ton = db.Column(db.Float, default=0)
    heat_mmbtu = db.Column(db.Float, default=0)
    cooling_ton = db.Column(db.Float, default=0)
    emission_factor = db.Column(db.Float)
    co2e = db.Column(db.Float)
    uncertainty = db.Column(db.Float, nullable=True)  # 1-sigma relative uncertainty
    uncertainty_pct = db.Column(db.Float, nullable=True)  # Overall combined uncertainty percentage
    qa_flag = db.Column(db.String(255), nullable=True)
    location = db.Column(db.String(100))
    grid_region = db.Column(db.String(100))

    # Matching Scope 1 Identity
    activity = db.Column(db.String(100), index=True)
    division = db.Column(db.String(100), index=True)
    region = db.Column(db.String(100))
    field = db.Column(db.String(100))  # OF / GF / GNL / GPL / Raffinerie / Pétrochimie

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    status = db.Column(db.String(20), default="Verified", index=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    # Maker-Checker Approval
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_scope2_fac_yr_status", "facility_id", "year", "status"),
    )


class Scope3Emission(db.Model):
    __tablename__ = "scope3_emissions"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), index=True)
    facility = db.relationship("Facility", overlaps="facility_parent,scope3_emissions")
    year = db.Column(db.Integer, index=True)
    month = db.Column(db.Integer)
    category = db.Column(db.String(100))  # Category 11, etc.
    sub_category = db.Column(db.String(100))
    activity_data = db.Column(db.Float, default=0)
    unit = db.Column(db.String(50))
    emission_factor = db.Column(db.Float)
    co2e = db.Column(db.Float)
    uncertainty = db.Column(db.Float, nullable=True)  # 1-sigma relative uncertainty
    uncertainty_pct = db.Column(db.Float, nullable=True)  # Overall combined uncertainty percentage
    qa_flag = db.Column(db.String(255), nullable=True)
    calculation_method = db.Column(db.String(50))
    data_quality = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    status = db.Column(db.String(20), default="Verified", index=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    # Maker-Checker Approval
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.Index("ix_scope3_fac_yr_status", "facility_id", "year", "status"),
    )


class MitigationProject(db.Model):
    __tablename__ = "mitigation_projects"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    project_type = db.Column(
        db.String(100)
    )  # renewable, efficiency, carbon_capture, etc.
    year = db.Column(db.Integer, index=True)
    quantity_tco2e = db.Column(db.Float, default=0)
    status = db.Column(db.String(50), default="active")  # active, planned, completed
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    investment_amount = db.Column(db.Float)
    description = db.Column(db.Text)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"))
    facility = db.relationship(
        "Facility", overlaps="facility_parent,mitigation_projects"
    )
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utc_now)


class BaseYearRecalculation(db.Model):
    __tablename__ = "base_year_recalculations"
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=False)
    recalc_date = db.Column(db.DateTime, default=utc_now)
    previous_emissions = db.Column(db.Float)
    adjusted_emissions = db.Column(db.Float)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utc_now)


class ReportingMetadata(db.Model):
    __tablename__ = "reporting_metadata"
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, unique=True)
    has_reduction_target = db.Column(db.Integer, default=0)
    target_description = db.Column(db.Text)
    is_tcfd_aligned = db.Column(db.Integer, default=0)
    assurance_level = db.Column(db.String(50))
    assurance_provider = db.Column(db.String(100))
    notes = db.Column(db.Text)


class Notification(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=True
    )  # Nullable for system-wide
    type = db.Column(
        db.String(50)
    )  # 'goal', 'audit', 'system', 'critical', 'warning', 'info'
    title = db.Column(db.String(120))
    message = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    metadata_json = db.Column("metadata", db.Text)  # JSON string for extra data

    @staticmethod
    def create(title, message, type="info", user_id=None, metadata=None):
        import json

        n = Notification(
            title=title,
            message=message,
            type=type,
            user_id=user_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        db.session.add(n)
        # NOTE: Do NOT call db.session.commit() here.
        # The caller (log_activity_and_notify → route handler) commits the full
        # transaction atomically: emission/data + activity log + notification.
        return n


class CbamProductExport(db.Model):
    __tablename__ = 'cbam_product_exports'
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey('facilities.id'), index=True, nullable=False)
    facility = db.relationship('Facility', overlaps="facility_parent,cbam_exports")
    year = db.Column(db.Integer, index=True, nullable=False)
    month = db.Column(db.Integer, nullable=False, default=1)
    product_name = db.Column(db.String(120), nullable=False)
    cn_code = db.Column(db.String(50), nullable=False, index=True) # e.g. '2814 10 00', '2804 10 00', '2710'
    quantity_tonnes = db.Column(db.Float, nullable=False, default=0.0)
    export_destination = db.Column(db.String(100), default='EU')
    specific_embedded_direct = db.Column(db.Float, default=0.0)   # tCO2e / t product
    specific_embedded_indirect = db.Column(db.Float, default=0.0) # tCO2e / t product
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=utc_now)


class OgmpSurvey(db.Model):
    __tablename__ = "ogmp_surveys"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(
        db.Integer, db.ForeignKey("facilities.id"), index=True, nullable=False
    )
    facility = db.relationship("Facility", overlaps="facility_parent,ogmp_surveys")
    year = db.Column(db.Integer, index=True, nullable=False)
    survey_date = db.Column(db.String(20), nullable=False)  # YYYY-MM-DD
    survey_type = db.Column(
        db.String(50), nullable=False
    )  # Satellite (Sentinel-5P/MethaneSAT), Flyover/Aerial, Drone OGI, Continuous Monitor, Site Survey
    measured_rate_kg_hr = db.Column(db.Float, nullable=False, default=0.0)
    operating_hours_year = db.Column(db.Float, default=8760.0)
    estimated_annual_tch4 = db.Column(db.Float, default=0.0)
    detection_threshold = db.Column(db.Float)  # kg/hr
    instrument_vendor = db.Column(
        db.String(100)
    )  # FLIR GF320, Bridger LiDAR, GHGSat, etc.
    raw_file_ref = db.Column(db.String(255))
    bottom_up_tch4 = db.Column(db.Float, default=0.0)
    variance_pct = db.Column(db.Float, default=0.0)
    variance_flag = db.Column(db.Boolean, default=False)
    reconciliation_status = db.Column(
        db.String(50), default="Reconciled"
    )  # Reconciled, Discrepancy Flagged, Pending
    status = db.Column(db.String(50), default="pending")  # pending, reviewed, reported
    operator_notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_at = db.Column(db.DateTime, default=utc_now)


class MethaneSourceType(db.Model):
    __tablename__ = "methane_source_types"
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, index=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(
        db.String(50), nullable=False
    )  # fugitive / vented / combustion_slip / flaring
    default_ef_reference = db.Column(db.String(150))
    default_level = db.Column(db.Integer, default=3)
    created_at = db.Column(db.DateTime, default=utc_now)


class LevelUpgradeLog(db.Model):
    __tablename__ = "level_upgrade_logs"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(
        db.Integer, db.ForeignKey("facilities.id"), nullable=False, index=True
    )
    facility = db.relationship("Facility")
    source_type_code = db.Column(db.String(50))
    old_level = db.Column(db.Integer, nullable=False)
    new_level = db.Column(db.Integer, nullable=False)
    target_date = db.Column(db.String(20))
    justification = db.Column(db.Text)
    changed_at = db.Column(db.DateTime, default=utc_now)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))


class SbtiTarget(db.Model):
    __tablename__ = "sbti_targets"
    id = db.Column(db.Integer, primary_key=True)
    base_year = db.Column(db.Integer, nullable=False)
    base_year_emissions = db.Column(db.Float, nullable=False)
    target_year = db.Column(db.Integer, default=2050)
    reduction_rate_pct = db.Column(db.Float, default=4.2)
    pathway_type = db.Column(db.String(20), default="1.5C")  # 1.5C, WB2C
    created_at = db.Column(db.DateTime, default=utc_now)
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))


class SystemSetting(db.Model):
    """
    Persistent key-value store for application-wide settings
    (GWP standard, OGMP parameters, WEC fees, Copernicus credentials, etc.)
    Survives server restarts and multi-worker deployments.
    """
    __tablename__ = "system_settings"
    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.Text, nullable=False)  # JSON-encoded value
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

