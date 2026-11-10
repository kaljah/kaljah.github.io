#!/usr/bin/env python3
"""
Synthetic Demo Dataset Builder (Idempotent, Clean From Scratch)
===============================================================
Builds a complete, client-free synthetic GHG dataset for live GIZ demos
and hands-on GIZ staff sandbox sessions.

Usage:
    python scripts/seed_demo.py [--db new/server/ghg_app.db] [--recreate] [--reset-passwords] [--template new/server/demo_template.db]
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import secrets
import shutil
import sqlite3
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SERVER_DIR = REPO_ROOT / "new" / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

DEMO_ENTITIES = [
    {"name": "Demo Operator Co.", "code": "DOC", "country": "Algeria", "is_operator": True},
    {"name": "Demo JV Partner A", "code": "JVPA", "country": "Algeria", "is_operator": False},
    {"name": "Demo JV Partner B", "code": "JVPB", "country": "Algeria", "is_operator": False},
]

DEMO_FACILITIES = [
    {
        "code": "FAC-A1",
        "name": "Facility A-1",
        "location": "Sector Alpha",
        "region": "Basin Alpha",
        "division": "Production",
        "activity": "EP",
        "segment": "Upstream",
        "field": "OF",
        "country": "Algeria",
        "latitude": 31.6800,
        "longitude": 6.0650,
        "description": "Synthetic central processing facility with oil stabilization, compression trains, and gas reinjection.",
        "operator_status": "operated",
        "equity_share_pct": 60.0,
        "ogmp_membership_year": 2023,
        "reconciliation_threshold": 15.0,
    },
    {
        "code": "FAC-B2",
        "name": "Facility B-2",
        "location": "Sector Beta",
        "region": "Basin Beta",
        "division": "Gas Processing",
        "activity": "GP",
        "segment": "Upstream",
        "field": "GF",
        "country": "Algeria",
        "latitude": 32.9300,
        "longitude": 3.2700,
        "description": "Synthetic wet gas processing hub with NGL recovery and booster compression.",
        "operator_status": "operated",
        "equity_share_pct": 70.0,
        "ogmp_membership_year": 2023,
        "reconciliation_threshold": 15.0,
    },
    {
        "code": "FAC-C3",
        "name": "Facility C-3",
        "location": "Coastal Hub",
        "region": "Coastal Terminal",
        "division": "Terminal & Export",
        "activity": "LNG",
        "segment": "Midstream",
        "field": "GNL",
        "country": "Algeria",
        "latitude": 35.8500,
        "longitude": -0.2800,
        "description": "Synthetic coastal midstream stabilization and marine export terminal.",
        "operator_status": "operated",
        "equity_share_pct": 100.0,
        "ogmp_membership_year": 2023,
        "reconciliation_threshold": 10.0,
    },
]

DEMO_USERS = [
    {
        "email": "demo.admin@example.org",
        "role": "admin",
        "fullName": "Demo Administrator",
        "orgName": "Demo Operator Co.",
        "jobTitle": "Corporate GHG Lead",
        "department": "HSE & Sustainability",
        "location": "All",
    },
    {
        "email": "demo.operator@example.org",
        "role": "user",
        "fullName": "Demo Operator",
        "orgName": "Demo Operator Co.",
        "jobTitle": "Facility MRV Engineer",
        "department": "Operations",
        "location": "Basin Alpha",
    },
    {
        "email": "demo.auditor@example.org",
        "role": "auditor",
        "fullName": "Demo Auditor",
        "orgName": "Demo Operator Co.",
        "jobTitle": "Lead ISO 14064 Verifier",
        "department": "Assurance & Audit",
        "location": "All",
    },
]

_XSS_SSTI_PATTERNS = ("%<script%", "%<svg%", "%onload=%", "%onerror=%", "%{{%", "%${%")


def _generate_runtime_password(length: int = 16) -> str:
    """Generates a cryptographically random password meeting complexity policy at runtime."""
    upper = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    lower = "abcdefghijkmnopqrstuvwxyz"
    digits = "23456789"
    special = "!@#$%&*-_+="
    all_chars = upper + lower + digits + special
    chars = [
        secrets.choice(upper),
        secrets.choice(lower),
        secrets.choice(digits),
        secrets.choice(special),
    ] + [secrets.choice(all_chars) for _ in range(max(8, length - 4))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def _purge_xss_ssti_and_retired_secrets(db) -> None:
    """Removes any stored XSS/SSTI test artifacts and retired CDSE/Copernicus DB keys."""
    from models import (
        CustomFactor,
        Emission,
        EmissionSource,
        Facility,
        MitigationProject,
        SystemSetting,
        User,
    )

    for key in (
        "copernicus_username",
        "copernicus_password",
        "copernicus_client_id",
        "copernicus_client_secret",
        "copernicus_qa_threshold",
        "copernicus_enabled",
    ):
        SystemSetting.query.filter_by(key=key).delete(synchronize_session=False)

    # Remove rows explicitly marked is_test=True
    for model_cls in (Emission, Facility, EmissionSource, CustomFactor, MitigationProject):
        if hasattr(model_cls, "is_test"):
            model_cls.query.filter_by(is_test=True).delete(synchronize_session=False)
    User.query.filter_by(is_test=True).delete(synchronize_session=False)

    # Remove stored XSS / SSTI strings if any slipped in
    for model_cls, cols in [
        (Facility, ["name", "location", "description"]),
        (Emission, ["fuel_type", "record_id", "data_source_ref"]),
        (EmissionSource, ["name", "description"]),
        (CustomFactor, ["name", "description"]),
        (MitigationProject, ["name", "description"]),
    ]:
        for col_name in cols:
            col = getattr(model_cls, col_name, None)
            if col is None:
                continue
            for pat in _XSS_SSTI_PATTERNS:
                model_cls.query.filter(col.ilike(pat)).delete(synchronize_session=False)

    db.session.commit()


def _vacuum_sqlite_file(db_path: Path) -> None:
    """Checkpoints WAL if active, compacts SQLite DB with VACUUM, leaving 0 freelist pages."""
    if not db_path.exists():
        return
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.commit()
        conn.execute("PRAGMA journal_mode = DELETE")
        conn.execute("VACUUM")
        conn.execute("ANALYZE")
        conn.commit()
        conn.execute("PRAGMA journal_mode = WAL")
        conn.commit()
    finally:
        conn.close()


def seed_demo_in_app(
    app,
    *,
    reset_passwords: bool = False,
    print_credentials: bool = True,
) -> dict[str, str]:
    """Idempotently populates all demo entities, facilities, users, and synthetic datasets."""
    from extensions import db
    from models import (
        ActivityLog,
        BaseYear,
        BaseYearRecalculation,
        CbamProductExport,
        ComponentInventory,
        CustomFactor,
        Emission,
        EmissionSource,
        Facility,
        FacilityEquityShare,
        FactorProvenanceRegistry,
        FlaringDetail,
        FugitiveSurvey,
        Goal,
        JvPartner,
        LevelUpgradeLog,
        MethaneSourceType,
        MitigationProject,
        MitigationRecord,
        OgmpSurvey,
        ProductionData,
        ReportingMetadata,
        SbtiTarget,
        Scope2Emission,
        Scope3Data,
        Scope3Emission,
        SystemSetting,
        User,
        UserFacilityAccess,
    )
    from routes.dashboard import clear_dashboard_cache

    generated_creds: dict[str, str] = {}

    with app.app_context():
        db.create_all()
        _purge_xss_ssti_and_retired_secrets(db)

        # 1. Entities (JV Partners)
        partners_by_code: dict[str, JvPartner] = {}
        for p_spec in DEMO_ENTITIES:
            partner = JvPartner.query.filter_by(code=p_spec["code"]).first()
            if not partner:
                partner = JvPartner.query.filter_by(name=p_spec["name"]).first()
            if not partner:
                partner = JvPartner(**p_spec)
                db.session.add(partner)
                db.session.flush()
            else:
                for k, v in p_spec.items():
                    setattr(partner, k, v)
            partners_by_code[p_spec["code"]] = partner
        db.session.commit()

        # 2. Facilities
        facs_by_code: dict[str, Facility] = {}
        for f_spec in DEMO_FACILITIES:
            fac = Facility.query.filter_by(code=f_spec["code"]).first()
            if not fac:
                fac = Facility.query.filter_by(name=f_spec["name"]).first()
            if not fac:
                fac = Facility(**f_spec)
                db.session.add(fac)
                db.session.flush()
            else:
                for k, v in f_spec.items():
                    setattr(fac, k, v)
            facs_by_code[f_spec["code"]] = fac
        db.session.commit()

        # 3. Equity Shares
        equity_blueprints = [
            ("FAC-A1", [("DOC", 60.0), ("JVPA", 25.0), ("JVPB", 15.0)]),
            ("FAC-B2", [("DOC", 70.0), ("JVPA", 30.0)]),
            ("FAC-C3", [("DOC", 100.0)]),
        ]
        for fac_code, splits in equity_blueprints:
            fac = facs_by_code[fac_code]
            for partner_code, pct in splits:
                partner = partners_by_code[partner_code]
                eq = FacilityEquityShare.query.filter_by(
                    facility_id=fac.id, partner_id=partner.id
                ).first()
                if not eq:
                    db.session.add(
                        FacilityEquityShare(
                            facility_id=fac.id,
                            partner_id=partner.id,
                            equity_share_pct=pct,
                            effective_start_date="2022-01-01",
                            agreement_reference=f"DEMO-JVA-{fac_code}",
                        )
                    )
                else:
                    eq.equity_share_pct = pct
        db.session.commit()

        # 4. Demo Users (passwords generated at seed time, never hardcoded)
        admin_user: User | None = None
        for u_spec in DEMO_USERS:
            user = User.query.filter_by(email=u_spec["email"]).first()
            if not user:
                raw_pw = _generate_runtime_password()
                user = User(
                    email=u_spec["email"],
                    fullName=u_spec["fullName"],
                    orgName=u_spec["orgName"],
                    role=u_spec["role"],
                    sector="Oil & Gas",
                    department=u_spec["department"],
                    jobTitle=u_spec["jobTitle"],
                    location=u_spec["location"],
                    status="active",
                    consolidationApproach="Operational Control",
                )
                user.set_password(raw_pw)
                db.session.add(user)
                db.session.flush()
                generated_creds[u_spec["email"]] = raw_pw
            else:
                user.fullName = u_spec["fullName"]
                user.orgName = u_spec["orgName"]
                user.role = u_spec["role"]
                user.jobTitle = u_spec["jobTitle"]
                user.department = u_spec["department"]
                user.location = u_spec["location"]
                user.status = "active"
                if reset_passwords:
                    raw_pw = _generate_runtime_password()
                    user.set_password(raw_pw)
                    user.session_version = (user.session_version or 0) + 1
                    generated_creds[u_spec["email"]] = raw_pw
            if u_spec["role"] == "admin":
                admin_user = user

            # Ensure UserFacilityAccess for operator & auditor across all demo facilities
            if u_spec["role"] in ("user", "auditor"):
                access_lvl = "verifier" if u_spec["role"] == "auditor" else "operator"
                for fac in facs_by_code.values():
                    ufa = UserFacilityAccess.query.filter_by(
                        user_id=user.id, facility_id=fac.id
                    ).first()
                    if not ufa:
                        db.session.add(
                            UserFacilityAccess(
                                user_id=user.id,
                                facility_id=fac.id,
                                access_level=access_lvl,
                            )
                        )
        db.session.commit()

        # 5. Factor Provenance Registry & Methane Source Types
        try:
            from scripts.verified_factors_seed_data import ALL_VERIFIED_FACTORS

            for fdata in ALL_VERIFIED_FACTORS:
                existing = db.session.get(FactorProvenanceRegistry, fdata["id"])
                if not existing:
                    db.session.add(FactorProvenanceRegistry(**fdata))
            db.session.commit()
        except Exception:
            db.session.rollback()

        methane_types = [
            ("FUG-VALVES", "Valves & Connectors Fugitive Leaks", "fugitive", "API Compendium Table 6-1", 4),
            ("VENT-TANKS", "Storage Tank Flashing & Venting", "vented", "API Compendium Sec 5.4", 4),
            ("FLR-HDR", "Continuous & Routine Flare Slip", "flaring", "API Compendium Eq 4-15", 4),
            ("COMP-SEAL", "Centrifugal Compressor Wet Seals", "combustion_slip", "OGMP 2.0 Technical Guidance", 5),
        ]
        for code, name, cat, ref, lvl in methane_types:
            if not MethaneSourceType.query.filter_by(code=code).first():
                db.session.add(
                    MethaneSourceType(
                        code=code,
                        name=name,
                        category=cat,
                        default_ef_reference=ref,
                        default_level=lvl,
                    )
                )
        db.session.commit()

        # 6. Emission Sources, Custom Factor, LDAR Components & Surveys
        source_specs = [
            ("FAC-A1", "SRC-A1-TURB", "Gas Turbine Train 1", "Combustion", "Natural Gas", "32 MW"),
            ("FAC-A1", "SRC-A1-FLR", "High-Pressure Flare Stack", "Flaring", "Associated Gas", "45 MMscfd"),
            ("FAC-B2", "SRC-B2-HTR", "Cryogenic Regeneration Heater", "Combustion", "Fuel Gas", "18 MW"),
            ("FAC-B2", "SRC-B2-VENT", "Condensate Stabilizer Vent", "Venting", "Associated Gas", "12 MMscfd"),
            ("FAC-C3", "SRC-C3-CMP", "Export Booster Compressor C-1", "Combustion", "Natural Gas", "24 MW"),
            ("FAC-C3", "SRC-C3-TNK", "Crude Storage Tank Manifold", "Fugitive", "Field Gas", "120k bbl"),
        ]
        sources_by_code: dict[str, EmissionSource] = {}
        for fac_code, scode, sname, stype, fuel, cap in source_specs:
            fac = facs_by_code[fac_code]
            src = EmissionSource.query.filter_by(code=scode).first()
            if not src:
                src = EmissionSource(
                    facility_id=fac.id,
                    code=scode,
                    name=sname,
                    type=stype,
                    equipment_id=scode,
                    fuel_type=fuel,
                    design_capacity=cap,
                    installation_date="2018-01-15",
                    status="Active",
                    activity=fac.activity,
                    division=fac.division,
                    region=fac.region,
                    field=fac.field,
                )
                db.session.add(src)
                db.session.flush()
            sources_by_code[scode] = src
        db.session.commit()

        if not CustomFactor.query.filter_by(name="Basin Alpha Sales Gas Blend", version="v2025.1").first():
            db.session.add(
                CustomFactor(
                    name="Basin Alpha Sales Gas Blend",
                    version="v2025.1",
                    co2_factor=2.18,
                    ch4_factor=0.00042,
                    n2o_factor=0.00004,
                    unit="m3",
                    hhv_factor=39.4,
                    usage="Stationary Combustion",
                    parent_fuel="Natural Gas",
                    source="Demo Laboratory Gas Chromatography ISO 6976",
                    uncertainty=0.035,
                    co2_uncertainty=0.03,
                    ch4_uncertainty=0.08,
                    n2o_uncertainty=0.12,
                    uncertainty_pct=3.5,
                    status="Approved",
                    facility_id=facs_by_code["FAC-A1"].id,
                    region="Basin Alpha",
                )
            )
            db.session.commit()

        for fac_code, comp_type, qty, leaking in [
            ("FAC-A1", "Valves (Gas Service)", 240, False),
            ("FAC-B2", "Flanges & Connectors", 410, True),
            ("FAC-C3", "Compressor Seals", 36, False),
        ]:
            fac = facs_by_code[fac_code]
            ci = ComponentInventory.query.filter_by(
                facility_id=fac.id, component_type=comp_type
            ).first()
            if not ci:
                ci = ComponentInventory(
                    facility_id=fac.id,
                    equipment_type="Process Skid",
                    component_type=comp_type,
                    service_type="Gas",
                    quantity=qty,
                    operating_hours=8760.0,
                    methodology="Component Average",
                    factor_value=0.0045,
                    factor_unit="kg/hr/component",
                    api_reference="API Compendium Table 6-1",
                    status="Active",
                )
                db.session.add(ci)
                db.session.flush()
                db.session.add(
                    FugitiveSurvey(
                        facility_id=fac.id,
                        component_inventory_id=ci.id,
                        survey_method="OGI",
                        survey_date="2025-06-15",
                        detection_threshold_ppm=500.0,
                        screening_value_ppm=1850.0 if leaking else 120.0,
                        leak_status="Leaking" if leaking else "Non-leaking",
                        measured_emission_rate=1.45 if leaking else 0.02,
                        measurement_unit="kg/hr",
                        leaking_hours=1200.0 if leaking else 0.0,
                        surveyor_name="Demo LDAR Team",
                    )
                )
        db.session.commit()

        # 7. Multi-Year Production Data (2022-2026)
        prod_rates = {
            "FAC-A1": (920000.0, 3400000.0),
            "FAC-B2": (360000.0, 6200000.0),
            "FAC-C3": (140000.0, 4800000.0),
        }
        for fac_code, fac in facs_by_code.items():
            oil_base, gas_base = prod_rates[fac_code]
            for yr in (2022, 2023, 2024, 2025, 2026):
                max_m = 6 if yr == 2026 else 12
                yoy = 1.0 - (yr - 2022) * 0.015
                for m in range(1, max_m + 1):
                    seasonal = 1.0 + ((m % 4) - 1.5) * 0.015
                    oil_val = round(oil_base * yoy * seasonal, 2)
                    gas_val = round(gas_base * yoy * seasonal, 2)
                    gross_gas_mmsm3 = round(gas_val * 0.0283168 / 1000.0, 4)
                    inj_gas_mmsm3 = round(gross_gas_mmsm3 * 0.30, 4)
                    crude_mmboe = round(oil_val / 1_000_000.0, 4)
                    total_mmboe = round(crude_mmboe + (gas_val / 6_000_000.0), 4)
                    saleable_mmboe = round(total_mmboe * 0.90, 4)

                    row = ProductionData.query.filter_by(
                        facility_id=fac.id, year=yr, month=m
                    ).first()
                    if not row:
                        row = ProductionData(
                            facility_id=fac.id,
                            year=yr,
                            month=m,
                            oil_amount=oil_val,
                            gas_amount=gas_val,
                            unit="bbl",
                            oil_unit="bbl",
                            gas_unit="mscf",
                            gross_gas_mmsm3=gross_gas_mmsm3,
                            injected_gas_mmsm3=inj_gas_mmsm3,
                            gas_without_injected_mmsm3=round(gross_gas_mmsm3 - inj_gas_mmsm3, 4),
                            crude_oil_mmboe=crude_mmboe,
                            total_production_mmboe=total_mmboe,
                            total_production_no_injected_mmboe=round(total_mmboe * 0.92, 4),
                            saleable_production_mmboe=saleable_mmboe,
                            activity=fac.activity,
                            division=fac.division,
                            region=fac.region,
                            field=fac.field,
                            created_by=admin_user.id if admin_user else None,
                        )
                        db.session.add(row)
                    else:
                        row.oil_amount = oil_val
                        row.gas_amount = gas_val
                        row.total_production_mmboe = total_mmboe
                        row.saleable_production_mmboe = saleable_mmboe
        db.session.commit()

        # 8. Scope 1 Emissions (2022-2026 quarterly/semi-annual deterministic records)
        scale_map = {"FAC-A1": (18000.0, 420.0), "FAC-B2": (14500.0, 310.0), "FAC-C3": (11000.0, 145.0)}
        for fac_code, fac in facs_by_code.items():
            base_co2, base_ch4 = scale_map[fac_code]
            for yr in (2022, 2023, 2024, 2025, 2026):
                trend = 1.0 - max(0, yr - 2023) * 0.035
                months = (3, 6) if yr == 2026 else (3, 6, 9, 12)
                for m in months:
                    specs = [
                        ("Combustion", "Natural Gas", base_co2 * 0.65 / len(months), base_ch4 * 0.12 / len(months), 0.0005, 4, "ef_facility_specific"),
                        ("Flaring", "Associated Gas", base_co2 * 0.24 / len(months), base_ch4 * 0.30 / len(months), 0.0002, 4, "direct_measurement"),
                        ("Venting", "Associated Gas", base_co2 * 0.07 / len(months), base_ch4 * 0.40 / len(months), 0.0, 4, "ef_facility_specific"),
                        ("Fugitive", "Field Gas", base_co2 * 0.04 / len(months), base_ch4 * 0.18 / len(months), 0.0, 4, "engineering_estimate"),
                    ]
                    for ptype, ftype, c2, c4, n2o_ratio, ogmp_lvl, method in specs:
                        rec_id = f"DEMO-S1-{fac_code}-{yr}-M{m:02d}-{ptype[:4].upper()}"
                        if Emission.query.filter_by(record_id=rec_id).first():
                            continue
                        co2 = round(c2 * trend, 2)
                        ch4 = round(c4 * trend, 2)
                        n2o = round(co2 * n2o_ratio, 3)
                        co2e = round(co2 + ch4 * 28.0 + n2o * 265.0, 2)
                        status = "Pending" if (yr == 2026 and m == 6 and ptype == "Fugitive" and fac_code == "FAC-A1") else "Verified"
                        db.session.add(
                            Emission(
                                record_id=rec_id,
                                facility_id=fac.id,
                                year=yr,
                                month=m,
                                company_name="Demo Operator Co.",
                                group_name=fac.region,
                                process_type=ptype,
                                fuel_type=ftype,
                                quantity=round(max(co2 * 0.48, ch4 * 1.4), 2),
                                unit="tonnes",
                                factor_source="API Compendium 2021",
                                ef_used_co2=2.18 if ptype == "Combustion" else 1.85,
                                ef_used_ch4=0.0042,
                                ef_used_n2o=0.0004,
                                co2_emissions=co2,
                                ch4_emissions=ch4,
                                n2o_emissions=n2o,
                                co2e_total=co2e,
                                uncertainty=0.05,
                                uncertainty_ch4=0.18,
                                uncertainty_n2o=0.20,
                                uncertainty_pct=6.5 if ptype == "Combustion" else 14.0,
                                uncertainty_ad=0.02,
                                uncertainty_ef_co2=0.04,
                                uncertainty_ef_ch4=0.15,
                                ef_key=f"DEMO-{ptype.upper()}",
                                status=status,
                                activity=fac.activity,
                                division=fac.division,
                                region=fac.region,
                                field=fac.field,
                                ogmp_level=ogmp_lvl,
                                calc_method=method,
                                gwp_version="AR5",
                                created_by=admin_user.id if admin_user else None,
                                approved_by=admin_user.id if (admin_user and status == "Verified") else None,
                                approved_at=datetime.datetime.now(datetime.UTC) if status == "Verified" else None,
                            )
                        )
        db.session.commit()

        # 9. Scope 2 & Scope 3 Emissions
        for fac_code, fac in facs_by_code.items():
            for yr in (2022, 2023, 2024, 2025, 2026):
                if not Scope2Emission.query.filter_by(facility_id=fac.id, year=yr, source_type="electricity").first():
                    kwh = 6_200_000.0 if fac_code == "FAC-C3" else 3_800_000.0
                    ef = 0.542
                    loc_co2e = round(kwh * ef / 1000.0, 2)
                    mkt_co2e = round(loc_co2e * 0.85, 2)
                    db.session.add(
                        Scope2Emission(
                            facility_id=fac.id,
                            year=yr,
                            month=6,
                            source_type="electricity",
                            electricity_kwh=kwh,
                            emission_factor=ef,
                            co2e=loc_co2e,
                            co2e_location_based=loc_co2e,
                            co2e_market_based=mkt_co2e,
                            market_instrument_type="PPA",
                            market_emission_factor=round(ef * 0.85, 4),
                            uncertainty=0.04,
                            uncertainty_pct=4.0,
                            location=fac.location,
                            grid_region="National Grid",
                            activity=fac.activity,
                            division=fac.division,
                            region=fac.region,
                            field=fac.field,
                            status="Verified",
                            created_by=admin_user.id if admin_user else None,
                        )
                    )
                if not Scope3Emission.query.filter_by(facility_id=fac.id, year=yr, category="Category 1: Purchased Goods and Services").first():
                    act = 6400.0
                    ef_s3 = 1280.0
                    s3_val = round(act * ef_s3 / 1000.0, 2)
                    db.session.add(
                        Scope3Emission(
                            facility_id=fac.id,
                            year=yr,
                            month=6,
                            category="Category 1: Purchased Goods and Services",
                            sub_category="Industrial Chemicals & Catalysts",
                            activity_data=act,
                            unit="tonnes",
                            emission_factor=ef_s3,
                            factor_unit="kg CO2e/tonne",
                            co2e=s3_val,
                            uncertainty=0.25,
                            uncertainty_pct=25.0,
                            calculation_method="spend_based_screening",
                            data_quality="Secondary EEIO Screening",
                            region=fac.region,
                            status="Verified",
                            created_by=admin_user.id if admin_user else None,
                        )
                    )
        for yr in (2023, 2024, 2025):
            if not Scope3Data.query.filter_by(year=yr, category="Category 11").first():
                vol = 420000.0
                ef = 0.415
                db.session.add(
                    Scope3Data(
                        year=yr,
                        category="Category 11",
                        method="Average-data Screening",
                        product_type="Natural Gas",
                        volume=vol,
                        unit="boe",
                        emission_factor=ef,
                        emissions_tco2e=round(vol * ef, 2),
                        notes="Spend-based and product throughput screening estimate.",
                    )
                )
        db.session.commit()

        # 10. Flaring Details (2022-2026)
        flaring_map = {
            "FAC-A1": (165.0, 38.0, 14.0, 99.86),
            "FAC-B2": (98.0, 24.0, 11.0, 99.91),
            "FAC-C3": (48.0, 16.0, 9.0, 99.94),
        }
        for fac_code, (r_base, nr_base, s_base, dre) in flaring_map.items():
            fac = facs_by_code[fac_code]
            for yr in (2022, 2023, 2024, 2025, 2026):
                if not FlaringDetail.query.filter_by(facility_id=fac.id, year=yr).first():
                    factor = 1.0 - max(0, yr - 2022) * 0.04
                    r = round(r_base * factor, 2)
                    nr = round(nr_base * factor, 2)
                    s = round(s_base, 2)
                    db.session.add(
                        FlaringDetail(
                            facility_id=fac.id,
                            year=yr,
                            month=6,
                            network="CPF",
                            routine_knm3=r,
                            non_routine_knm3=nr,
                            safety_knm3=s,
                            total_knm3=round(r + nr + s, 2),
                            measured_dre_pct=dre,
                            dre_method="VISR Infrared Optical Camera",
                            status="Verified",
                        )
                    )
        db.session.commit()

        # 11. OGMP 2.0 Empirical Surveys
        ogmp_specs = [
            ("FAC-A1", 2024, "2024-06-14", "Satellite (Sentinel-5P/TROPOMI)", 49.2, 431.0, 442.0, -2.49, False, "Reconciled"),
            ("FAC-A1", 2025, "2025-05-18", "Aerial LiDAR (Bridger Photonics)", 46.8, 410.0, 415.0, -1.20, False, "Reconciled"),
            ("FAC-B2", 2025, "2025-07-10", "Drone OGI (FLIR GF320)", 34.4, 301.3, 298.0, 1.11, False, "Reconciled"),
            ("FAC-C3", 2025, "2025-08-22", "Continuous Monitor", 16.2, 141.9, 138.0, 2.83, False, "Reconciled"),
        ]
        for fac_code, yr, sdate, stype, rate, est_t, bu_t, var_pct, vflag, rec_status in ogmp_specs:
            fac = facs_by_code[fac_code]
            if not OgmpSurvey.query.filter_by(facility_id=fac.id, year=yr, survey_date=sdate).first():
                db.session.add(
                    OgmpSurvey(
                        facility_id=fac.id,
                        year=yr,
                        survey_date=sdate,
                        survey_type=stype,
                        measured_rate_kg_hr=rate,
                        operating_hours_year=8760.0,
                        estimated_annual_tch4=est_t,
                        detection_threshold=3.0 if "LiDAR" in stype else 15.0,
                        instrument_vendor="Demo Sensor Suite",
                        bottom_up_tch4=bu_t,
                        variance_pct=var_pct,
                        variance_flag=vflag,
                        reconciliation_status=rec_status,
                        status="reviewed",
                    )
                )
        db.session.commit()

        # 12. EU CBAM Product Exports
        cbam_specs = [
            ("FAC-C3", 2024, 6, "Anhydrous Ammonia (Synthetic Grade)", "2814 10 00", 42000.0, "EU - France", 1.76, 0.14),
            ("FAC-C3", 2025, 4, "Clean Hydrogen (Demo ATR)", "2804 10 00", 9800.0, "EU - Germany", 3.95, 0.31),
            ("FAC-B2", 2025, 9, "Stabilized Condensate / Fuel", "2710 19 43", 64000.0, "EU - Italy", 0.28, 0.05),
        ]
        for fac_code, yr, m, pname, cn, qty, dest, sdir, sindir in cbam_specs:
            fac = facs_by_code[fac_code]
            if not CbamProductExport.query.filter_by(facility_id=fac.id, year=yr, product_name=pname).first():
                db.session.add(
                    CbamProductExport(
                        facility_id=fac.id,
                        year=yr,
                        month=m,
                        product_name=pname,
                        cn_code=cn,
                        quantity_tonnes=qty,
                        export_destination=dest,
                        quarter=f"Q{((m - 1) // 3) + 1}",
                        specific_embedded_direct=sdir,
                        specific_embedded_indirect=sindir,
                        notes="Synthetic demo CBAM export record (XML preview format).",
                        created_by=admin_user.id if admin_user else None,
                    )
                )
        db.session.commit()

        # 13. Goals, Base Year, Recalculation History, Reporting Metadata, SBTi, Mitigation
        for yr, target in [(2025, 195000.0), (2026, 182000.0), (2030, 130000.0)]:
            if not Goal.query.filter_by(year=yr).first():
                db.session.add(Goal(year=yr, target_amount=target))
        if not BaseYear.query.filter_by(id=1).first():
            db.session.add(BaseYear(id=1, year=2023, locked=1))
        if not BaseYearRecalculation.query.first():
            db.session.add(
                BaseYearRecalculation(
                    year=2023,
                    reason="Initial synthetic demo base year establishment and boundary verification (ISO 14064-1 Clause 6.4.1).",
                    previous_emissions=212400.0,
                    adjusted_emissions=210850.0,
                    created_by=admin_user.id if admin_user else None,
                )
            )
        for yr in (2023, 2024, 2025):
            if not ReportingMetadata.query.filter_by(year=yr).first():
                db.session.add(
                    ReportingMetadata(
                        year=yr,
                        has_reduction_target=1,
                        target_description="25% Scope 1 & 2 intensity reduction by 2030 vs. 2023 baseline.",
                        is_tcfd_aligned=1,
                        assurance_level="Limited Assurance",
                        assurance_provider="Independent Verification Demo Body",
                    )
                )
        if not SbtiTarget.query.first():
            db.session.add(
                SbtiTarget(
                    base_year=2023,
                    base_year_emissions=210850.0,
                    target_year=2050,
                    reduction_rate_pct=4.2,
                    pathway_type="1.5C",
                    scope_coverage="S1S2S3",
                    created_by=admin_user.id if admin_user else None,
                )
            )
        mit_specs = [
            ("FAC-A1", "Flare Gas Recovery Unit Phase 1", "efficiency", 2024, 18500.0, "completed", "Captured routine low-pressure flare gas."),
            ("FAC-B2", "LDAR Continuous Optical Monitoring", "methane_abatement", 2025, 9200.0, "active", "Continuous methane leak mitigation campaign."),
            ("FAC-C3", "Export Pump Solar Hybridization", "renewable", 2025, 7400.0, "active", "Grid-tied solar PV displacement."),
        ]
        for fac_code, mname, mtype, yr, qty, st, desc in mit_specs:
            fac = facs_by_code[fac_code]
            if not MitigationProject.query.filter_by(facility_id=fac.id, name=mname, year=yr).first():
                db.session.add(
                    MitigationProject(
                        facility_id=fac.id,
                        name=mname,
                        project_type=mtype,
                        year=yr,
                        quantity_tco2e=qty,
                        status=st,
                        description=desc,
                        created_by=admin_user.id if admin_user else None,
                    )
                )
        if not MitigationRecord.query.first():
            db.session.add(
                MitigationRecord(
                    year=2025,
                    type="Flaring Reduction",
                    subtype="Flare Gas Recovery",
                    quantity_tco2e=18500.0,
                    notes="Verified flare recovery reduction at Facility A-1.",
                    reference_id="MIT-DEMO-01",
                )
            )
        if not LevelUpgradeLog.query.first():
            db.session.add(
                LevelUpgradeLog(
                    facility_id=facs_by_code["FAC-A1"].id,
                    source_type_code="FUG-VALVES",
                    old_level=3,
                    new_level=4,
                    target_date="2025-12-31",
                    justification="Transition from generic component factors to OGI survey measurements.",
                    created_by=admin_user.id if admin_user else None,
                )
            )
        db.session.commit()

        # 14. Clean System Settings (NO CDSE / Copernicus secrets)
        default_settings = {
            "gwp_standard": "AR5",
            "ogmp_default_base_year": 2023,
            "reconciliation_threshold": 15.0,
            "ogmp_upstream_target_pct": 0.20,
            "ogmp_midstream_target_pct": 0.05,
            "session_timeout_minutes": 15,
            "auto_flag_discrepancy": True,
        }
        for k, v in default_settings.items():
            row = db.session.get(SystemSetting, k)
            if not row:
                db.session.add(SystemSetting(key=k, value=json.dumps(v)))
        db.session.commit()

        # Seal at least one audit log entry cleanly
        if ActivityLog.query.count() == 0:
            from utils import log_activity_and_notify
            log_activity_and_notify(
                action="DEMO_SEED",
                record_id="demo_template",
                details="Initialized clean synthetic demo dataset (Demo Operator Co.)",
                user=admin_user or "System",
                entity="System",
            )
            db.session.commit()

        clear_dashboard_cache()

    if print_credentials and generated_creds:
        print("\n=== DEMO USER CREDENTIALS (generated at seed time — save now) ===")
        for email, pw in generated_creds.items():
            role = next((u["role"] for u in DEMO_USERS if u["email"] == email), "user")
            print(f"  {email} ({role}): {pw}")
        print("=================================================================\n")

    return generated_creds


def seed_demo(
    db_path: Path | None = None,
    *,
    recreate: bool = False,
    reset_passwords: bool = False,
    template_path: Path | None = None,
    print_credentials: bool = True,
) -> tuple[Path, dict[str, str]]:
    """Builds or idempotently updates the SQLite demo database."""
    target_db = Path(db_path or (SERVER_DIR / "ghg_app.db")).resolve()
    target_db.parent.mkdir(parents=True, exist_ok=True)

    if recreate:
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(target_db) + suffix)
            if p.exists():
                p.unlink()

    os.environ["DATABASE_URL"] = f"sqlite:///{target_db.as_posix()}"
    os.environ.setdefault("FLASK_ENV", "development")
    os.environ["SEED_ADMIN"] = "false"
    os.environ["AUTO_MIGRATE"] = "true"

    from app import app
    from extensions import db

    creds = seed_demo_in_app(
        app,
        reset_passwords=reset_passwords,
        print_credentials=print_credentials,
    )

    with app.app_context():
        db.session.remove()
        db.engine.dispose()

    _vacuum_sqlite_file(target_db)

    if template_path:
        tpl = Path(template_path).resolve()
        tpl.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target_db, tpl)
        _vacuum_sqlite_file(tpl)

    return target_db, creds


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Seed clean synthetic demo database.")
    parser.add_argument("--db", default=str(SERVER_DIR / "ghg_app.db"), help="Target SQLite database path.")
    parser.add_argument("--template", default=None, help="Optional pristine template DB output path.")
    parser.add_argument("--recreate", action="store_true", help="Remove existing DB file and create from scratch.")
    parser.add_argument("--reset-passwords", action="store_true", help="Regenerate passwords for existing demo users.")
    args = parser.parse_args(argv)

    db_file, _ = seed_demo(
        db_path=Path(args.db),
        recreate=args.recreate,
        reset_passwords=args.reset_passwords,
        template_path=Path(args.template) if args.template else None,
    )
    print(f"[OK] Synthetic demo database ready: {db_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
