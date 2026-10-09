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
    # BUG-114: bumped on logout / password change / deactivation; sessions carrying an
    # older value are rejected, so a copied cookie stops working after logout.
    session_version = db.Column(db.Integer, default=0, server_default="0", nullable=False)

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
    equity_share_pct = db.Column(db.Float, default=100.0)
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
    # 255: catalog fuel names (75 chars) and activity-factor labels (70) overflowed 50 on PostgreSQL
    fuel_type = db.Column(db.String(255))
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
    # RC-10 (BUG-008/037): 1-sigma relative components kept separately so the inventory
    # can correlate the emission-factor part across records that share a factor.
    uncertainty_ad = db.Column(db.Float, nullable=True)
    uncertainty_ef_co2 = db.Column(db.Float, nullable=True)
    uncertainty_ef_ch4 = db.Column(db.Float, nullable=True)
    uncertainty_ef_n2o = db.Column(db.Float, nullable=True)
    ef_key = db.Column(db.String(200), nullable=True)  # identifies the factor for correlation
    qa_flag = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="Pending", index=True)

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
    # BUG-069: identity snapshots survive user deletion
    created_by_name = db.Column(db.String(255), nullable=True)
    approved_by_name = db.Column(db.String(255), nullable=True)
    # BUG-056: Tier 2 records reference their custom factor by id (real FK)
    custom_factor_id = db.Column(db.Integer, db.ForeignKey("custom_factors.id"), nullable=True, index=True)

    __table_args__ = (
        db.Index("ix_emissions_fac_yr_status", "facility_id", "year", "status"),
        db.Index("ix_emissions_act_div", "activity", "division"),
        db.Index("ix_emissions_status_yr_co2e", "status", "year", "co2e_total"),
        db.Index("ix_emissions_yr_status_proc", "year", "status", "process_type"),
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

    # Granular Production Metrics (API Compendium / Berkine standard)
    gross_gas_mmsm3 = db.Column(db.Float, default=0.0)
    injected_gas_mmsm3 = db.Column(db.Float, default=0.0)
    gas_without_injected_mmsm3 = db.Column(db.Float, default=0.0)
    crude_oil_mmboe = db.Column(db.Float, default=0.0)
    condensate_mmboe = db.Column(db.Float, default=0.0)
    lpg_mmboe = db.Column(db.Float, default=0.0)
    ngl_mmboe = db.Column(db.Float, default=0.0)
    total_production_mmboe = db.Column(db.Float, default=0.0)
    total_production_no_injected_mmboe = db.Column(db.Float, default=0.0)
    saleable_production_mmboe = db.Column(db.Float, default=0.0)
    fuel_gas_export_mmsm3 = db.Column(db.Float, default=0.0)

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
        db.Index("ix_prod_yr_fac_units", "year", "facility_id", "oil_unit", "gas_unit"),
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


class ComponentInventory(db.Model):
    __tablename__ = "component_inventories"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), index=True, nullable=False)
    emission_source_id = db.Column(db.Integer, db.ForeignKey("emission_sources.id"), nullable=True)
    facility = db.relationship("Facility", foreign_keys=[facility_id])
    emission_source = db.relationship("EmissionSource", foreign_keys=[emission_source_id])

    equipment_type = db.Column(db.String(100), nullable=False)
    component_type = db.Column(db.String(100), nullable=False)
    service_type = db.Column(db.String(50), nullable=False)  # Gas, Light Oil, Heavy Oil, Water/Oil
    quantity = db.Column(db.Integer, default=1, nullable=False)
    operating_hours = db.Column(db.Float, default=8760.0)
    methodology = db.Column(db.String(100), default="Component Average")
    factor_id = db.Column(db.String(100), nullable=True)
    factor_value = db.Column(db.Float, nullable=True)
    factor_unit = db.Column(db.String(50), nullable=True)
    api_reference = db.Column(db.String(120), nullable=True)
    status = db.Column(db.String(20), default="Active")
    description = db.Column(db.Text, nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, onupdate=utc_now)


