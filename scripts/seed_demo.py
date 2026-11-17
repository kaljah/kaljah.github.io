#!/usr/bin/env python3
"""
Synthetic Demo Dataset Builder (Idempotent, Clean From Scratch)
===============================================================
Builds a complete, client-free synthetic GHG dataset for live GIZ demos
and hands-on GIZ staff sandbox sessions.

Usage:
    python scripts/seed_demo.py [--db new/server/ghg_app.db] [--recreate] [--reset-passwords] [--template new/server/instance/demo_template.db]
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import secrets
import shutil
import sqlite3
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

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
        "description": "Central processing facility operating oil stabilization trains, turbine gas compression, and associated gas reinjection.",
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
        "description": "Wet gas processing hub operating cryogenic NGL recovery, stabilizer trains, and booster compression.",
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
        "description": "Coastal midstream hydrocarbon stabilization terminal with cryogenic liquefaction and marine export berths.",
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


def _ensure_demo_user_facility_access(
    db,
    UserFacilityAccessModel,
    user,
    facs_by_code: dict,
) -> None:
    """Grants role-appropriate Facility access links to non-admin demo users."""
    if user.role not in ("user", "auditor"):
        return
    access_lvl = "verifier" if user.role == "auditor" else "operator"
    for fac in facs_by_code.values():
        ufa = UserFacilityAccessModel.query.filter_by(user_id=user.id, facility_id=fac.id).first()
        if not ufa:
            db.session.add(
                UserFacilityAccessModel(
                    user_id=user.id,
                    facility_id=fac.id,
                    access_level=access_lvl,
                )
            )


def _upsert_demo_production_row(
    db,
    ProductionDataModel,
    *,
    fac,
    yr: int,
    m: int,
    oil_base: float,
    gas_base: float,
    admin_user,
) -> None:
    """Creates or refreshes a monthly demo ProductionData row."""
    yoy = 1.0 - (yr - 2022) * 0.015
    seasonal = 1.0 + ((m % 4) - 1.5) * 0.015
    oil_val = round(oil_base * yoy * seasonal, 2)
    gas_val = round(gas_base * yoy * seasonal, 2)
    gross_gas_mmsm3 = round(gas_val * 0.0283168 / 1000.0, 4)
    inj_gas_mmsm3 = round(gross_gas_mmsm3 * 0.30, 4)
    crude_mmboe = round(oil_val / 1_000_000.0, 4)
    total_mmboe = round(crude_mmboe + (gas_val / 6_000_000.0), 4)
    saleable_mmboe = round(total_mmboe * 0.90, 4)

    row = ProductionDataModel.query.filter_by(
        facility_id=fac.id, year=yr, month=m
    ).first()
    if row:
        row.oil_amount = oil_val
        row.gas_amount = gas_val
        row.total_production_mmboe = total_mmboe
        row.saleable_production_mmboe = saleable_mmboe
        return

    db.session.add(
        ProductionDataModel(
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
    )


def _upsert_demo_scope1_emission(
    db,
    EmissionModel,
    *,
    fac,
    fac_code: str,
    yr: int,
    m: int,
    spec: tuple,
    admin_user,
    auditor_user,
) -> None:
    """Creates or refreshes one deterministic monthly/quarterly Scope 1 demo emission row."""
    ptype, ftype, qty_m3, ef_c2, ef_c4, ef_n2, fsrc, cf_id, ogmp_lvl, method = spec
    rec_id = f"DEMO-S1-{fac_code}-{yr}-M{m:02d}-{ptype[:4].upper()}"
    co2 = round(qty_m3 * ef_c2 / 1000.0, 2)
    ch4 = round(qty_m3 * ef_c4 / 1000.0, 4)
    n2o = round(qty_m3 * ef_n2 / 1000.0, 4)
    co2e = round(co2 + ch4 * 28.0 + n2o * 265.0, 2)
    status = "Pending" if (yr == 2026 and m == 6 and ptype == "Fugitive" and fac_code == "FAC-A1") else "Verified"
    existing_em = EmissionModel.query.filter_by(record_id=rec_id).first()
    if existing_em:
        existing_em.quantity = qty_m3
        existing_em.unit = "m3"
        existing_em.factor_source = fsrc
        existing_em.custom_factor_id = cf_id
        existing_em.ef_used_co2 = ef_c2
        existing_em.ef_used_ch4 = ef_c4
        existing_em.ef_used_n2o = ef_n2
        existing_em.co2_emissions = co2
        existing_em.ch4_emissions = ch4
        existing_em.n2o_emissions = n2o
        existing_em.co2e_total = co2e
        existing_em.status = status
        return
    db.session.add(
        EmissionModel(
            record_id=rec_id,
            facility_id=fac.id,
            year=yr,
            month=m,
            company_name="Demo Operator Co.",
            group_name=fac.region,
            process_type=ptype,
            fuel_type=ftype,
            quantity=qty_m3,
            unit="m3",
            factor_source=fsrc,
            custom_factor_id=cf_id,
            ef_used_co2=ef_c2,
            ef_used_ch4=ef_c4,
            ef_used_n2o=ef_n2,
            co2_emissions=co2,
            ch4_emissions=ch4,
            n2o_emissions=n2o,
            co2e_total=co2e,
            uncertainty=0.035 if ptype == "Combustion" else (0.05 if ptype == "Flaring" else 0.12),
            uncertainty_ch4=0.08 if ptype == "Combustion" else 0.15,
            uncertainty_n2o=0.12 if ef_n2 > 0 else None,
            uncertainty_pct=4.5 if ptype == "Combustion" else (7.0 if ptype == "Flaring" else 16.0),
            uncertainty_ad=0.02,
            uncertainty_ef_co2=0.03,
            uncertainty_ef_ch4=0.14,
            ef_key=f"custom:{cf_id}" if cf_id else f"DEMO-{ptype.upper()}",
            status=status,
            activity=fac.activity,
            division=fac.division,
            region=fac.region,
            field=fac.field,
            ogmp_level=ogmp_lvl,
            calc_method=method,
            gwp_version="AR5",
            created_by=admin_user.id if admin_user else None,
            approved_by=(auditor_user or admin_user).id if ((auditor_user or admin_user) and status == "Verified") else None,
            approved_at=datetime.datetime.now(datetime.UTC) if status == "Verified" else None,
        )
    )


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
        OgmpAnnualReport,
        OgmpAsset,
        OgmpAssetReport,
        OgmpAuditTrail,
        OgmpEmissionSource,
        OgmpImplementationPlan,
        OgmpReportingEntity,
        OgmpSiteMeasurement,
        OgmpSurvey,
        OgmpTarget,
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
    from services.dashboard_filters import production_gas_m3
    from services.ogmp_reconciliation import build_default_implementation_plan, reconcile_l4_l5

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
        auditor_user: User | None = None
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
            elif u_spec["role"] == "auditor":
                auditor_user = user

            # Ensure UserFacilityAccess for operator & auditor across all demo facilities
            _ensure_demo_user_facility_access(db, UserFacilityAccess, user, facs_by_code)
        db.session.commit()

        # 5. Factor Provenance Registry & Methane Source Types
        try:
            from scripts.verified_factors_seed_data import ALL_VERIFIED_FACTORS

            for fdata in ALL_VERIFIED_FACTORS:
                existing = db.session.get(FactorProvenanceRegistry, fdata["id"])
                if not existing:
                    db.session.add(FactorProvenanceRegistry(**fdata))
                    continue
                for k, v in fdata.items():
                    setattr(existing, k, v)
            db.session.commit()
        except Exception as exc:
            logger.warning("Failed seeding FactorProvenanceRegistry rows: %s", exc, exc_info=True)
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

        sales_gas_comp = {
            "ch4_mol_pct": 86.40,
            "c2h6_mol_pct": 7.20,
            "c3h8_mol_pct": 2.40,
            "ic4_mol_pct": 0.45,
            "nc4_mol_pct": 0.65,
            "ic5_mol_pct": 0.18,
            "nc5_mol_pct": 0.14,
            "c6_plus_mol_pct": 0.18,
            "co2_mol_pct": 1.40,
            "n2_mol_pct": 1.00,
            "h2s_ppm": 12.0,
            "hhv_btu_scf": 1076.0,
            "mw_kg_mole": 18.42,
            "carbon_content": 0.742,
        }
        cf_basin_alpha = CustomFactor.query.filter_by(
            name="Basin Alpha Sales Gas Blend", version="v2025.1"
        ).first()
        if not cf_basin_alpha:
            cf_basin_alpha = CustomFactor(
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
                gas_composition=sales_gas_comp,
            )
            db.session.add(cf_basin_alpha)
            db.session.commit()
        elif not cf_basin_alpha.gas_composition:
            cf_basin_alpha.gas_composition = sales_gas_comp
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
                for m in range(1, max_m + 1):
                    _upsert_demo_production_row(
                        db,
                        ProductionData,
                        fac=fac,
                        yr=yr,
                        m=m,
                        oil_base=oil_base,
                        gas_base=gas_base,
                        admin_user=admin_user,
                    )
        db.session.commit()

        # 8. Reconciled Flaring Volume Blueprint & Stoichiometric Scope 1 Emissions (2022-2026)
        # Annual volumes (m3/yr for Combustion/Venting/Fugitive; kNm3/yr for Flaring) enforce exact
        # conservation of mass: quantity * ef_used / 1000 == gas_emissions, and FlaringDetail == Flaring Emission.
        flaring_map = {
            "FAC-A1": (1600.0, 370.0, 140.0, 98.60),  # 2,110 kNm3/yr (~2.11 MMSm3/yr -> ~4,325 tCO2/yr)
            "FAC-B2": (1250.0, 320.0, 120.0, 98.80),  # 1,690 kNm3/yr (~1.69 MMSm3/yr -> ~3,465 tCO2/yr)
            "FAC-C3": (920.0, 260.0, 100.0, 99.10),   # 1,280 kNm3/yr (~1.28 MMSm3/yr -> ~2,624 tCO2/yr)
        }
        comb_m3_map = {"FAC-A1": 5_367_000.0, "FAC-B2": 4_323_000.0, "FAC-C3": 3_280_000.0}
        vent_m3_map = {"FAC-A1": 420_000.0, "FAC-B2": 320_000.0, "FAC-C3": 140_000.0}
        fug_m3_map = {"FAC-A1": 240_000.0, "FAC-B2": 180_000.0, "FAC-C3": 95_000.0}

        for fac_code, fac in facs_by_code.items():
            r_b, nr_b, s_b, dre = flaring_map[fac_code]
            flr_yr_m3 = (r_b + nr_b + s_b) * 1000.0
            flr_ef_ch4 = round(0.56 * (1.0 - dre / 100.0), 6)
            for yr in (2022, 2023, 2024, 2025, 2026):
                trend = 1.0 - max(0, yr - 2023) * 0.035
                months = (3, 6) if yr == 2026 else (3, 6, 9, 12)
                for m in months:
                    specs = [
                        (
                            "Combustion",
                            "Natural Gas",
                            round(comb_m3_map[fac_code] * trend / 4.0, 2),
                            2.18,
                            0.00042,
                            0.00004,
                            "custom",
                            cf_basin_alpha.id if (fac_code == "FAC-A1" and cf_basin_alpha) else None,
                            4,
                            "ef_facility_specific",
                        ),
                        (
                            "Flaring",
                            "Associated Gas",
                            round(flr_yr_m3 * trend / 4.0, 2),
                            2.05,
                            flr_ef_ch4,
                            0.00004,
                            "specific",
                            None,
                            4,
                            "direct_measurement",
                        ),
                        (
                            "Venting",
                            "Associated Gas",
                            round(vent_m3_map[fac_code] * trend / 4.0, 2),
                            0.03,
                            0.55,
                            0.0,
                            "default",
                            None,
                            4,
                            "ef_facility_specific",
                        ),
                        (
                            "Fugitive",
                            "Field Gas",
                            round(fug_m3_map[fac_code] * trend / 4.0, 2),
                            0.025,
                            0.58,
                            0.0,
                            "default",
                            None,
                            4,
                            "engineering_estimate",
                        ),
                    ]
                    for spec in specs:
                        _upsert_demo_scope1_emission(
                            db,
                            Emission,
                            fac=fac,
                            fac_code=fac_code,
                            yr=yr,
                            m=m,
                            spec=spec,
                            admin_user=admin_user,
                            auditor_user=auditor_user,
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

        # 10. Flaring Details (2022-2026) — exact volume parity with Flaring Emission records
        for fac_code, (r_base, nr_base, s_base, dre) in flaring_map.items():
            fac = facs_by_code[fac_code]
            for yr in (2022, 2023, 2024, 2025, 2026):
                trend = 1.0 - max(0, yr - 2023) * 0.035
                period_frac = 0.5 if yr == 2026 else 1.0
                r = round(r_base * trend * period_frac, 2)
                nr = round(nr_base * trend * period_frac, 2)
                s = round(s_base * trend * period_frac, 2)
                tot_knm3 = round(r + nr + s, 2)
                existing_fd = FlaringDetail.query.filter_by(facility_id=fac.id, year=yr).first()
                if existing_fd:
                    existing_fd.routine_knm3 = r
                    existing_fd.non_routine_knm3 = nr
                    existing_fd.safety_knm3 = s
                    existing_fd.total_knm3 = tot_knm3
                    existing_fd.measured_dre_pct = dre
                else:
                    db.session.add(
                        FlaringDetail(
                            facility_id=fac.id,
                            year=yr,
                            month=6,
                            network="CPF",
                            routine_knm3=r,
                            non_routine_knm3=nr,
                            safety_knm3=s,
                            total_knm3=tot_knm3,
                            measured_dre_pct=dre,
                            dre_method="VISR Infrared Optical Camera",
                            status="Verified",
                        )
                    )
        db.session.commit()

        # 11. OGMP 2.0 Empirical Surveys (2024-2025 only; 2023 intentionally has none)
        ogmp_specs = [
            ("FAC-A1", 2024, "2024-06-14", "Satellite (Sentinel-5P/TROPOMI)", 42.1, 368.8, 375.4, -1.76, False, "Reconciled"),
            ("FAC-A1", 2025, "2025-05-18", "Aerial LiDAR (Bridger Photonics)", 40.9, 358.3, 361.8, -0.97, False, "Reconciled"),
            ("FAC-B2", 2025, "2025-07-10", "Drone OGI (FLIR GF320)", 31.6, 276.8, 273.0, 1.39, False, "Reconciled"),
            ("FAC-C3", 2025, "2025-08-22", "Continuous Monitor", 15.2, 133.2, 130.1, 2.38, False, "Reconciled"),
        ]
        for fac_code, yr, sdate, stype, rate, est_t, bu_t, var_pct, vflag, rec_status in ogmp_specs:
            fac = facs_by_code[fac_code]
            existing_ogmp = OgmpSurvey.query.filter_by(facility_id=fac.id, year=yr, survey_date=sdate).first()
            if existing_ogmp:
                existing_ogmp.measured_rate_kg_hr = rate
                existing_ogmp.estimated_annual_tch4 = est_t
                existing_ogmp.bottom_up_tch4 = bu_t
                existing_ogmp.variance_pct = var_pct
            else:
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

        # 11B. OGMP 2.0 Level 4 / Level 5 Workspace Seed (Entities, Sources, Campaigns, Reports, Plans)
        entity_blueprints = [
            ("FAC-A1", "Demo Operator - Basin Alpha CPF", "Basin Alpha Train", "Upstream", "Oil & Gas Production", "operated", "Demo Operator Co.", 60.0, True, 2023, 2026, False, "", False),
            ("FAC-B2", "Demo Operator - Basin Beta Gas Hub", "Basin Beta Processing", "Upstream", "Natural Gas Processing", "operated", "Demo Operator Co.", 70.0, True, 2023, 2026, False, "", False),
            ("FAC-C3", "Demo Operator - Coastal Terminal", "Coastal LNG Terminal", "Midstream", "LNG Liquefaction & Export", "operated", "Demo Operator Co.", 100.0, True, 2023, 2026, False, "", False),
            ("FAC-C3", "Demo JV Satellite Gathering (Minor NOJV)", "Satellite Gathering Tie-In", "Midstream", "Pipeline Gathering", "non_operated", "Demo JV Partner B", 3.5, False, 2024, 2029, True, "Minority non-operated JV stake (<5% equity CH4 materiality rule).", True),
        ]
        ent_by_name: dict[str, OgmpReportingEntity] = {}
        for fcode, ename, aname, seg, sseg, op_st, op_co, wi, ctrl, myr, tyr, excl, excl_r, mem_nojv in entity_blueprints:
            fac = facs_by_code[fcode]
            ent = OgmpReportingEntity.query.filter_by(entity_name=ename).first()
            if not ent:
                ent = OgmpReportingEntity(
                    facility_id=fac.id,
                    entity_name=ename,
                    asset_name=aname,
                    segment=seg,
                    sub_segment=sseg,
                    country=fac.country,
                    operator_status=op_st,
                    operating_company=op_co,
                    working_interest_pct=wi,
                    has_operational_control=ctrl,
                    membership_year=myr,
                    target_gold_year=tyr,
                    is_nojv_material_excluded=excl,
                    exclusion_reason=excl_r,
                    is_member_reported_nojv=mem_nojv,
                    tenant_id="default",
                    created_by=admin_user.id if admin_user else None,
                )
                db.session.add(ent)
                db.session.flush()
            ent_by_name[ename] = ent
            if not OgmpAsset.query.filter_by(reporting_entity_id=ent.id, asset_name=aname).first():
                db.session.add(
                    OgmpAsset(
                        reporting_entity_id=ent.id,
                        facility_id=fac.id,
                        asset_code=f"{fcode}-ASSET-{ent.id}",
                        asset_name=aname,
                        asset_type=sseg,
                        segment=seg,
                        operator_status=op_st,
                        equity_share_pct=wi,
                        is_nojv=(op_st != "operated"),
                        is_excluded_below_5pct=excl,
                        tenant_id="default",
                    )
                )
        primary_ent = ent_by_name["Demo Operator - Basin Alpha CPF"]
        if not OgmpTarget.query.filter_by(reporting_entity_id=primary_ent.id, target_year=2025).first():
            db.session.add(
                OgmpTarget(
                    reporting_entity_id=primary_ent.id,
                    target_year=2025,
                    metric_type="methane_intensity",
                    upstream_target_pct=0.20,
                    midstream_target_pct=0.05,
                    reduction_target_pct=45.0,
                    base_year=2023,
                    notes="UNEP OGMP 2.0 2025 near-zero methane intensity & Gold Standard Pathway 1 target.",
                    tenant_id="default",
                    created_by=admin_user.id if admin_user else None,
                )
            )
        db.session.commit()

        # Source disclosures across 2024 and 2025 (Quantified, MI, N/A, zero-emission & >10% YoY notes)
        l4_source_specs = [
            # FAC-A1 (2024 baseline + 2025 showing YoY note & L4 >=90%)
            ("FAC-A1", 2024, "Upstream", "UP-02", "Flaring (Routine, Non-Routine & Safety Flares)", "Flaring", 4, "Quantified", 142.0, 12.0, "VISR Flare Spectrometry + Flowmeter", "1", None, "", ""),
            ("FAC-A1", 2024, "Upstream", "UP-11", "Equipment Leaks & Component Fugitives (Valves/Flanges)", "Fugitive", 4, "Quantified", 128.0, 14.0, "OGI + Hi-Flow EN 15446", "1", None, "", ""),
            ("FAC-A1", 2024, "Upstream", "UP-03", "Hydrocarbon Storage Tanks (Flashing, Working & Breathing)", "Vented", 4, "Quantified", 75.0, 15.0, "VRU Direct Flowmeter", "1", None, "", ""),
            ("FAC-A1", 2024, "Upstream", "UP-04", "Pneumatic Devices & Controllers (Bleed & Intermittent)", "Vented", 3, "Quantified", 24.0, 22.0, "API Table 5-16 Pilot Count", "1", None, "", ""),
            ("FAC-A1", 2025, "Upstream", "UP-02", "Flaring (Routine, Non-Routine & Safety Flares)", "Flaring", 4, "Quantified", 122.0, 11.5, "VISR Flare Spectrometry + Flowmeter", "1", -14.08, "Flare Gas Recovery Unit Phase 1 commissioning reduced routine flare slip by 14% YoY.", ""),
            ("FAC-A1", 2025, "Upstream", "UP-11", "Equipment Leaks & Component Fugitives (Valves/Flanges)", "Fugitive", 4, "Quantified", 131.5, 13.0, "OGI + Hi-Flow EN 15446", "1", 2.73, "", ""),
            ("FAC-A1", 2025, "Upstream", "UP-03", "Hydrocarbon Storage Tanks (Flashing, Working & Breathing)", "Vented", 4, "Quantified", 82.0, 14.0, "VRU Direct Flowmeter", "1", 9.33, "", ""),
            ("FAC-A1", 2025, "Upstream", "UP-05", "Compressor Seals (Centrifugal Wet/Dry & Reciprocating Rod)", "Fugitive", 3, "Quantified", 22.0, 20.0, "API Table 5-19 Seal Count", "1", None, "", ""),
            ("FAC-A1", 2025, "Upstream", "UP-04", "Pneumatic Devices & Controllers (Bleed & Intermittent)", "Vented", 4, "Quantified", 0.0, 5.0, "Instrument Air Retrofit Audit", "1", -100.0, "Converted all high-bleed controllers to compressed instrument air in Q1 2025.", "Zero methane bleed verified post instrument-air header retrofit."),
            ("FAC-A1", 2025, "Upstream", "UP-08", "Well Completions & Workovers (Flowback Venting)", "Vented", 3, "N/A", 0.0, 0.0, "No flowback events", None, None, "", ""),
            ("FAC-A1", 2025, "Upstream", "UP-13", "Produced Water Handling, Vessels & Flash Separators", "Vented", 3, "MI", 0.0, 0.0, "Sampling campaign scheduled Q3 2026", None, None, "", ""),
            # FAC-B2 (2025 ~83% L4 with technical justification + remaining >= L3)
            ("FAC-B2", 2025, "Upstream", "UP-01", "Stationary Combustion (Turbines, Engines & Heaters)", "Combustion", 4, "Quantified", 68.0, 10.0, "Exhaust Slip Stack CEMS", "1", None, "", ""),
            ("FAC-B2", 2025, "Upstream", "UP-06", "Glycol Dehydrators & Stripping Gas Vents", "Vented", 4, "Quantified", 94.0, 15.0, "Rich Glycol Sampling + GRI-GLYCalc L4", "1", None, "", ""),
            ("FAC-B2", 2025, "Upstream", "UP-11", "Equipment Leaks & Component Fugitives (Valves/Flanges)", "Fugitive", 4, "Quantified", 66.0, 16.0, "OGI + Hi-Flow", "1", None, "", ""),
            ("FAC-B2", 2025, "Upstream", "UP-12", "Blowdowns, Purging & Vessel Depressurization", "Vented", 3, "Quantified", 45.0, 25.0, "Event Pressure-Volume Balance", "1", None, "", ""),
            # FAC-C3 (Midstream 2025 >=90% L4)
            ("FAC-C3", 2025, "Midstream", "MD-01", "Compressor Station Seals & Unit Blowdowns", "Fugitive", 4, "Quantified", 58.0, 12.0, "Direct Seal Vent Flowmeter", "1", None, "", ""),
            ("FAC-C3", 2025, "Midstream", "MD-06", "LNG Liquefaction, Regasification & Marine Loading Vents", "Vented", 4, "Quantified", 46.5, 13.0, "GIIGNL BOG Mass Balance", "1", None, "", ""),
            ("FAC-C3", 2025, "Midstream", "MD-10", "Refinery & Gas Plant Flares (Routine & Uncombusted Slip)", "Flaring", 4, "Quantified", 18.0, 15.0, "Ultrasonic Flare Meter + DRE", "1", None, "", ""),
            ("FAC-C3", 2025, "Midstream", "MD-04", "Pneumatic Controllers, Actuators & Valve Operators", "Vented", 3, "Quantified", 7.6, 20.0, "Stem Calibration EF", "1", None, "", ""),
        ]
        for fcode, yr, seg, scode, sname, scat, lvl, sflag, ch4_t, unc_p, qmeth, pway, yoy_p, yoy_ex, zero_ex in l4_source_specs:
            fac = facs_by_code[fcode]
            existing_src = OgmpEmissionSource.query.filter_by(facility_id=fac.id, year=yr, source_code=scode).first()
            if not existing_src:
                db.session.add(
                    OgmpEmissionSource(
                        facility_id=fac.id,
                        year=yr,
                        segment=seg,
                        source_code=scode,
                        source_name=sname,
                        source_category=scat,
                        ogmp_level=lvl,
                        status_flag=sflag,
                        ch4_tonnes=ch4_t,
                        uncertainty_pct=unc_p,
                        emission_factor_ref=qmeth,
                        quantification_method=qmeth,
                        pathway_code=pway,
                        yoy_change_pct=yoy_p,
                        yoy_explanation=yoy_ex,
                        zero_emission_explanation=zero_ex,
                        tenant_id="default",
                        created_by=admin_user.id if admin_user else None,
                    )
                )
        db.session.commit()

        # L5 Site-Level Measurement Campaigns (Option 1 & Option 2)
        l5_meas_specs = [
            ("FAC-A1", 2024, "2024-06-14", "Satellite (Sentinel-5P/MethaneSAT)", "Demo Sensor Suite", "Annualized", "Option 1", 42.1, 8760.0, 18.0, 3.0, "Clear sky overpass, wind 4.1 m/s NW"),
            ("FAC-A1", 2025, "2025-05-18", "Aircraft / Hyperspectral Imaging", "Bridger Photonics Demo", "Annualized", "Option 2", 40.9, 8760.0, 14.0, 1.5, "Spring multi-flight Option 2 survey, wind 3.2 m/s NE"),
            ("FAC-A1", 2025, "2025-09-12", "Drone LiDAR / OGI Survey", "Demo UAV Sensor", "Instantaneous", "Option 2", 39.8, 8760.0, 18.0, 2.0, "Autumn verification flight confirming Option 2 repeatability"),
            ("FAC-B2", 2025, "2025-07-10", "Drone LiDAR / OGI Survey", "FLIR GF320 + TDLAS", "Annualized", "Option 1", 31.6, 8760.0, 17.5, 2.5, "Low turbulence window, wind 2.8 m/s SW"),
            ("FAC-C3", 2025, "2025-08-22", "Fixed Continuous Sensor Network", "Demo Perimeter Array", "Annualized", "Option 1", 15.2, 8760.0, 12.0, 0.8, "Continuous coastal perimeter monitoring annual mean"),
        ]
        for fcode, yr, cdate, stype, vend, mmode, omode, rate, hrs, unc_p, mdl, notes in l5_meas_specs:
            fac = facs_by_code[fcode]
            if not OgmpSiteMeasurement.query.filter_by(facility_id=fac.id, year=yr, campaign_date=cdate).first():
                ann = round(rate * hrs / 1000.0, 4)
                hw = round(ann * (unc_p / 100.0), 4)
                db.session.add(
                    OgmpSiteMeasurement(
                        facility_id=fac.id,
                        year=yr,
                        campaign_date=cdate,
                        survey_type=stype,
                        instrument_vendor=vend,
                        measurement_mode=mmode,
                        option_mode=omode,
                        measured_rate_kg_hr=rate,
                        operating_hours_year=hrs,
                        annualized_tch4=ann,
                        uncertainty_pct=unc_p,
                        ci_low_tch4=round(max(0.0, ann - hw), 4),
                        ci_high_tch4=round(ann + hw, 4),
                        detection_threshold_kg_hr=mdl,
                        meteorological_notes=notes,
                        tenant_id="default",
                        created_by=admin_user.id if admin_user else None,
                    )
                )
        db.session.commit()

        # Reconcile L4/L5 Annual Reports & Implementation Plans
        rec_targets = [
            ("FAC-A1", 2024, "Option 1", "", "Demo Operator - Basin Alpha CPF"),
            ("FAC-A1", 2025, "Option 2", "", "Demo Operator - Basin Alpha CPF"),
            ("FAC-B2", 2025, "Option 1", "Blowdown event modeling uses verified supervisory SCADA logs (>= L3) alongside >=83% direct L4 coverage.", "Demo Operator - Basin Beta Gas Hub"),
            ("FAC-C3", 2025, "Option 1", "", "Demo Operator - Coastal Terminal"),
        ]
        for fcode, yr, opt_m, l4_just, ent_name in rec_targets:
            fac = facs_by_code[fcode]
            ent = ent_by_name[ent_name]
            srcs = OgmpEmissionSource.query.filter_by(facility_id=fac.id, year=yr).all()
            meas = OgmpSiteMeasurement.query.filter_by(facility_id=fac.id, year=yr).all()
            res = reconcile_l4_l5(
                srcs,
                meas,
                threshold_pct=20.0,
                l4_justification=l4_just,
                option_mode=opt_m,
            )
            prod_rows = ProductionData.query.filter_by(facility_id=fac.id, year=yr).all()
            gas_m3 = sum(production_gas_m3(pr) for pr in prod_rows)
            ch4_int = round((res["bottom_up"]["total_tch4"] * 1000.0 / (gas_m3 * 0.72)) * 100.0, 4) if gas_m3 > 0 else None
            wi = float(ent.working_interest_pct or 100.0)
            eq_ch4 = round(res["bottom_up"]["total_tch4"] * (wi / 100.0), 4)
            rep = OgmpAnnualReport.query.filter_by(facility_id=fac.id, year=yr).first()
            if not rep:
                rep = OgmpAnnualReport(
                    facility_id=fac.id,
                    reporting_entity_id=ent.id,
                    year=yr,
                    reporting_level=res["reporting_level"],
                    status="Submitted",
                    total_bottom_up_tch4=res["bottom_up"]["total_tch4"],
                    total_top_down_tch4=res["top_down"]["total_tch4"],
                    bu_uncertainty_pct=res["bottom_up"]["uncertainty_pct"],
                    bu_ci_low_tch4=res["bottom_up"]["ci_low_tch4"],
                    bu_ci_high_tch4=res["bottom_up"]["ci_high_tch4"],
                    td_uncertainty_pct=res["top_down"]["uncertainty_pct"],
                    td_ci_low_tch4=res["top_down"]["ci_low_tch4"],
                    td_ci_high_tch4=res["top_down"]["ci_high_tch4"],
                    ci_overlaps=res["ci_overlaps"],
                    variance_pct=res["variance_pct"],
                    variance_flag=res["variance_flag"],
                    reconciliation_status=res["reconciliation_status"],
                    l4_materiality_pct=res["materiality"]["l4_materiality_pct"],
                    l4_justification=l4_just,
                    pathway_code=res["pathway_code"],
                    measurement_mode=res["top_down"]["measurement_mode"],
                    option_mode=res["top_down"]["option_mode"],
                    gas_production_m3=round(gas_m3, 2),
                    ch4_intensity_pct=ch4_int,
                    equity_ch4_tch4=eq_ch4,
                    tenant_id="default",
                    created_by=admin_user.id if admin_user else None,
                )
                db.session.add(rep)
                db.session.flush()
                for s_row in srcs:
                    s_row.annual_report_id = rep.id
                for m_row in meas:
                    m_row.annual_report_id = rep.id
                db.session.add(
                    OgmpAssetReport(
                        annual_report_id=rep.id,
                        facility_id=fac.id,
                        year=yr,
                        ogmp_level=res["reporting_level"],
                        bottom_up_tch4=res["bottom_up"]["total_tch4"],
                        top_down_tch4=res["top_down"]["total_tch4"],
                        bu_ci_low_tch4=res["bottom_up"]["ci_low_tch4"],
                        bu_ci_high_tch4=res["bottom_up"]["ci_high_tch4"],
                        td_ci_low_tch4=res["top_down"]["ci_low_tch4"],
                        td_ci_high_tch4=res["top_down"]["ci_high_tch4"],
                        variance_pct=res["variance_pct"],
                        reconciliation_status=res["reconciliation_status"],
                        l4_coverage_pct=res["materiality"]["l4_materiality_pct"],
                        gas_throughput_m3=round(gas_m3, 2),
                        ch4_intensity_pct=ch4_int,
                        tenant_id="default",
                    )
                )
        db.session.commit()

        # Y0-Y10 Implementation Plans for Operated Assets
        for fcode, ent_name in [("FAC-A1", "Demo Operator - Basin Alpha CPF"), ("FAC-B2", "Demo Operator - Basin Beta Gas Hub")]:
            fac = facs_by_code[fcode]
            ent = ent_by_name[ent_name]
            if not OgmpImplementationPlan.query.filter_by(facility_id=fac.id).first():
                for prow in build_default_implementation_plan(fac.id, fac.name, operator_status="operated", base_year=2023):
                    status_lbl = "Completed" if prow["planned_year"] <= 2025 else "Planned"
                    db.session.add(
                        OgmpImplementationPlan(
                            reporting_entity_id=ent.id,
                            actual_level=prow["target_level"] if prow["planned_year"] <= 2025 else None,
                            milestone_status=status_lbl,
                            tenant_id="default",
                            created_by=admin_user.id if admin_user else None,
                            **{k: v for k, v in prow.items() if k != "milestone_status"},
                        )
                    )
        if not OgmpAuditTrail.query.first():
            db.session.add(
                OgmpAuditTrail(
                    facility_id=facs_by_code["FAC-A1"].id,
                    entity_type="OgmpAnnualReport",
                    entity_id="2025",
                    action="RECONCILE",
                    actor_id=admin_user.id if admin_user else None,
                    actor_name="Demo Administrator",
                    summary="Seeded UNEP OGMP 2.0 Level 4/5 RSS 95% CI reconciliation across operated basins (Pathway 1, Gold Level 5).",
                    tenant_id="default",
                )
            )
        db.session.commit()

        # 12. EU CBAM Product Exports (FAC-A1 and 2023 intentionally have none)
        cbam_specs = [
            {
                "fac_code": "FAC-C3",
                "year": 2024,
                "month": 6,
                "product_name": "Anhydrous Ammonia (Industrial Grade)",
                "cn_code": "2814 10 00",
                "quantity_tonnes": 42000.0,
                "export_destination": "EU - France",
                "specific_embedded_direct": 1.76,
                "specific_embedded_indirect": 0.14,
                "captured_co2_tonnes": 12600.0,
                "ccs_certificate_id": "CC-CCS-2024-001",
                "carbon_price_paid_eur": 18.5,
                "carbon_price_legal_ref": "Demo Origin Carbon Levy Law Art. 9 (2024)",
                "is_complex_good": False,
            },
            {
                "fac_code": "FAC-C3",
                "year": 2025,
                "month": 2,
                "product_name": "Ammonia Solution (Industrial Derivative)",
                "cn_code": "2814 90 00",
                "quantity_tonnes": 18500.0,
                "export_destination": "EU - Netherlands",
                "specific_embedded_direct": 1.62,
                "specific_embedded_indirect": 0.12,
                "captured_co2_tonnes": 0.0,
                "ccs_certificate_id": None,
                "carbon_price_paid_eur": 12.0,
                "carbon_price_legal_ref": "Demo Origin Carbon Levy Law Art. 9 (2025)",
                "is_complex_good": False,
            },
            {
                "fac_code": "FAC-C3",
                "year": 2025,
                "month": 4,
                "product_name": "Clean Hydrogen (Demo ATR)",
                "cn_code": "2804 10 00",
                "quantity_tonnes": 9800.0,
                "export_destination": "EU - Germany",
                "specific_embedded_direct": 3.95,
                "specific_embedded_indirect": 0.31,
                "captured_co2_tonnes": 2450.0,
                "ccs_certificate_id": "CC-CCS-2025-002",
                "carbon_price_paid_eur": 22.0,
                "carbon_price_legal_ref": "Demo Origin Carbon Levy Law Art. 9 (2025)",
                "is_complex_good": True,
                "precursor_name": "Refined Natural Gas Feedstock",
                "precursor_cn_code": "2711 21 00",
                "precursor_ratio": 2.85,
                "precursor_see_dir": 0.18,
                "precursor_see_indir": 0.02,
            },
            {
                "fac_code": "FAC-B2",
                "year": 2025,
                "month": 9,
                "product_name": "Stabilized Condensate / Fuel",
                "cn_code": "2710 19 43",
                "quantity_tonnes": 64000.0,
                "export_destination": "EU - Italy",
                "specific_embedded_direct": 0.28,
                "specific_embedded_indirect": 0.05,
                "captured_co2_tonnes": 0.0,
                "ccs_certificate_id": None,
                "carbon_price_paid_eur": 0.0,
                "carbon_price_legal_ref": None,
                "is_complex_good": False,
            },
        ]
        for cspec in cbam_specs:
            fac = facs_by_code[cspec["fac_code"]]
            qtr = f"Q{((cspec['month'] - 1) // 3) + 1}"
            existing_cbam = CbamProductExport.query.filter_by(
                facility_id=fac.id, year=cspec["year"], cn_code=cspec["cn_code"]
            ).first()
            if existing_cbam:
                existing_cbam.month = cspec["month"]
                existing_cbam.quarter = qtr
                existing_cbam.quantity_tonnes = cspec["quantity_tonnes"]
                existing_cbam.export_destination = cspec["export_destination"]
                existing_cbam.specific_embedded_direct = cspec["specific_embedded_direct"]
                existing_cbam.specific_embedded_indirect = cspec["specific_embedded_indirect"]
                existing_cbam.captured_co2_tonnes = cspec.get("captured_co2_tonnes", 0.0)
                existing_cbam.ccs_certificate_id = cspec.get("ccs_certificate_id")
                existing_cbam.carbon_price_paid_eur = cspec.get("carbon_price_paid_eur", 0.0)
                existing_cbam.carbon_price_legal_ref = cspec.get("carbon_price_legal_ref")
                existing_cbam.is_complex_good = bool(cspec.get("is_complex_good", False))
                existing_cbam.precursor_name = cspec.get("precursor_name")
                existing_cbam.precursor_cn_code = cspec.get("precursor_cn_code")
                existing_cbam.precursor_ratio = cspec.get("precursor_ratio", 0.0)
                existing_cbam.precursor_see_dir = cspec.get("precursor_see_dir", 0.0)
                existing_cbam.precursor_see_indir = cspec.get("precursor_see_indir", 0.0)
                existing_cbam.notes = "Demonstrative EU CBAM export record (Regulation (EU) 2023/956 transitional declaration)."
            else:
                db.session.add(
                    CbamProductExport(
                        facility_id=fac.id,
                        year=cspec["year"],
                        month=cspec["month"],
                        product_name=cspec["product_name"],
                        cn_code=cspec["cn_code"],
                        quantity_tonnes=cspec["quantity_tonnes"],
                        export_destination=cspec["export_destination"],
                        quarter=qtr,
                        specific_embedded_direct=cspec["specific_embedded_direct"],
                        specific_embedded_indirect=cspec["specific_embedded_indirect"],
                        captured_co2_tonnes=cspec.get("captured_co2_tonnes", 0.0),
                        ccs_certificate_id=cspec.get("ccs_certificate_id"),
                        carbon_price_paid_eur=cspec.get("carbon_price_paid_eur", 0.0),
                        carbon_price_legal_ref=cspec.get("carbon_price_legal_ref"),
                        is_complex_good=bool(cspec.get("is_complex_good", False)),
                        precursor_name=cspec.get("precursor_name"),
                        precursor_cn_code=cspec.get("precursor_cn_code"),
                        precursor_ratio=cspec.get("precursor_ratio", 0.0),
                        precursor_see_dir=cspec.get("precursor_see_dir", 0.0),
                        precursor_see_indir=cspec.get("precursor_see_indir", 0.0),
                        notes="Demonstrative EU CBAM export record (Regulation (EU) 2023/956 transitional declaration).",
                        created_by=admin_user.id if admin_user else None,
                    )
                )
        db.session.commit()

        # 13. Goals, Base Year, Recalculation History, Reporting Metadata, SBTi, Mitigation
        # Reconcile corporate 2023 baseline strictly to verified seeded 2023 inventory
        demo_fids = [f.id for f in facs_by_code.values()]
        s1_2023 = sum(
            float(e.co2e_total or 0.0)
            for e in Emission.query.filter(
                Emission.facility_id.in_(demo_fids),
                Emission.year == 2023,
                Emission.status == "Verified",
            ).all()
        )
        s2_2023 = sum(
            float(s2.co2e or 0.0)
            for s2 in Scope2Emission.query.filter(
                Scope2Emission.facility_id.in_(demo_fids),
                Scope2Emission.year == 2023,
                Scope2Emission.status == "Verified",
            ).all()
        )
        s3_2023 = sum(
            float(s3.co2e or 0.0)
            for s3 in Scope3Emission.query.filter(
                Scope3Emission.facility_id.in_(demo_fids),
                Scope3Emission.year == 2023,
                Scope3Emission.status == "Verified",
            ).all()
        )
        s1_s2_2023 = round(s1_2023 + s2_2023, 2)
        s1_s2_s3_2023 = round(s1_s2_2023 + s3_2023, 2)

        for yr, pct in [(2025, 0.92), (2026, 0.87), (2030, 0.65)]:
            tgt_val = round(s1_s2_2023 * pct, 0)
            g = Goal.query.filter_by(year=yr).first()
            if g:
                g.target_amount = tgt_val
            else:
                db.session.add(Goal(year=yr, target_amount=tgt_val))
        if not BaseYear.query.filter_by(id=1).first():
            db.session.add(BaseYear(id=1, year=2023, locked=1))
        byr = BaseYearRecalculation.query.filter_by(year=2023).first()
        if byr:
            byr.reason = "Initial 2023 base-year establishment and boundary verification (ISO 14064-1 Clause 6.4.1)."
            byr.previous_emissions = round(s1_s2_2023 * 1.012, 2)
            byr.adjusted_emissions = s1_s2_2023
            byr.approved_by = (auditor_user or admin_user).id if (auditor_user or admin_user) else None
        else:
            db.session.add(
                BaseYearRecalculation(
                    year=2023,
                    reason="Initial 2023 base-year establishment and boundary verification (ISO 14064-1 Clause 6.4.1).",
                    previous_emissions=round(s1_s2_2023 * 1.012, 2),
                    adjusted_emissions=s1_s2_2023,
                    approved_by=(auditor_user or admin_user).id if (auditor_user or admin_user) else None,
                    created_by=admin_user.id if admin_user else None,
                )
            )
        for yr in (2023, 2024, 2025):
            rm = ReportingMetadata.query.filter_by(year=yr).first()
            if rm:
                rm.assurance_level = "Pre-Assurance / Internal Review"
                rm.assurance_provider = "Internal MRV Team (No Third-Party Verifier Engaged)"
            else:
                db.session.add(
                    ReportingMetadata(
                        year=yr,
                        has_reduction_target=1,
                        target_description="25% Scope 1 & 2 intensity reduction by 2030 vs. 2023 baseline.",
                        is_tcfd_aligned=1,
                        assurance_level="Pre-Assurance / Internal Review",
                        assurance_provider="Internal MRV Team (No Third-Party Verifier Engaged)",
                    )
                )
        sbti = SbtiTarget.query.first()
        if sbti:
            sbti.base_year = 2023
            sbti.base_year_emissions = s1_s2_s3_2023
        else:
            db.session.add(
                SbtiTarget(
                    base_year=2023,
                    base_year_emissions=s1_s2_s3_2023,
                    target_year=2050,
                    reduction_rate_pct=4.2,
                    pathway_type="1.5C",
                    scope_coverage="S1S2S3",
                    created_by=admin_user.id if admin_user else None,
                )
            )
        mit_specs = [
            ("FAC-A1", "Flare Gas Recovery Unit Phase 1", "efficiency", 2024, 18500.0, 1480000.0, "completed", "Captured routine low-pressure flare gas."),
            ("FAC-B2", "LDAR Continuous Optical Monitoring", "methane_abatement", 2025, 9200.0, 460000.0, "active", "Continuous methane leak mitigation campaign."),
            ("FAC-C3", "Export Pump Solar Hybridization", "renewable", 2025, 7400.0, 590000.0, "active", "Grid-tied solar PV displacement."),
        ]
        for fac_code, mname, mtype, yr, qty, inv_usd, st, desc in mit_specs:
            fac = facs_by_code[fac_code]
            mp = MitigationProject.query.filter_by(facility_id=fac.id, name=mname, year=yr).first()
            if mp:
                mp.investment_amount = inv_usd
                mp.quantity_tco2e = qty
            else:
                db.session.add(
                    MitigationProject(
                        facility_id=fac.id,
                        name=mname,
                        project_type=mtype,
                        year=yr,
                        quantity_tco2e=qty,
                        investment_amount=inv_usd,
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
                details="Initialized clean demonstration dataset (Demo Operator Co.)",
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
    """CLI entrypoint to initialize or refresh the synthetic demo SQLite database."""
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
