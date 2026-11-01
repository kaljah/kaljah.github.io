"""
Tenant Configuration & Multi-Tenancy Architecture (Part 3.2)
============================================================
Moves hardcoded operator names ('Sonatrach'), regulatory frameworks
('Executive Decree 21-330 Article 9'), email domains ('sonatrach.dz'),
and factor tier labels into configurable tenant profiles.
"""
from typing import Dict, Any, Optional
import os
import json
from models import db, SystemSetting, ActivityLog, utc_now

DEFAULT_TENANT_CONFIG: Dict[str, Any] = {
    "tenant_id": "default",
    "organization_name": "Sonatrach",
    "short_code": "SH",
    "legal_entity": "Société Nationale pour la Recherche, la Production, le Transport, la Transformation, et la Commercialisation des Hydrocarbures",
    "email_domain": "sonatrach.dz",
    "country": "Algeria",
    "regulatory_framework": "Executive Decree 21-330 Article 9",
    "regulatory_citation": "Décret exécutif n° 21-330 du 1er septembre 2021 relatif au contrôle des émissions atmosphériques et de gaz à effet de serre",
    "tier2_label": "Tier 2 (Site-Specific Laboratory Factors)",
    "tier2_partner_label": "Tier 2 (Operator Partner Factors)",
    "national_group_name": "Sonatrach Corporate Group (Consolidated National)",
    "default_currency": "DZD",
    "base_year": 2023,
    "target_year": 2030,
}

TENANT_REGISTRY: Dict[str, Dict[str, Any]] = {
    "default": DEFAULT_TENANT_CONFIG,
    "sonatrach": DEFAULT_TENANT_CONFIG,
    "mena_operator_b": {
        "tenant_id": "mena_operator_b",
        "organization_name": "Al-Amal Petroleum Corp",
        "short_code": "AAP",
        "legal_entity": "Al-Amal Petroleum Exploration & Production Co.",
        "email_domain": "alamal-petro.com",
        "country": "MENA Region",
        "regulatory_framework": "National Environmental Law 14/2019",
        "regulatory_citation": "Regional Ministry of Environment Greenhouse Gas Standard",
        "tier2_label": "Tier 2 (Site-Specific Laboratory Factors)",
        "tier2_partner_label": "Tier 2 (Joint Venture Operating Factors)",
        "national_group_name": "Al-Amal Petroleum Group (Consolidated)",
        "default_currency": "USD",
        "base_year": 2024,
        "target_year": 2035,
    }
}


def get_tenant_config(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve tenant configuration by tenant_id, with persistent DB overrides."""
    if not tenant_id:
        tenant_id = os.environ.get("DEFAULT_TENANT_ID", "default")
    key_name = str(tenant_id).lower()
    base_cfg = dict(TENANT_REGISTRY.get(key_name, DEFAULT_TENANT_CONFIG))

    try:
        setting_key = f"tenant_config_{key_name}" if key_name != "default" else "tenant_config"
        setting = SystemSetting.query.filter_by(key=setting_key).first()
        if not setting and key_name != "default":
            setting = SystemSetting.query.filter_by(key="tenant_config").first()
        if setting and setting.value:
            stored = json.loads(setting.value)
            if isinstance(stored, dict):
                base_cfg.update(stored)
    except Exception:
        pass
    return base_cfg


def update_tenant_config(tenant_id: Optional[str], updates: Dict[str, Any], user=None) -> Dict[str, Any]:
    """Persist updated tenant settings to the DB and record an audit log."""
    if not tenant_id:
        tenant_id = "default"
    current = get_tenant_config(tenant_id)
    old_snapshot = dict(current)

    allowed_keys = {
        "organization_name",
        "short_code",
        "legal_entity",
        "email_domain",
        "country",
        "regulatory_framework",
        "regulatory_citation",
        "tier2_label",
        "tier2_partner_label",
        "national_group_name",
        "default_currency",
        "base_year",
        "target_year",
    }
    filtered = {k: v for k, v in updates.items() if k in allowed_keys}
    current.update(filtered)

    setting_key = f"tenant_config_{tenant_id.lower()}" if tenant_id.lower() != "default" else "tenant_config"
    setting = SystemSetting.query.filter_by(key=setting_key).first()
    if not setting:
        setting = SystemSetting(key=setting_key, value=json.dumps(current))
        db.session.add(setting)
    else:
        setting.value = json.dumps(current)
        setting.updated_at = utc_now()

    # Log audit event
    user_name = getattr(user, "fullName", None) or getattr(user, "email", "Admin") if user else "System"
    user_id = getattr(user, "id", None) if user else None
    audit = ActivityLog(
        action="SETTINGS_CHANGE",
        entity="TenantConfig",
        entity_id=setting_key,
        user_name=user_name,
        user_id=user_id,
        details=f"Tenant configuration '{tenant_id}' updated: {', '.join(filtered.keys())}",
        old_values=json.dumps(old_snapshot),
        new_values=json.dumps(current),
    )
    db.session.add(audit)
    db.session.commit()
    return current


def get_current_tenant_id(user=None) -> str:
    """Derive tenant_id from active user session, organization, or environment."""
    if user and getattr(user, "orgName", None):
        org = user.orgName.lower().strip()
        if "al-amal" in org or "alamal" in org or "tenant_b" in org:
            return "mena_operator_b"
        if getattr(user, "tenant_id", None):
            return str(user.tenant_id).lower().strip()
    return os.environ.get("DEFAULT_TENANT_ID", "default")