class FugitiveSurvey(db.Model):
    __tablename__ = "fugitive_surveys"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), index=True, nullable=False)
    component_inventory_id = db.Column(db.Integer, db.ForeignKey("component_inventories.id"), nullable=True)
    facility = db.relationship("Facility", foreign_keys=[facility_id])
    component_inventory = db.relationship("ComponentInventory", foreign_keys=[component_inventory_id])

    survey_method = db.Column(db.String(50), nullable=False)  # Method 21, OGI, Measurement
    survey_date = db.Column(db.String(20), nullable=False)
    detection_threshold_ppm = db.Column(db.Float, nullable=True)
    screening_value_ppm = db.Column(db.Float, nullable=True)
    leak_status = db.Column(db.String(20), default="Non-leaking")  # Leaking, Non-leaking
    measured_emission_rate = db.Column(db.Float, nullable=True)
    measurement_unit = db.Column(db.String(50), nullable=True)  # kg/hr, scf/hr, m3/hr
    repair_date = db.Column(db.String(20), nullable=True)
    leaking_hours = db.Column(db.Float, default=8760.0)
    surveyor_name = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
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
    description = db.Column(db.Text, nullable=True)
    version = db.Column(db.String(20))
    uncertainty = db.Column(db.Float)  # legacy fallback
    co2_uncertainty = db.Column(db.Float)
    ch4_uncertainty = db.Column(db.Float)
    n2o_uncertainty = db.Column(db.Float)
    uncertainty_pct = db.Column(db.Float, nullable=True)  # Overall combined uncertainty percentage
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    updated_at = db.Column(db.DateTime, onupdate=utc_now)
    created_at = db.Column(db.DateTime, default=utc_now)
    # BUG-056: referenced factors are archived instead of deleted (ids are never reused)
    is_archived = db.Column(db.Boolean, default=False, server_default="0", nullable=False)
    # Maker-checker approval workflow
    status = db.Column(db.String(20), default="Approved", server_default="Approved", nullable=False, index=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)


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
    # BUG-038: facility the entry relates to (no FK: log rows outlive deleted facilities)
    facility_id = db.Column(db.Integer, nullable=True, index=True)
    metadata_json = db.Column("metadata", db.Text)
    timestamp = db.Column(db.DateTime, default=utc_now, index=True)
    # F12 (pilot check 2026-10-09): hash chain, sealed when the row is written (services/audit_chain.py)
    prev_hash = db.Column(db.String(64), nullable=True)
    entry_hash = db.Column(db.String(64), nullable=True)



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
    # Scope 2 Dual Reporting (GHG Protocol Scope 2 Guidance)
    co2e_location_based = db.Column(db.Float, nullable=True)
    co2e_market_based = db.Column(db.Float, nullable=True)
    market_instrument_type = db.Column(db.String(50), nullable=True)  # PPA, REC, GO, supplier_tariff, residual_mix
    market_emission_factor = db.Column(db.Float, nullable=True)
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
    status = db.Column(db.String(20), default="Pending", index=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    # Maker-Checker Approval
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(db.DateTime, onupdate=utc_now)
    created_by_name = db.Column(db.String(255), nullable=True)
    approved_by_name = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.Index("ix_scope2_fac_yr_status", "facility_id", "year", "status"),
        db.Index("ix_scope2_status_yr_co2e", "status", "year", "co2e", "electricity_kwh"),
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
    status = db.Column(db.String(20), default="Pending", index=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    # Maker-Checker Approval
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    updated_at = db.Column(db.DateTime, onupdate=utc_now)
    created_by_name = db.Column(db.String(255), nullable=True)
    approved_by_name = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.Index("ix_scope3_fac_yr_status", "facility_id", "year", "status"),
        db.Index("ix_scope3_status_yr_co2e", "status", "year", "co2e"),
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
    # BUG-009: deleted with its facility (was the only facility child without a cascade)
    facility = db.relationship("Facility", backref=db.backref("level_upgrade_logs", cascade="all, delete-orphan"))
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
    pathway_type = db.Column(db.String(20), default="1.5C")  # 1.5C, WB2C, custom
    # BUG-019: which scopes the base-year emissions / target cover ("S1S2S3" or "S1S2")
    scope_coverage = db.Column(db.String(10), default="S1S2S3", server_default="S1S2S3", nullable=False)
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


class CapEmission(db.Model):
    """
    Criteria Air Pollutants (CAP) - Mass and stack concentration tracking.
    Complies with Algerian Executive Decree 06-138 and API Compendium 2021.
    """
    __tablename__ = "cap_emissions"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), index=True, nullable=False)
    facility = db.relationship("Facility", backref=db.backref("cap_emissions", cascade="all, delete-orphan"))
    year = db.Column(db.Integer, index=True, nullable=False)
    month = db.Column(db.Integer, nullable=True)  # NULL for annual totals
    source_module = db.Column(db.String(100), index=True, nullable=False)  # Stationary Combustion, Flare, Equipment Leaks, O&G Venting, Total
    pollutant = db.Column(db.String(20), index=True, nullable=False)  # NO2, CO, SO2, PM, VOC
    mass_tonnes = db.Column(db.Float, default=0.0, nullable=False)
    concentration_mg_nm3 = db.Column(db.Float, nullable=True)
    flue_gas_volume_nm3 = db.Column(db.Float, nullable=True)
    calc_method = db.Column(db.String(100), default="API Compendium")
    notes = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default="Pending", index=True)  # BUG-053: maker-checker
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, onupdate=utc_now)
    updated_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_by_name = db.Column(db.String(255), nullable=True)
    approved_by_name = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.Index("ix_cap_fac_yr_mod_pol", "facility_id", "year", "source_module", "pollutant"),
    )


class CapRegulatoryLimit(db.Model):
    """
    Regulatory limit values for Criteria Air Pollutants in mg/Nm3.
    Default standard: Algerian Executive Decree No. 06-138.
    """
    __tablename__ = "cap_regulatory_limits"
    id = db.Column(db.Integer, primary_key=True)
    standard_name = db.Column(db.String(100), default="Executive Decree 06-138", nullable=False)
    pollutant = db.Column(db.String(20), nullable=False)  # NO2, CO, SO2, PM, VOC
    limit_mg_nm3 = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), default="mg/Nm3")
    notes = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("standard_name", "pollutant", name="_cap_standard_pollutant_uc"),
    )


class FlaringDetail(db.Model):
    """
    Detailed operational flaring streams (Routine, Non-Routine, Safety)
    and field-measured DRE for Algerian Executive Decree 21-330 compliance.
    """
    __tablename__ = "flaring_details"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), index=True, nullable=False)
    facility = db.relationship("Facility", backref=db.backref("flaring_details", cascade="all, delete-orphan"))
    year = db.Column(db.Integer, index=True, nullable=False)
    month = db.Column(db.Integer, nullable=True)
    network = db.Column(db.String(50), default="CPF")  # CPF or Field
    routine_knm3 = db.Column(db.Float, default=0.0)
    non_routine_knm3 = db.Column(db.Float, default=0.0)
    safety_knm3 = db.Column(db.Float, default=0.0)
    total_knm3 = db.Column(db.Float, default=0.0)
    measured_dre_pct = db.Column(db.Float, nullable=True)  # e.g. 99.85 from VISR camera
    dre_method = db.Column(db.String(100), default="VISR Camera")
    status = db.Column(db.String(20), default="Verified")
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.Index("ix_flare_fac_yr_net", "facility_id", "year", "network"),
    )


class JvPartner(db.Model):
    """
    Joint Venture Partner metadata for equity share carbon & methane accounting.
    """
    __tablename__ = "jv_partners"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)  # Sonatrach, Occidental, Eni, TotalEnergies, Pertamina, Repsol
    code = db.Column(db.String(50), unique=True, nullable=False)
    country = db.Column(db.String(100), default="Algeria")
    is_operator = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=utc_now)


class FacilityEquityShare(db.Model):
    """
    Time-sliced equity ownership percentages per facility.
    Supports mid-year ownership shifts (e.g. May 2, 2023).
    """
    __tablename__ = "facility_equity_shares"
    id = db.Column(db.Integer, primary_key=True)
    facility_id = db.Column(db.Integer, db.ForeignKey("facilities.id"), index=True, nullable=False)
    partner_id = db.Column(db.Integer, db.ForeignKey("jv_partners.id"), index=True, nullable=False)
    facility = db.relationship("Facility", backref=db.backref("equity_shares", cascade="all, delete-orphan"))
    partner = db.relationship("JvPartner", backref=db.backref("facility_shares", cascade="all, delete-orphan"))
    equity_share_pct = db.Column(db.Float, nullable=False)  # e.g. 51.0, 24.5
    effective_start_date = db.Column(db.String(20), default="2021-01-01", nullable=False)
    effective_end_date = db.Column(db.String(20), nullable=True)  # None = currently active
    agreement_reference = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    __table_args__ = (
        db.Index("ix_fac_partner_date", "facility_id", "partner_id", "effective_start_date"),
    )


class ImportMapping(db.Model):
    """A column mapping a user saved in the import wizard: re-applied to files with the same columns
    (a monthly export from the same system), so the columns are not matched by hand again."""
    __tablename__ = "import_mappings"
    __table_args__ = (db.UniqueConstraint("user_id", "scope", "name", name="uq_import_mapping_user_scope_name"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    scope = db.Column(db.String(20), nullable=False, default="1")
    name = db.Column(db.String(80), nullable=False)
    headers = db.Column(db.Text, nullable=False)   # JSON list of the file's column names
    mapping = db.Column(db.Text, nullable=False)   # JSON object field -> column name
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    last_used_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        import json

        return {
            "id": self.id, "scope": self.scope, "name": self.name,
            "headers": json.loads(self.headers or "[]"), "mapping": json.loads(self.mapping or "{}"),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }

